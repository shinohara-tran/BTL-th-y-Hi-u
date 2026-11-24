"""Query-aware extractive answer pinpointer and highlighter for financial texts and tables."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class ExtractedAnswer:
    """Encapsulates the pinpointed answer and highlighted text."""
    exact_answer: str
    confidence: float
    highlighted_text: str
    is_table_row: bool = False


class AnswerExtractor:
    """Extracts the precise answering clause, sentence, or table row from a retrieved chunk."""

    STOP_WORDS = {
        "what", "is", "the", "of", "and", "a", "an", "in", "to", "for", "how", "many",
        "based", "on", "does", "represents", "represent", "which", "are", "from", "with",
        "by", "at", "as", "was", "were", "or", "that", "this", "these", "those", "about"
    }

    @classmethod
    def extract(cls, query: str, chunk_text: str, *, company: str = "", ticker: str = "") -> ExtractedAnswer:
        """Extracts the most relevant answering sentence or table segment for the given query."""
        if not chunk_text:
            return ExtractedAnswer(exact_answer="", confidence=0.0, highlighted_text="")

        # Separate metadata header from body
        header_match = re.match(r"^(\[.*?\])\s*\n+", chunk_text)
        header = header_match.group(1) if header_match else ""
        body = chunk_text[len(header):].strip() if header else chunk_text.strip()

        # 1. Try smart tabular row extraction if text contains tables
        table_fact = cls._extract_table_fact(query, body, company, ticker)
        if table_fact:
            highlighted_body = cls._highlight_in_text(body, table_fact[1])
            full_highlighted = f"{header}\n\n{highlighted_body}" if header else highlighted_body
            return ExtractedAnswer(
                exact_answer=table_fact[0],
                confidence=cls._evidence_score(query, table_fact[0], header),
                highlighted_text=full_highlighted,
                is_table_row=True,
            )

        # 2. Parse candidates: sentences, footnotes, and table rows
        candidates = cls._split_into_candidates(body)
        if not candidates:
            return ExtractedAnswer(exact_answer=body[:200], confidence=0.0, highlighted_text=chunk_text)

        # Tokenize query keywords
        query_words = [w.lower() for w in re.findall(r"\w+", query)]
        keywords = [w for w in query_words if w not in cls.STOP_WORDS and len(w) > 1]
        keyword_set = set(keywords)

        scored_candidates: List[Tuple[float, str, bool]] = []
        for cand, is_table in candidates:
            cand_lower = cand.lower()
            cand_words = set(re.findall(r"\w+", cand_lower))
            
            # Direct token overlap
            overlap = len(keyword_set.intersection(cand_words))
            
            # Stemmed / semantic synonym overlap for key risk, operational, and financial concepts
            stem_synonyms = {
                "supply": {"supplies", "supplier", "suppliers", "sourcing", "procurement", "materials"},
                "bottlenecks": {"shortages", "shortage", "constraints", "bottleneck", "limits", "cycles", "delays", "unavailability", "unavailability"},
                "disrupt": {"disruption", "disruptions", "delay", "delays", "impair", "hinder", "fail", "decline", "loss"},
                "manufacturing": {"production", "fabrication", "operations", "manufacture", "wafers", "foundry"},
                "chip": {"semiconductor", "semiconductors", "wafers", "silicon", "integrated", "circuits"},
            }
            for kw in keyword_set:
                syns = stem_synonyms.get(kw, set())
                if syns and any(s in cand_words for s in syns):
                    overlap += 0.75

            # Bonus for numerical/percentage facts if query asks for percentage/how many/amounts
            bonus = 0.0
            if any(q in query.lower() for q in ["how many", "percentage", "revenue", "percent", "%", "total", "spend", "cost", "earnings", "per share", "eps", "diluted", "income", "sales"]):
                if re.search(r"\d+[\.,]?\d*%", cand) or re.search(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b", cand) or "$" in cand or "%" in cand or "=" in cand:
                    bonus += 0.40

            # Substantive content bonus: specific concrete materials, named entities, lists (such as, including)
            if any(term in cand_lower for term in ["such as", "including", "limited number of", "shortages", "unavailability", "silicon wafers", "photoresist", "chemicals", "export licenses"]):
                bonus += 0.30

            # Causal risk impact bonus
            if any(term in cand_lower for term in ["unable to obtain", "limited supply", "delivery cycles", "result in", "adversely affect"]):
                bonus += 0.20

            # Severe penalty for table lead-in sentences ending in colon or procedural table intros without numbers
            if cand.strip().endswith(":") or re.search(r"\b(the following table|the table below|the following tables|as follows:?)\b", cand_lower):
                bonus -= 0.60

            # Penalty for generic procedural transition sentences / platitudes
            if re.match(r"^(?:to better manage|we evaluate and project|we have also implemented|in order to|we believe that|we continue to)", cand_lower):
                bonus -= 0.40

            score = (overlap / (len(keyword_set) + 1e-5)) + bonus
            scored_candidates.append((score, cand, is_table))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_cand, is_table = scored_candidates[0]

        # Clean candidate text for display
        clean_answer = cls._clean_answer_text(best_cand)

        # Highlight the answer inside the body
        highlighted_body = cls._highlight_in_text(body, best_cand)
        full_highlighted = f"{header}\n\n{highlighted_body}" if header else highlighted_body

        confidence = cls._evidence_score(query, clean_answer, header)
        return ExtractedAnswer(
            exact_answer=clean_answer,
            confidence=confidence,
            highlighted_text=full_highlighted,
            is_table_row=is_table,
        )

    @classmethod
    def _evidence_score(cls, query: str, answer: str, header: str) -> float:
        """Heuristic evidence coverage, not a calibrated correctness probability."""
        q, a = query.lower(), answer.lower()
        if answer.strip().endswith(":") or re.search(r"\b(the following table|the table below|the following tables)\b", a):
            return 0.0
        words = set(re.findall(r"[a-z]+", q)) - cls.STOP_WORDS
        evidence = set(re.findall(r"[a-z]+", a + " " + header.lower()))
        score = len(words & evidence) / max(1, len(words))
        if re.search(r"earnings per share|\beps\b", q):
            if not re.search(r"(earnings|income) per (common )?share|\beps\b", a):
                return 0.0
            if any(term in q and term not in a for term in ("basic", "diluted")):
                return 0.0
            if not re.search(r"\$\s*\d+|\d+\.\d+|\b\d{1,3}(?:,\d{3})*\b", a):
                return 0.0
        if ("percentage" in q or "percent" in q) and not re.search(r"\d\s*%|\d\s*\|\s*%|\d\s*percent", a):
            return 0.0
        if re.search(r"weighted[ -]average.*shares|shares outstanding", q) and not re.search(r"\d[\d,.]*", a):
            return 0.0
        years = set(re.findall(r"(?:\bfy\s*|\b)((?:19|20)\d{2})\b", q))
        if years and not all(year in a for year in years):
            score = min(score, 0.5)
        annual = re.search(r"\b(?:fiscal(?: year)?|full year|fy)\s*\d{4}", q)
        interim = re.search(r"\b(?:quarter|q[1-4]|months?)\b", q)
        if annual and not interim and re.search(r"\b10-q\b|\b(?:three|six|nine)[ -]months?", header.lower() + " " + a):
            score = min(score, 0.25)
        return round(score, 4)

    @classmethod
    def _extract_table_fact(cls, query: str, body: str, company: str = "", ticker: str = "") -> Optional[Tuple[str, str]]:
        """Extracts aligned tabular row metric (e.g. 'Intelligent Cloud -> 2024: $105,362M') if present."""
        if "|" not in body:
            return None

        # 1. Check for Footnotes first (e.g., Singapore represented 22%...)
        fn_match = re.search(r"(\(\d+\)\s+[A-Z][^\n]+(?:represented|revenue|accounted)[^\n]+)", body, re.IGNORECASE)
        if fn_match:
            fn_text = fn_match.group(1).strip()
            stop_words = {"what", "was", "the", "for", "in", "of", "and", "a", "an", "to", "how", "much", "is"}
            q_words = set(re.findall(r"\w+", query.lower())) - stop_words
            fn_words = set(re.findall(r"\w+", fn_text.lower()))
            if len(q_words.intersection(fn_words)) >= 2:
                sents = re.split(r"(?<=[.!?])\s+", fn_text)
                clean_fn = sents[0] if sents else fn_text
                return (clean_fn, fn_text)

        # 2. Parse Clean Table Cells
        cells = [c.strip() for c in body.split("|") if c.strip() and c.strip() not in ["$", "%", "-"]]
        if len(cells) < 4:
            return None

        company_words = set(re.findall(r"\w+", f"{company} {ticker}".lower()))
        stop_words = {"what", "was", "the", "for", "in", "of", "and", "a", "an", "to", "how", "much", "is", "total", "revenue", "fiscal", "year", "2024", "2023", "2022", "2025", "2026"}.union(company_words)
        q_metric_words = [w for w in re.findall(r"\w+", query.lower()) if w not in stop_words and len(w) > 1]
        if not q_metric_words:
            q_metric_words = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 2 and w not in company_words]

        # 4. Look for Target Row Labels (skipping dates, headers, company names)
        target_matches = []
        for idx, cell in enumerate(cells):
            if len(cell) > 50:
                continue
            if re.search(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Year Ended|Months Ended|Form 10|Performance|Inc\.|Corporation)\b", cell, re.IGNORECASE):
                continue
            if re.match(r"^[\$\d\s,\.\(\)\-\%]+$", cell):
                continue

            cell_lower = cell.lower()
            match_count = sum(1 for qw in q_metric_words if qw in cell_lower)
            if match_count > 0:
                target_matches.append((match_count, idx, cell))

        if not target_matches:
            return None

        target_matches.sort(key=lambda x: x[0], reverse=True)
        best_count, best_idx, best_label = target_matches[0]

        # 5. Extract Multi-Year Numerical Values Following Label
        # Read the unit attached to the selected row and its table caption.
        caption = body[:body.find(best_label)].rsplit("Note ", 1)[-1].lower()
        label = best_label.lower()
        scale = r"(thousands|millions|billions)"
        shares = re.search(r"\bshares?\s+in\s+" + scale, caption)
        money = re.search(r"\b(?:dollars|usd|net income)\s+in\s+" + scale, caption)
        general = re.search(r"\bin\s+" + scale, caption)
        if shares is None:
            shares = re.search(r"\bin\s+" + scale + r",?\s+except per[ -]share", caption)
        per_share = "per share" in label
        share_count = bool(re.search(r"\bshares?\b", label)) and not per_share

        # Preserve detached currency and percentage markers discarded during label matching.
        raw_cells = [c.strip() for c in body.split("|") if c.strip()]
        label_offset = -1
        for offset, raw in enumerate(raw_cells):
            if raw not in {"$", "%", "-"}:
                label_offset += 1
            if label_offset == best_idx:
                break

        values: List[str] = []
        cursor = offset + 1
        while cursor < len(raw_cells):
            dollar = raw_cells[cursor] == "$"
            if dollar:
                cursor += 1
            if cursor >= len(raw_cells):
                break
            cell = raw_cells[cursor]
            if cell in {"-", "—", "–"}:
                values.append(cell)
                cursor += 1
                continue
            if not re.fullmatch(r"\$?\s*\(?-?[\d,]+(?:\.\d+)?\)?\s*%?", cell):
                break
            cursor += 1
            percent = cell.endswith("%")
            if cursor < len(raw_cells) and raw_cells[cursor] == "%":
                percent = True
                cursor += 1
            value = cell.strip("$% ").strip()
            if percent or "percentage" in label:
                value += "%"
            elif share_count:
                value += " " + (shares.group(1) + " of " if shares else "") + "shares"
            else:
                currency = dollar or "$" in cell or bool(re.search(r"\b(?:dollars|usd)\s+in\b", caption))
                if currency:
                    value = "$" + value
                unit = money or general
                if unit and not per_share and (currency or money):
                    value += " " + unit.group(1)
                if per_share:
                    value += " per share"
            values.append(value)

        if values:
            # Look for a contiguous run of year cells above this row.
            year_cell = re.compile(r"(?:FY\s*|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+)?((?:19|20)\d{2})", re.I)
            years = []
            run = []
            for cell in cells[:best_idx] + [""]:
                match = year_cell.fullmatch(cell)
                if match:
                    run.append(match.group(1))
                elif run:
                    years = run
                    run = []

            if len(years) != len(values) or len(set(years)) != len(years):
                return None

            requested = set(re.findall(r"(?:\bFY\s*|\b)((?:19|20)\d{2})\b", query, re.I))
            if requested.difference(years):
                return None
            parts = [f"{year}: {value}" for year, value in zip(years, values)
                     if not requested or year in requested]
            return (f"{best_label} -> " + " | ".join(parts), best_label)

        return None



    @classmethod
    def _split_into_candidates(cls, text: str) -> List[Tuple[str, bool]]:
        """Splits text into meaningful semantic candidates (sentences, bullet items, footnotes, table segments)."""
        candidates: List[Tuple[str, bool]] = []

        # 1. Detect Footnotes like (1) Singapore represented... or Footnote 1: ...
        footnote_pattern = re.compile(r"(\(\d+\)\s+[A-Z][^\n]+)")
        for fn in footnote_pattern.findall(text):
            if len(fn.strip()) > 20:
                candidates.append((fn.strip(), False))

        # 2. Split lines for table rows vs standard narrative text
        lines = text.split("\n")
        running_header_pattern = re.compile(
            r"(?:\|\s*)?(?:Financial\s+Statements|Notes\s+to\s+(?:Condensed\s+)?Financial\s+Statements|Table\s+of\s+Contents|Part\s+[I|V|X]+|Item\s+\d+[A-Z]?)(?:\s*\|\s*(?:Financial\s+Statements|Notes\s+to\s+(?:Condensed\s+)?Financial\s+Statements|Table\s+of\s+Contents|\d+))*\s*(?:\|\s*)?",
            re.IGNORECASE
        )

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Strip embedded running headers like "Financial Statements | Notes to Financial Statements | 8 | Table of Contents"
            clean_line = running_header_pattern.sub(" ", line_str).strip()
            # Clean leading/trailing pipes and bullets
            clean_line = re.sub(r"^[\|\s]+", "", clean_line).strip()
            if not clean_line or len(clean_line) < 15:
                continue

            # Check if this line is genuinely a tabular row (multiple short cells or row-to-text with =)
            cells = [c.strip() for c in clean_line.split("|") if c.strip()]
            is_true_table = (
                (len(cells) >= 3 and all(len(c) < 70 for c in cells) and any(re.search(r"\d", c) for c in cells))
                or (("=" in clean_line or ";" in clean_line) and any(y in clean_line for y in ["2022", "2023", "2024", "2025", "Years ended", "Months Ended"]) and any(c in clean_line for c in ["$", "%", "USD", "shares"]))
            )

            if is_true_table:
                # Genuine table row
                candidates.append((clean_line, True))
            else:
                # Narrative paragraph (even if it had pipe artifacts): split by bullets (*, •) and sentence boundaries
                # Remove isolated stray pipes from narrative text
                narrative_body = re.sub(r"\|+", " ", clean_line)
                bullet_parts = re.split(r"(?:\s*[\*\•]\s+|\n\s*[-*]\s+)", narrative_body)
                for bp in bullet_parts:
                    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(\"])", bp.strip())
                    for s in sentences:
                        s_clean = s.strip()
                        s_clean = running_header_pattern.sub("", s_clean).strip()
                        s_clean = re.sub(r"^[\•\*\-\s]+", "", s_clean).strip()
                        if len(s_clean) > 20:
                            candidates.append((s_clean, False))

        # Boilerplate phrases to ignore as standalone answers
        boilerplate_regex = re.compile(
            r"^(?:table of contents|index to financial statements|part [i|v|x]+|item \d+[a-z]?|notes to (?:condensed )?consolidated financial statements|financial statements and supplementary data|\d+)\.?$",
            re.IGNORECASE
        )

        return [
            (cand, is_tbl) for cand, is_tbl in candidates
            if not boilerplate_regex.match(cand.strip()) and len(cand.strip()) > 15
        ]

    @classmethod
    def _clean_answer_text(cls, text: str) -> str:
        """Cleans extracted candidate string into a concise, readable fact."""
        cleaned = text.strip()
        # Strip running page header patterns
        cleaned = re.sub(
            r"^(?:Financial\s+Statements\s+|Notes\s+to\s+(?:Condensed\s+)?Financial\s+Statements\s+|\d+\s+|Table\s+of\s+Contents\s*)+",
            "",
            cleaned,
            flags=re.IGNORECASE
        ).strip()
        cleaned = re.sub(r"^[\|\s\•\*\-]+", "", cleaned).strip()
        cleaned = re.sub(r"[\|\s]+$", "", cleaned).strip()
        if "|" in cleaned:
            cells = [c.strip() for c in cleaned.split("|") if c.strip() and c.strip() != "$"]
            cleaned = " | ".join(cells)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    @classmethod
    def _highlight_in_text(cls, body: str, target: str) -> str:
        """Surrounds the target sentence inside the body text with visual highlight tags."""
        if not target:
            return body
        if target in body:
            return body.replace(target, f"[bold green]{target}[/bold green]")
        escaped_target = re.escape(target[:35])
        return re.sub(f"({escaped_target}[^\n.!?]*[.!?]?)", r"[bold green]\1[/bold green]", body, count=1)



