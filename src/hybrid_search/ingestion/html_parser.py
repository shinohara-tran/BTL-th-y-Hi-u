"""HTML and iXBRL parser for SEC filing documents with generalized row-to-text table preservation."""

from __future__ import annotations

import re
import html
import warnings
from typing import List, Optional
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# Suppress XMLParsedAsHTMLWarning when BeautifulSoup parses SEC iXBRL/HTML documents
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class EdgarHtmlParser:
    """Parses SEC filing HTML/iXBRL documents into clean, searchable plain text with preserved tables."""

    @classmethod
    def _extract_table_unit(cls, table, soup) -> str:
        """Infers the currency and numerical scale from table headers or surrounding context."""
        candidates = []
        if table.caption:
            candidates.append(table.caption.get_text())

        # Scan previous sibling/ancestor tags up to 15 blocks to capture headers placed further above
        for elem in table.find_all_previous(["p", "div", "span", "h1", "h2", "h3", "h4"], limit=15):
            txt = elem.get_text(strip=True)
            if txt:
                candidates.append(txt)
                if elem.name in ["table", "h1"]:
                    break

        for tr in table.find_all("tr")[:5]:
            candidates.append(tr.get_text())

        context_str = " ".join(candidates)

        if re.search(r"in billions|dollars in billions|\(\$ in billions\)", context_str, re.IGNORECASE):
            return "billions of USD"
        if re.search(r"in millions|dollars in millions|\(\$ in millions\)", context_str, re.IGNORECASE):
            return "millions of USD"
        if re.search(r"in thousands|dollars in thousands|\(\$ in thousands\)", context_str, re.IGNORECASE):
            return "thousands of USD"
        if re.search(r"per share", context_str, re.IGNORECASE):
            return "USD per share"
        return "không rõ đơn vị"

    @classmethod
    def _clean_table_grid(cls, table) -> List[List[str]]:
        """Extracts and cleans table cells, eliminating empty spacers and merging detached currency/negative symbols."""
        grid: List[List[str]] = []
        for tr in table.find_all("tr"):
            raw_cells: List[str] = []
            for td in tr.find_all(["th", "td"]):
                txt = html.unescape(td.get_text()).replace("\xa0", " ").replace("\u200b", "").replace("\ufeff", "").strip()
                txt = re.sub(r"\s+", " ", txt)
                if txt:
                    raw_cells.append(txt)
            if not raw_cells:
                continue

            # Merge currency symbols ($), parenthetical negatives ((, )) into the adjacent number
            merged: List[str] = []
            i = 0
            while i < len(raw_cells):
                c = raw_cells[i]
                # Currency symbol ($) before number or dash
                if c in ["$", "€", "£", "¥"] and i + 1 < len(raw_cells):
                    next_c = raw_cells[i + 1]
                    if re.match(r"^[\(\d]", next_c):
                        merged.append(f"{c}{next_c}")
                        i += 2
                        continue
                    elif next_c in ["—", "-", "–"]:
                        merged.append(next_c)
                        i += 2
                        continue
                elif c == "(" and i + 1 < len(raw_cells):
                    next_c = raw_cells[i + 1]
                    if next_c in ["$", "€", "£", "¥"] and i + 2 < len(raw_cells):
                        val = raw_cells[i + 2]
                        if i + 3 < len(raw_cells) and raw_cells[i + 3] == ")":
                            merged.append(f"({next_c}{val})")
                            i += 4
                            continue
                        else:
                            merged.append(f"({next_c}{val}")
                            i += 3
                            continue
                    elif re.match(r"^[\$\d]", next_c):
                        if i + 2 < len(raw_cells) and raw_cells[i + 2] == ")":
                            merged.append(f"({next_c})")
                            i += 3
                            continue
                        else:
                            merged.append(f"({next_c}")
                            i += 2
                            continue
                elif re.match(r"^\(?[$\d,\.\-]+$", c) and i + 1 < len(raw_cells) and raw_cells[i + 1] == ")":
                    merged.append(f"{c})")
                    i += 2
                    continue

                merged.append(c)
                i += 1

            if merged:
                grid.append(merged)
        return grid

    @classmethod
    def _is_value_cell(cls, c: str) -> bool:
        """Determines if a cell contains a numeric value, currency, or tabular dash."""
        clean = re.sub(r"[\$,\s\(\)]", "", c)
        return bool(re.match(r"^\(?[$\d,\.\-]+(?:\.\d+)?\)?%?$", c) or clean in ["—", "-", "–", "—%", "N/A", "none"])

    @classmethod
    def _infer_row_unit(cls, label: str, base_unit: str, vals: Optional[List[str]] = None) -> str:
        """Determines exact unit for each specific row item avoiding incorrect blanket table units."""
        lbl_lower = label.lower()

        # 1. Shares (e.g. Basic shares, Diluted shares, Weighted-average shares)
        if "shares" in lbl_lower or "share-based" in lbl_lower or "denominator" in lbl_lower:
            if "per share" not in lbl_lower:
                if "thousand" in base_unit.lower() or any(len(re.sub(r"[^\d]", "", v)) >= 7 for v in (vals or [])):
                    return "thousands of shares"
                elif "million" in base_unit.lower():
                    return "millions of shares"
                return "shares"

        # 2. Explicit per share (e.g. Basic earnings per share, Diluted earnings per share)
        if "per share" in lbl_lower or "earnings per share" in lbl_lower:
            return "USD per share"

        # If values have $ and are small amounts (typical EPS like $6.08)
        if vals and all("$" in v or v.strip() in ["-", "—", "–", "N/A"] for v in vals if v.strip()):
            sample_nums = [float(re.sub(r"[^\d\.]", "", v)) for v in vals if re.search(r"\d", v)]
            if sample_nums and max(sample_nums) < 100:
                return "USD per share"

        # 3. Percentages
        if "%" in lbl_lower or "percent" in lbl_lower or "margin" in lbl_lower or "ratio" in lbl_lower:
            return "%"

        # 4. Financial totals (Income, Taxes, Provision, Sales, Revenue, Cost, Expense, Cash, Assets, Liabilities, Debt)
        if any(k in lbl_lower for k in [
            "income", "tax", "provision", "sales", "revenue", "cost", "expense",
            "assets", "liabilities", "cash", "debt", "proceeds", "payments",
            "operating", "total", "equity", "securities", "obligations", "numerator"
        ]):
            if "per share" in base_unit.lower():
                return "millions of USD"
            return base_unit

        # 5. Fallback when blanket table unit had "per share" but row is not an EPS line
        if "per share" in base_unit.lower():
            if vals and any(len(re.sub(r"[^\d]", "", v)) >= 5 for v in vals):
                return "thousands of shares"
            return "millions of USD"

        return base_unit

    @classmethod
    def _convert_table_to_row_text(cls, table, unit: str) -> Optional[str]:
        """Converts financial tables into rich, self-contained row-to-text sentences using generalized column headers."""
        grid = cls._clean_table_grid(table)
        if len(grid) < 2:
            return None

        # 1. Locate the first data row (row where >= 50% of following cells are values)
        data_row_idx = -1
        for idx, row in enumerate(grid):
            if len(row) < 2:
                continue
            # If this row is a header year row (e.g. ['Year Ended', '2024', '2023', '2022']), skip as header
            num_years = sum(1 for c in row if re.match(r"^(?:FY)?20[12]\d$", c.strip()))
            if num_years >= 2 and num_years >= len(row) - 1:
                continue
            # If row label looks like a header label (Year Ended, Months Ended, Three Months, etc.)
            if re.search(r"\b(year ended|months ended|as of|period ended)\b", row[0], re.IGNORECASE):
                continue

            val_count = sum(1 for c in row[1:] if cls._is_value_cell(c))
            if val_count >= 2 and val_count >= len(row[1:]) * 0.5:
                data_row_idx = idx
                break

        if data_row_idx <= 0:
            return None

        # 2. Extract column names and date context from header rows before data_row_idx
        candidate_headers = []
        for r in grid[:data_row_idx]:
            # Filter out single-cell category rows like ['Numerator:']
            if len(r) == 1 and r[0].endswith(":"):
                continue
            candidate_headers.append(r)

        if not candidate_headers:
            return None

        header_rows = candidate_headers
        date_context = ""
        col_names: List[str] = []
        first_data_vals_len = len(grid[data_row_idx]) - 1

        if len(header_rows) == 1:
            header_line = header_rows[0]
            if len(header_line) == 1:
                return None
            if len(header_line) == first_data_vals_len + 1:
                col_names = header_line[1:]
            else:
                col_names = header_line
        elif len(header_rows) >= 2:
            r0, r1 = header_rows[0], header_rows[1]
            if len(r0) == 1 and len(r1) > 1:
                date_context = r0[0]
                if len(r1) == first_data_vals_len + 1:
                    col_names = r1[1:]
                else:
                    col_names = r1
            elif len(r0) > 1 and len(r1) == len(r0) * 2:
                # Multi-tier period header like Three Months Ended (2 cols), Nine Months Ended (2 cols)
                col_names = []
                for i, c1 in enumerate(r1):
                    tier0 = r0[0] if i < len(r1) // 2 else r0[1]
                    col_names.append(f"{tier0} {c1}")
            else:
                last_header = header_rows[-1]
                if len(last_header) == first_data_vals_len + 1:
                    col_names = last_header[1:]
                else:
                    col_names = last_header
        else:
            return None

        # Clean column names (space before camelCase)
        cleaned_cols = []
        for c in col_names:
            c_clean = re.sub(r"([a-z])([A-Z])", r"\1 \2", c).strip()
            cleaned_cols.append(c_clean)

        # 3. Convert data rows into row-to-text statements
        sentences: List[str] = []
        current_section = ""
        for row in grid[data_row_idx:]:
            if len(row) < 2:
                if len(row) == 1 and not cls._is_value_cell(row[0]) and len(row[0]) < 100:
                    current_section = row[0].rstrip(":")
                continue
            val_count = sum(1 for c in row[1:] if cls._is_value_cell(c))
            if val_count == 0:
                if not cls._is_value_cell(row[0]) and len(row[0]) < 100:
                    current_section = row[0].rstrip(":")
                continue

            label = row[0]
            vals = row[1:]
            if len(label) > 120 or re.match(r"^[\$\d\s,\.\(\)\-\%]+$", label):
                continue

            full_label = label
            lbl_lower = label.lower().strip()
            # Context enrichment for generic subheaders like "Basic" and "Diluted"
            if lbl_lower in ["basic", "diluted"]:
                has_dollar = any("$" in v for v in vals)
                is_decimal = any(re.search(r"\b\d+\.\d{2}\b", v) for v in vals)
                if has_dollar or is_decimal:
                    full_label = f"{label} earnings per share"
                elif any(len(re.sub(r"[^\d]", "", v)) >= 5 for v in vals):
                    full_label = f"{label} shares"
                elif current_section:
                    full_label = f"{label} ({current_section})"
                else:
                    full_label = f"{label} earnings per share"

            if date_context and date_context not in full_label:
                full_label = f"{full_label} ({date_context})"

            row_unit = cls._infer_row_unit(full_label, unit, vals)

            pairings: List[str] = []
            cols_to_use = cleaned_cols[-len(vals):] if len(cleaned_cols) >= len(vals) else cleaned_cols
            for k, v in zip(cols_to_use, vals):
                pairings.append(f"{k} = {v}")

            if not pairings:
                continue

            pair_str = "; ".join(pairings)
            sentences.append(f"{full_label}: {pair_str}. Unit: {row_unit}.")

        if sentences:
            return "\n".join(sentences)
        return None

    @classmethod
    def parse_html_to_text(cls, html_content: str | bytes) -> str:
        """Converts raw filing HTML into clean narrative text preserving tabular structure with generalized row-to-text."""
        if isinstance(html_content, bytes):
            try:
                html_content = html_content.decode("utf-8")
            except UnicodeDecodeError:
                html_content = html_content.decode("latin-1", errors="ignore")

        soup = BeautifulSoup(html_content, "lxml")

        # Strip unneeded non-content tags
        for tag in soup(["script", "style", "meta", "link", "noscript", "ix:header", "ix:hidden"]):
            tag.decompose()

        # Transform tables with row-to-text preservation
        for table in soup.find_all("table"):
            table_unit = cls._extract_table_unit(table, soup)
            row_text = cls._convert_table_to_row_text(table, table_unit)

            # Check if there is an introductory lead-in paragraph immediately preceding the table
            intro_text = ""
            target_node = table
            while target_node.parent and target_node.parent.name in ["div", "span"] and target_node.parent != soup:
                target_node = target_node.parent

            curr_elem = target_node.previous_sibling
            for _ in range(5):
                if curr_elem is None:
                    break
                if hasattr(curr_elem, "get_text"):
                    ptxt = curr_elem.get_text(strip=True)
                    if ptxt:
                        if len(ptxt) < 300 and (ptxt.endswith(":") or re.search(r"\b(the following tables?|the tables? below|tables? shows?|were as follows:?)\b", ptxt, re.IGNORECASE)):
                            intro_text = ptxt
                            curr_elem.decompose()
                        break
                curr_elem = curr_elem.previous_sibling

            if not intro_text:
                prev_sib = table.find_previous_sibling(["p", "div", "span"])
                if prev_sib:
                    ptxt = prev_sib.get_text(strip=True)
                    if ptxt and len(ptxt) < 300:
                        if ptxt.endswith(":") or re.search(r"\b(the following tables?|the tables? below|tables? shows?|were as follows:?)\b", ptxt, re.IGNORECASE):
                            intro_text = ptxt
                            prev_sib.decompose()

            if row_text:
                if intro_text:
                    row_text = f"Table context: {intro_text}\n{row_text}"
                new_tag = soup.new_tag("div")
                new_tag.string = f"\n{row_text}\n"
                table.replace_with(new_tag)
            else:
                # Robust clean fallback: join non-empty cells with ", " instead of pipes |
                grid = cls._clean_table_grid(table)
                fallback_lines = []
                for row in grid:
                    if row:
                        fallback_lines.append(", ".join(row))
                fallback_str = "\n".join(fallback_lines)
                if intro_text:
                    fallback_str = f"Table context: {intro_text}\n{fallback_str}"
                new_tag = soup.new_tag("div")
                new_tag.string = f"\n{fallback_str}\n"
                table.replace_with(new_tag)

        # Insert newlines after block elements
        for tag in soup.find_all(["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "br", "li", "section", "article", "header", "footer", "blockquote", "hr"]):
            tag.append("\n")

        # Extract text
        text = soup.get_text()

        # Unescape HTML entities
        text = html.unescape(text)

        # Normalize line endings and non-breaking spaces
        text = text.replace("\xa0", " ").replace("\u200b", "").replace("\ufeff", "")
        text = re.sub(r"\r\n|\r", "\n", text)

        # Clean multiple spaces and tabs (preserving newlines)
        text = re.sub(r"[ \t]+", " ", text)

        # Clean excessive blank lines (more than 2 consecutive newlines)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Trim each line
        lines = [line.strip() for line in text.split("\n")]
        cleaned_text = "\n".join(lines).strip()
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

        # Remove SEC EDGAR running page headers / footers / next statements:
        cleaned_text = re.sub(r"(?:Apple|NVIDIA|Microsoft|Alphabet|Amazon|Tesla|Intel)\s+Inc\.?\s*\|\s*202\d\s+Form\s+10-[KQ]\s*\|\s*\d+", "", cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r"See accompanying Notes to (?:Consolidated |Condensed )?Financial Statements\.?", "", cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r"\bCONSOLIDATED STATEMENTS OF [A-Z\s]{4,40}\b", "", cleaned_text)
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text).strip()

        return cleaned_text
