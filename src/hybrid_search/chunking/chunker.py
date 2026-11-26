"""Deterministic token-aware document chunking with contextual enrichment."""

from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any, List, Optional
from hybrid_search.models.document import Chunk, Document

_TOKENIZER: Optional[Any] = None


def get_tokenizer() -> Optional[Any]:
    """Retrieves cached tokenizer for BAAI/bge-small-en-v1.5, prioritizing local fastembed cache."""
    global _TOKENIZER
    if _TOKENIZER is None:
        try:
            from fastembed import TextEmbedding
            _TOKENIZER = TextEmbedding(model_name="BAAI/bge-small-en-v1.5").model.tokenizer
            _TOKENIZER.no_truncation()
        except Exception:
            try:
                from tokenizers import Tokenizer
                _TOKENIZER = Tokenizer.from_pretrained("BAAI/bge-small-en-v1.5")
                _TOKENIZER.no_truncation()
            except Exception:
                _TOKENIZER = None
    return _TOKENIZER


def count_tokens(text: str, tokenizer: Optional[Any] = None) -> int:
    """Calculates exact token count using BGE tokenizer with word-count fallback."""
    tok = tokenizer or get_tokenizer()
    if tok is not None:
        try:
            return len(tok.encode(text).ids)
        except Exception:
            pass
    # Fallback to word-based approximation: 1 token ≈ 0.75 words
    return int(len(text.split()) * 1.33)


def extract_fact_years(text: str, fallback_period: Optional[str] = None) -> List[int]:
    """Extracts all financial years present in text and fallback fiscal period."""
    years = set()
    found = re.findall(r"\b(201[0-9]|202[0-9])\b", text)
    for y in found:
        years.add(int(y))
    if not years and fallback_period and fallback_period != "Unknown":
        fp_years = re.findall(r"(?:FY|Q-|Event\s+)?(201[0-9]|202[0-9])", fallback_period)
        for y in fp_years:
            years.add(int(y))
    return sorted(list(years))


