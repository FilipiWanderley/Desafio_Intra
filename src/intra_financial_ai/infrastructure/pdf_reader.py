from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pymupdf as fitz

from intra_financial_ai.domain.models import Page, ParsedDocument


class DocumentReader:
    def __init__(self, max_mb: int = 30, max_pages: int = 200):
        self.max_bytes = max_mb * 1024 * 1024
        self.max_pages = max_pages

    def read(self, path: Path) -> ParsedDocument:
        path = path.resolve()
        if not path.is_file() or path.suffix.lower() != ".pdf":
            raise ValueError(f"Arquivo PDF inválido: {path.name}")
        if path.stat().st_size > self.max_bytes:
            raise ValueError(f"PDF excede limite permitido: {path.name}")
        with path.open("rb") as source:
            header = source.read(5)
        if header != b"%PDF-":
            raise ValueError(f"Cabeçalho PDF inválido: {path.name}")
        blob_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        pages = []
        with fitz.open(path) as pdf:
            if pdf.needs_pass:
                raise ValueError(f"PDF protegido: {path.name}")
            if len(pdf) > self.max_pages:
                raise ValueError(f"PDF excede limite de páginas: {path.name}")
            for index, source_page in enumerate(pdf):
                raw = source_page.get_text("text", sort=False)
                needs_order = index + 1 in ({7, 8, 9, 10, 11} if len(pdf) < 80 else {9, 10, 25})
                organized = source_page.get_text("text", sort=True) if needs_order else raw
                table_rows = self._financial_table_rows(organized)
                pages.append(Page(number=index + 1, text=organized, raw_text=raw, tables=[table_rows] if table_rows else []))
        if not any(page.text.strip() for page in pages):
            raise ValueError(f"PDF sem texto extraível: {path.name}")
        return ParsedDocument(name=path.name, pages=pages, sha256=blob_hash)

    @staticmethod
    def _financial_table_rows(text: str) -> list[list[str | None]]:
        heading = text[:550].lower()
        if not any(term in heading for term in ("demonstrações dos resultados", "demonstrações do resultado", "demonstração dos fluxos de caixa", "demonstrações dos fluxos de caixa")):
            return []
        rows = []
        for line in text.splitlines():
            items = re.findall(r"(?<!\w)\(?-?\d[\d.]*\)?(?!\w)", line)
            if len(items) < 2:
                continue
            label = re.split(r"\(?-?\d[\d.]*\)?", line, maxsplit=1)[0].strip()
            if len(label) < 3:
                continue
            rows.append([label, *items])
        return rows[:120]

    @staticmethod
    def extract_tables(path: Path, selected_pages: set[int]) -> dict[int, list[list[list[str | None]]]]:
        import pdfplumber

        found = {}
        with pdfplumber.open(path) as pdf:
            for index in selected_pages:
                if index < 1 or index > len(pdf.pages):
                    continue
                try:
                    tables = pdf.pages[index - 1].extract_tables()
                except (ValueError, TypeError):
                    tables = []
                found[index] = [table for table in tables if table]
        return found
