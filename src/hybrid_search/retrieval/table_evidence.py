"""Company-independent, conservative extraction from explicit row-to-text tables.

No fiscal calendar or missing unit is inferred from a filing date. Unsupported
or ambiguous rows remain available as source text, not as numerical answers.
"""
from __future__ import annotations

import re

ROW = re.compile(r"^(.+):\s+(.+?)\.\s+Unit:\s+(.+?)\.?$")
NUMBER = re.compile(r"(?:US\$|\$|USD\s*)?\s*(\(?-?\d[\d,]*(?:\.\d+)?\)?)\s*(%)?", re.I)


def canonical(text):
    text = text.lower().replace('’', "'").replace('-', ' ')
    text = re.sub(r"\bweighted\s+average\b", 'weighted average', text)
    text = re.sub(r"\b(?:net income|income|earnings) per (?:common )?share\b|\beps\b", 'eps', text)
    text = re.sub(r"\brevenues\b", 'revenue', text)
    text = re.sub(r"\bnet sales\b", 'revenue', text)
    text = re.sub(r"\bpercent(?:age)?\b", 'percentage', text)
    text = re.sub(r"\boutstanding\b", '', text) if 'weighted average' in text else text
    return set(re.findall(r'[a-z]+', text))


def metric_request(query, company='', ticker=''):
    """Recognize numeric metric questions; qualifiers remain part of the metric."""
    q = query.lower().replace('’', "'").replace('-', ' ')
    if re.search(r'\b(why|explain|describe|compare|difference|growth|change|increase|decrease|ratio|trend)\b', q):
        return None
    if len(set(re.findall(r'(?:\bfy\s*|\b)((?:19|20)\d{2})\b', q))) != 1:
        return None
    # Remove an explicitly possessive entity, not a hardcoded company list.
    q = re.sub(r"(?<=was )[^?]+?'s\s+|(?<=were )[^?]+?'s\s+", '', q)
    for name in (company, ticker):
        if name:
            q = re.sub(r'\b' + re.escape(name.lower()) + r'\b', '', q)
    q = re.sub(r'\b(?:first|second|third|fourth) quarter\b|\bq[1-4]\b', '', q)
    q = re.sub(r'\bin (?:thousands|millions|billions) of (?:dollars|usd)\b', '', q)
    words = canonical(q) - {
        'what','was','were','is','are','the','of','for','in','during','fiscal',
        'financial','year','fy','full','annual','whole','how','much','many',
        'did','have','report','reported','amount','its','a','an',
    }
    if not words.intersection({'revenue','income','profit','margin','eps','shares','assets','liabilities','expenses','cash','debt','research','dividends'}):
        return None
    kind = ('eps' if 'eps' in words else 'shares' if 'shares' in words
            else 'percent' if 'percentage' in words else 'money')
    return words, kind


def normalized_fact(query, body, period, company='', ticker='', filing_type=''):
    request = metric_request(query, company, ticker)
    if not request or not period:
        return None
    wanted, kind = request
    year, frequency = period
    facts = []
    context = ''
    for line in body.splitlines():
        line = line.strip()
        if line.startswith('Table context:'):
            context = line.lower()
            continue
        match = ROW.fullmatch(line)
        if not match:
            if line:
                context = ''
            continue
        label, pairs, unit = match.groups()
        clean_label = re.sub(r'\((?:loss|note \d+)\)', '', label, flags=re.I)
        clean_label = re.split(r'\s*\(+(?=years? ended|for the year|as of|in |three months|six months|nine months)', clean_label, maxsplit=1, flags=re.I)[0].strip(' :')
        label_words = canonical(clean_label)
        u = unit.lower().strip().rstrip('.')
        if kind == 'eps' and label_words in ({'net', 'income', 'basic'}, {'net', 'income', 'diluted'}):
            variant = 'basic' if 'basic' in label_words else 'diluted'
            label_words = {variant, 'eps'}
            clean_label = variant.capitalize() + ' earnings per share'
        if kind == 'percent' and 'margin' in label_words and u in {'%', 'percent', 'percentage'}:
            label_words.add('percentage')
            if 'percentage' not in clean_label.lower():
                clean_label += ' percentage'
        if wanted == {'services', 'revenue'}:
            if label_words == {'services'} and (
                re.search(r'\b(?:net sales|revenue) by category\b', context)
                or re.match(r'Total net sales:.*Unit: millions of USD\.$', body[body.index(line)+len(line):].lstrip('\n'), re.I | re.M)
            ):
                label_words = {'services', 'revenue'}
            if label_words == wanted:
                clean_label = 'Services net sales'
        # Total/plain revenue are equivalent only for a total/consolidated row.
        requested_words = wanted - {'total'}
        actual_words = label_words - {'total'}
        if actual_words != requested_words:
            continue
        if 'total' in wanted and 'total' not in label_words and not (
            'consolidated' in context or re.search(r'\(note \d+\)', label, re.I)
        ):
            continue
        if requested_words in ({'revenue'}, {'net','revenue'}) and 'total' not in label_words and not (
            'consolidated' in context or re.search(r'\(note \d+\)', label, re.I)
        ):
            # A bare Revenue row may belong to a region or segment.
            continue
        if wanted == {'total', 'revenue'}:
            clean_label = 'Total revenue'
        scale = re.fullmatch(r'(thousand|million|billion)s? of (usd|shares)', u)
        if kind == 'money':
            if u == 'usd':
                prefix, suffix = '$', ''
            elif scale and scale[2] == 'usd':
                prefix, suffix = '$', ' ' + scale[1]
            else:
                continue
        elif kind == 'shares':
            if u == 'shares':
                prefix, suffix = '', ' shares'
            elif scale and scale[2] == 'shares':
                prefix, suffix = '', ' ' + scale[1] + ' shares'
            else:
                continue
        elif kind == 'eps':
            if u != 'usd per share':
                continue
            prefix, suffix = '$', ' per share'
        else:
            if u not in {'%', 'percent', 'percentage'}:
                continue
            prefix, suffix = '', '%'
        selected = []
        for pair in pairs.split(';'):
            column, sep, value = pair.strip().partition(' = ')
            if not sep or set(re.findall(r'\b(?:19|20)\d{2}\b', column)) != {year}:
                continue
            period_text = label + ' ' + column
            interim = re.search(r'\b(three|six|nine|3|6|9) months?\b', period_text, re.I)
            if frequency == 'annual':
                if interim or re.search(r'\bq[1-4]\b|quarter', period_text, re.I):
                    continue
                if filing_type == '10-Q' and not re.search(r'years? ended|twelve months|12 months|annual', period_text, re.I):
                    continue
            else:
                quarter_labels = set(re.findall(r'\bQ([1-4])\s+(?:FY\s*)?((?:19|20)\d{2})\b', body, re.I))
                if quarter_labels != {(frequency, year)}:
                    continue
                if not interim or interim[1].lower() not in {'three','3'}:
                    continue
            number = NUMBER.fullmatch(value.strip())
            if not number or (number[2] and kind != 'percent'):
                continue
            if kind == 'shares' and re.search(r'\$|USD', value, re.I):
                continue
            selected.append(number[1])
        # Repeated years can represent currencies or quarter/YTD: never guess.
        if len(selected) != 1:
            continue
        display = f'FY{year}' if frequency == 'annual' else f'Q{frequency} FY{year}'
        facts.append((f'{clean_label} - {display}: {prefix}{selected[0]}{suffix}', line))
    unique = {answer for answer, _ in facts}
    return facts[0] if len(unique) == 1 else None
