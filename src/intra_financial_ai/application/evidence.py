from __future__ import annotations

import re
import unicodedata

from intra_financial_ai.domain.models import Evidence, Page, ParsedDocument


def normalize(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text)
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", plain).strip().casefold()


def excerpt(page: Page, start: int, end: int, width: int = 260) -> str:
    lo = max(0, start - width // 2)
    hi = min(len(page.text), end + width // 2)
    return re.sub(r"\s+", " ", page.text[lo:hi]).strip()


def cite(doc: ParsedDocument, page: Page, start: int, end: int, section: str | None = None) -> Evidence:
    return Evidence(document=doc.name, page=page.number, excerpt=excerpt(page, start, end), section=section)


def verified(evidence: Evidence, doc: ParsedDocument) -> bool:
    if evidence.document != doc.name or not (1 <= evidence.page <= len(doc.pages)):
        return False
    return normalize(evidence.excerpt) in normalize(doc.pages[evidence.page - 1].text)


def page_by_keyword(doc: ParsedDocument, keyword: str) -> list[Page]:
    needle = normalize(keyword)
    return [p for p in doc.pages if needle in normalize(p.text)]


def search_evidence(doc: ParsedDocument, terms: list[str], limit: int = 6) -> list[Evidence]:
    findings = []
    for page in doc.pages:
        for term in terms:
            match = re.search(re.escape(term), page.text, re.IGNORECASE)
            if match:
                findings.append(cite(doc, page, match.start(), match.end(), term))
                break
        if len(findings) >= limit:
            break
    return findings
