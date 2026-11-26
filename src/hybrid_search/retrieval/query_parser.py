"""Reads a question before searching: which company and filing type it asks about.

Upstream never looks at the question, so "How does Microsoft describe risks from AI
regulation?" returned Apple chunks, and even with a MSFT filter the word "Microsoft"
pulled up chunks that merely mention the name. The parser turns company names and
form codes into a metadata filter and removes them from the text that gets embedded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from hybrid_search.models.filter import MetadataFilter

# Names people use that are not derivable from the legal name in companies.yaml.
EXTRA_ALIASES: Dict[str, List[str]] = {
    "GOOGL": ["google"],
    "META": ["facebook"],
    "TSM": ["tsmc", "taiwan semiconductor"],
    "AMD": ["advanced micro devices"],
    "LLY": ["lilly"],
    "JPM": ["jpmorgan", "jp morgan", "j.p. morgan"],
    "VFS": ["vinfast"],
}

_LEGAL_SUFFIX = re.compile(
    r"\s*(,?\s*(inc|incorporated|corp|corporation|co|company|ltd|limited|plc|platforms|auto|holdings|group|mfg)\.?)+$|\s*&\s*co\.?$",
    re.I,
)
# A name right after these words is context ("competition from Tesla"), not the subject.
_CONTEXT_CUE = re.compile(
    r"(?:\b(?:competition|compete|competes|competing|competitors?|rivals?)\s+(?:from|with|against|such\s+as|like|including)"
    r"|\b(?:versus|vs\.?|than|against))\s*$",
    re.I,
)
_FORM = re.compile(r"\b(10-K|10-Q|20-F)\b", re.I)
_CODE_TOKEN = re.compile(r"\b[A-Z]{1,6}[- ]?\d+[A-Z]?\b|\b\d{2,}[A-Z]{1,3}\b|\"[^\"]+\"")  # ASC 606, MI300, CET1, 340B
_NOT_CODE = re.compile(r"^(?:(?:19|20)\d{2}|(?:FY|Q)[- ]?\d+)$")  # years and periods are not identifiers
# Short names that are also ordinary words: only a capitalised mention counts as the company.
_PROPER_NOUN_ONLY = {"meta", "apple", "amazon"}


@dataclass
class ParsedQuery:
    original: str
    text: str                                   # what gets embedded and matched
    tickers: List[str] = field(default_factory=list)          # companies the question is about
    context_tickers: List[str] = field(default_factory=list)  # mentioned only as competitor/comparison
    document_types: List[str] = field(default_factory=list)
    query_type: str = "balanced"                # "code", "concept" or "balanced"

    def merge_into(self, user_filter: Optional[MetadataFilter]) -> Optional[MetadataFilter]:
        """Adds parsed constraints only where the user did not set that field."""
        merged = user_filter.model_copy() if user_filter else MetadataFilter()
        if self.tickers and not merged.tickers:
            merged.tickers = list(self.tickers)
        if self.document_types and not merged.document_types:
            merged.document_types = list(self.document_types)
        return None if merged.is_empty() else merged


def short_name(legal_name: str) -> str:
    """'Apple Inc.' -> 'apple', 'JPMorgan Chase & Co.' -> 'jpmorgan chase'."""
    name = legal_name.strip()
    while True:
        cut = re.sub(r"\s+(?:and|&)$", "", _LEGAL_SUFFIX.sub("", name), flags=re.I)  # "Eli Lilly and Company"
        if cut == name:
            return name.lower()
        name = cut


class QueryParser:
    def __init__(self, companies: Sequence):
        """companies: objects with .ticker and .name (CompanyConfig from config/companies.yaml)."""
        aliases: List[Tuple[str, str]] = []
        self.tickers = {c.ticker.upper() for c in companies}
        for c in companies:
            names = {short_name(c.name), *EXTRA_ALIASES.get(c.ticker.upper(), [])}
            aliases += [(n, c.ticker.upper()) for n in names if len(n) >= 3]
        # Longest first so "taiwan semiconductor" wins over a shorter overlapping alias.
        self._aliases = sorted(aliases, key=lambda a: len(a[0]), reverse=True)

    def _find_mentions(self, query: str) -> List[Tuple[int, int, str]]:
        spans: List[Tuple[int, int, str]] = []
        taken = [False] * len(query)

        def add(m: re.Match, ticker: str) -> None:
            s, e = m.span()
            if not any(taken[s:e]):
                spans.append((s, e, ticker))
                for i in range(s, e):
                    taken[i] = True

        for alias, ticker in self._aliases:
            pattern = r"(?<![\w.])" + re.escape(alias).replace(r"\ ", r"\s+") + r"(?:['’]s)?(?!\w)"
            for m in re.finditer(pattern, query, re.I):
                if alias in _PROPER_NOUN_ONLY and not m.group(0)[0].isupper():
                    continue
                add(m, ticker)
        # Ticker symbols only in upper case, so "meta" or "amd" in normal prose are not tickers.
        for ticker in self.tickers:
            for m in re.finditer(r"(?<![\w$])" + re.escape(ticker) + r"(?:['’]s)?(?!\w)", query):
                add(m, ticker)
        return sorted(spans)

    def parse(self, query: str) -> ParsedQuery:
        subjects: List[str] = []
        context: List[str] = []
        remove: List[Tuple[int, int]] = []
        for s, e, ticker in self._find_mentions(query):
            if _CONTEXT_CUE.search(query[:s]):
                if ticker not in context:
                    context.append(ticker)
            else:
                if ticker not in subjects:
                    subjects.append(ticker)
                remove.append((s, e))

        forms = sorted({m.group(1).upper() for m in _FORM.finditer(query)})

        # One subject: say "the company", the way filings refer to themselves. Several: drop the names.
        replacement = "the company" if len(subjects) == 1 else ""
        edits = [(s, e, replacement + ("'s" if re.search(r"['’]s$", query[s:e]) and replacement else ""))
                 for s, e in remove]
        edits += [(m.start(), m.end(), "") for m in _FORM.finditer(query)]
        text = query
        for s, e, new in sorted(edits, reverse=True):
            text = text[:s] + " " + new + " " + text[e:]
        if len(subjects) > 1:
            text = re.sub(r"\b(?:and|,)\s+(?=(?:and\b|,|\s)*\b(?:describe|discuss|say|report)\b)", "", text)
        text = re.sub(r"\s+([?.,!])", r"\1", re.sub(r"\s{2,}", " ", text)).strip(" ,")
        rest = re.sub(r"\bthe company(?:'s)?", "", text)
        if not re.search(r"\w", rest):  # question was only a name, keep it as typed
            text = query

        return ParsedQuery(
            original=query,
            text=text,
            tickers=subjects,
            context_tickers=[t for t in context if t not in subjects],
            document_types=forms,
            query_type=classify(text),
        )


def classify(text: str) -> str:
    """'code' when the question holds an identifier BM25 should match exactly, 'concept' for long plain questions."""
    codes = [m.group(0) for m in _CODE_TOKEN.finditer(text) if not _NOT_CODE.match(m.group(0))]
    if codes:
        return "code"
    if len(re.findall(r"\w+", text)) >= 8:
        return "concept"
    return "balanced"