class DocumentChunker:
    """Splits Document sections into overlapping, boundary-aware text chunks with contextual metadata."""

    MAX_MODEL_TOKENS: int = 480

    def __init__(
        self,
        chunk_size_tokens: int = 480,
        chunk_overlap_tokens: int = 80,
        tokenizer: Optional[Any] = None,
    ):
        self.max_tokens = min(chunk_size_tokens, self.MAX_MODEL_TOKENS)
        self.chunk_overlap_tokens = min(chunk_overlap_tokens, self.max_tokens // 2)
        self.tokenizer = tokenizer or get_tokenizer()

    def count_tokens(self, text: str) -> int:
        return count_tokens(text, self.tokenizer)

    @classmethod
    def split_into_sentences(cls, text: str) -> List[str]:
        """Splits text into sentences based on punctuation boundaries while preserving financial numbers and abbreviations."""
        text = text.strip()
        if not text:
            return []

        # Split on double newlines or paragraph breaks first
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        units: List[str] = []

        for para in paragraphs:
            # If paragraph contains markdown/pipe table rows or row-to-text lines, split by line to keep rows atomic
            if ("|" in para or "Unit:" in para) and "\n" in para:
                lines = [l.strip() for l in para.split("\n") if l.strip()]
                units.extend(lines)
                continue

            # Split sentences carefully avoiding common financial abbreviations (e.g. U.S., Inc., Jan., No., vs.)
            # Match sentence ends: period/exclamation/question followed by whitespace and uppercase letter
            sentence_splits = re.split(r"(?<=[.!?])\s+(?=[A-Z\"\'\$\(])", para)
            for s in sentence_splits:
                s_clean = s.strip()
                if s_clean:
                    units.append(s_clean)

        return units

    def chunk_section_text(
        self,
        text: str,
        max_tokens: Optional[int] = None,
        overlap_tokens: Optional[int] = None,
    ) -> List[str]:
        """Chunks section text into overlapping windows respecting sentence/table boundaries."""
        sentences = self.split_into_sentences(text)
        if not sentences:
            return []

        target_tokens = max_tokens if max_tokens is not None else max(self.max_tokens - 30, 60)
        target_overlap = overlap_tokens if overlap_tokens is not None else min(self.chunk_overlap_tokens, target_tokens // 3)

        chunks: List[str] = []
        current_sentences: List[str] = []
        current_tokens = 0

        for sentence in sentences:
            s_tokens = self.count_tokens(sentence)

            # If a single sentence or table row is larger than target_tokens, split by word window
            if s_tokens > target_tokens:
                words = sentence.split()
                start_w = 0
                while start_w < len(words):
                    end_w = len(words)
                    while end_w > start_w and self.count_tokens(" ".join(words[start_w:end_w])) > target_tokens:
                        end_w -= 5
                    if end_w <= start_w:
                        end_w = start_w + 1
                    sub_text = " ".join(words[start_w:end_w])
                    chunks.append(sub_text)
                    step = end_w - start_w
                    if step > 5:
                        step = max(step - 10, 1)
                    start_w += step
                continue

            if current_tokens + s_tokens > target_tokens and current_sentences:
                chunk_sep = "\n" if any("Unit:" in s for s in current_sentences) else " "
                chunks.append(chunk_sep.join(current_sentences))
                # Compute overlap sentences to retain
                overlap_sentences: List[str] = []
                overlap_tokens_acc = 0
                for s in reversed(current_sentences):
                    st = self.count_tokens(s)
                    if overlap_tokens_acc + st <= target_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_tokens_acc += st
                    else:
                        break
                current_sentences = list(overlap_sentences)
                current_tokens = self.count_tokens(" ".join(current_sentences)) if current_sentences else 0

            current_sentences.append(sentence)
            current_tokens = self.count_tokens(" ".join(current_sentences))

        if current_sentences:
            chunk_sep = "\n" if any("Unit:" in s for s in current_sentences) else " "
            final_chunk = chunk_sep.join(current_sentences)
            if not chunks or final_chunk != chunks[-1]:
                chunks.append(final_chunk)

        return chunks

    def chunk_document(self, document: Document, start_chunk_idx: int = 0) -> List[Chunk]:
        """Creates contextualized Chunk models from all sections of a Document with strict <= 480 token limit."""
        chunks: List[Chunk] = []
        chunk_idx = start_chunk_idx

        sections = document.sections or []
        for section in sections:
            # Contextual enrichment prefix: ensures dense, sparse, and lexical embeddings
            # retain critical entity, ticker, document type, period, and section context
            context_prefix = (
                f"[{document.company} ({document.ticker}) | {document.document_type} {document.fiscal_period} | "
                f"Section: {section.section_name}]\n\n"
            )
            prefix_tokens = self.count_tokens(context_prefix)
            target_body_tokens = max(self.max_tokens - prefix_tokens, 60)
            overlap_body_tokens = max(min(self.chunk_overlap_tokens, target_body_tokens // 3), 10)

            section_chunks = self.chunk_section_text(
                section.text,
                max_tokens=target_body_tokens,
                overlap_tokens=overlap_body_tokens,
            )

            for text_piece in section_chunks:
                chunk_id = f"{document.document_id}_chunk_{chunk_idx:04d}"
                enriched_text = context_prefix + text_piece

                # Strict guarantee: ensure header + chunk body <= MAX_MODEL_TOKENS (480)
                while self.count_tokens(enriched_text) > self.MAX_MODEL_TOKENS and len(text_piece.split()) > 5:
                    words = text_piece.split()
                    text_piece = " ".join(words[:-5])
                    enriched_text = context_prefix + text_piece

                fact_years = extract_fact_years(text_piece, fallback_period=document.fiscal_period)

                chunk = Chunk(
                    chunk_id=chunk_id,
                    document_id=document.document_id,
                    company=document.company,
                    ticker=document.ticker,
                    cik=document.cik,
                    document_type=document.document_type,
                    filing_date=document.filing_date,
                    fiscal_period=document.fiscal_period,
                    section=section.section_name,
                    sector=document.sector or "Unknown",
                    geography=document.geography or "US",
                    text=enriched_text,
                    fact_years=fact_years,
                    chunk_index=chunk_idx,
                    source_url=document.source_url,
                    accession_number=document.accession_number,
                )
                chunks.append(chunk)
                chunk_idx += 1

        return chunks

    def chunk_documents(
        self,
        documents: List[Document],
        output_path: Optional[str | Path] = None,
    ) -> List[Chunk]:
        """Chunks a batch of Documents and optionally serializes to JSONL."""
        all_chunks: List[Chunk] = []
        for doc in documents:
            doc_chunks = self.chunk_document(doc)
            all_chunks.extend(doc_chunks)

        if output_path:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                for c in all_chunks:
                    f.write(json.dumps(c.model_dump()) + "\n")


            manifest_file = out_file.parent / "manifest.json"
            manifest_data = {
                "total_chunks": len(all_chunks),
                "total_documents": len(documents),
                "companies": list({c.ticker for c in all_chunks}),
            }
            manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        return all_chunks
