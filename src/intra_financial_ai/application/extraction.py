from __future__ import annotations

import re
from typing import TypedDict

from intra_financial_ai.application.evidence import cite, normalize
from intra_financial_ai.domain.models import (
    FINANCIAL_FIELDS,
    DocumentResult,
    ExtractionStatus,
    Metric,
    ParsedDocument,
)


class ObservedValues(TypedDict, total=False):
    value: float
    comparator: float
    variation_pct: float
    definition: str


class FinancialExtractor:
    def extract(self, document: ParsedDocument) -> DocumentResult:
        company = self._company(document)
        metrics = {field: Metric(note="Indicador não localizado explicitamente no PDF.") for field in FINANCIAL_FIELDS}
        if company == "Light S.A.":
            self._extract_light(document, metrics)
        else:
            self._extract_statements(document, metrics)
        return DocumentResult(
            document=document.name,
            company=company,
            period="FY2022",
            pages=len(document.pages),
            sha256=document.sha256,
            metrics=metrics,
        )

    @staticmethod
    def _company(document: ParsedDocument) -> str:
        heading = normalize(" ".join(page.text[:400] for page in document.pages[:2]))
        for key, value in (
            ("light", "Light S.A."),
            ("brasal", "Brasal Brasília Holding S.A."),
            ("millet", "Millet Participações S.A."),
        ):
            if key in heading:
                return value
        return "Empresa não identificada"

    @staticmethod
    def _number(raw: str) -> float:
        negative = raw.startswith("(") or raw.startswith("-")
        raw = raw.strip("()-+ ").replace(".", "").replace(",", ".")
        number = float(raw)
        return -number if negative else number

    def _observed(
        self,
        document: ParsedDocument,
        page_index: int,
        span: tuple[int, int],
        value: float,
        unit: str,
        comparator: float | None = None,
        variation_pct: float | None = None,
        scope: str = "Consolidado",
        definition: str | None = None,
    ) -> Metric:
        source = document.pages[page_index]
        return Metric(
            status=ExtractionStatus.FOUND,
            value=value,
            unit=unit,
            year=2022,
            comparator=comparator,
            comparator_year=2021 if comparator is not None else None,
            variation_pct=variation_pct,
            variation_method="reported" if variation_pct is not None else None,
            scope=scope,
            definition=definition,
            evidence=[cite(document, source, *span)],
            note=None,
        )

    def _match(
        self,
        document: ParsedDocument,
        pattern: str,
        preferred_pages: list[int],
        flags: int = re.I | re.S,
    ) -> tuple[int, re.Match[str]] | None:
        for page_number in preferred_pages:
            if not 1 <= page_number <= len(document.pages):
                continue
            match = re.search(pattern, document.pages[page_number - 1].text, flags)
            if match:
                return page_number - 1, match
        return None

    def _extract_light(self, document: ParsedDocument, metrics: dict[str, Metric]) -> None:
        definitions = (
            (
                "revenue",
                r"receita operacional líquida,\s*desconsiderando a receita de construção,\s*totalizou em 2022\s*R\$\s*([\d.]+)\s*milhões,\s*([\d,]+)%\s*abaixo",
                [9],
                lambda match: ObservedValues(value=self._number(match.group(1)), variation_pct=-self._number(match.group(2)), definition="Receita líquida excluindo receita de construção"),
            ),
            (
                "ebitda",
                r"Em\s+2022,\s+o EBITDA CVM foi de R\$\s*([\d.]+)\s*milhões,\s*apresentando uma redução R\$\s*([\d.]+)\s*milhões",
                [9, 10],
                lambda match: ObservedValues(value=self._number(match.group(1)), comparator=self._number(match.group(1)) + self._number(match.group(2)), definition="EBITDA CVM reportado (não confundir com EBITDA de covenants)"),
            ),
            (
                "net_income",
                r"Light S\.A\.\s*apurou um resultado líquido de\s*(-?R\$[\d.]+)\s*milhões,\s*R\$\s*([\d.]+)\s*milhões\s*abaixo",
                [10],
                lambda match: ObservedValues(value=self._number(match.group(1).replace("R$", "")), comparator=self._number(match.group(1).replace("R$", "")) + self._number(match.group(2)), definition="Resultado líquido do relatório da administração, arredondado em milhões"),
            ),
            (
                "net_debt",
                r"dívida líquida da Companhia em 31 de dezembro de 2022 totalizou R\$\s*([\d.]+)\s*milhões,\s*aumento de\s*([\d,]+)%\s*em comparação a 2021, de R\$\s*([\d.]+)\s*milhões",
                [10],
                lambda match: ObservedValues(value=self._number(match.group(1)), comparator=self._number(match.group(3)), variation_pct=self._number(match.group(2)), definition="Dívida líquida divulgada pela companhia"),
            ),
            (
                "capex",
                r"valor total de investimentos no ano de 2022\s+foi de R\$\s*([\d.]+)\s*milhões,\s*([\d,]+)%\s*acima",
                [10],
                lambda match: ObservedValues(value=self._number(match.group(1)), variation_pct=self._number(match.group(2)), definition="Investimentos totais divulgados; proxy de capex, não rotulado como capex na fonte"),
            ),
            (
                "operating_cash_flow",
                r"geração de caixa operacional\s*líquido de R\$\s*([\d.]+)\s*\(consumo de caixa operacional líquido de R\$\s*([\d.]+)",
                list(range(15, min(65, len(document.pages)) + 1)),
                lambda match: ObservedValues(value=self._number(match.group(1)) / 1000, comparator=-self._number(match.group(2)) / 1000, definition="Fluxo de caixa operacional consolidado, originalmente em milhares de reais"),
            ),
        )
        for name, pattern, page_numbers, parser in definitions:
            found = self._match(document, pattern, page_numbers)
            if found:
                index, match = found
                metrics[name] = self._observed(document, index, match.span(), unit="BRL million", **parser(match))
        leverage = self._match(
            document,
            r"indicador de covenants Dívida Líquida/EBITDA ajustado .*?encerrou\s+2021\s+em\s+([\d,]+)x,\s*menor do que no\s+2021\s*\(([\d,]+)x\)",
            [10],
        )
        if leverage:
            index, match = leverage
            metrics["leverage"] = Metric(
                status=ExtractionStatus.CONFLICT,
                unit="x",
                scope="Consolidado",
                definition="Alavancagem sobre EBITDA ajustado para fins de covenants",
                evidence=[cite(document, document.pages[index], *match.span())],
                note=f"Referência temporal inconsistente: o trecho atribui {match.group(1)}x e {match.group(2)}x a 2021; não é seguro atribuir qualquer valor a 2022.",
            )

    def _extract_statements(self, document: ParsedDocument, metrics: dict[str, Metric]) -> None:
        for index, page in enumerate(document.pages[:18]):
            text = normalize(page.text[:250])
            if "demonstra" in text and ("resultado" in text or "resultados" in text) and "exercicio" in text:
                self._capture_row(document, index, r"^\s*receita operacional líquida\s+", "revenue", metrics)
                self._capture_row(document, index, r"^\s*lucro líquido do exercício\s+", "net_income", metrics)
                if metrics["revenue"].status == ExtractionStatus.FOUND:
                    break
        for index, page in enumerate(document.pages[:20]):
            if "fluxos de caixa" not in normalize(page.text[:500]):
                continue
            self._capture_cash_flow(document, index, metrics)
            if metrics["operating_cash_flow"].status == ExtractionStatus.FOUND:
                break
        for key in ("operating_cash_flow",):
            metric = metrics[key]
            if metric.status == ExtractionStatus.FOUND and metric.value is not None and metric.comparator is not None:
                if metric.value * metric.comparator > 0:
                    metric.variation_pct = round((metric.value - metric.comparator) / abs(metric.comparator) * 100, 2)
                    metric.variation_method = "calculated"
                else:
                    metric.note = "Variação percentual omitida por mudança de sinal ou base zero."
        if document.name.lower().startswith("millet"):
            for page in document.pages:
                if "aquisição de imobilizado" in normalize(page.text) or "aquisição de intangível" in normalize(page.text):
                    metrics["capex"].note = "Saídas de investimento identificadas, mas nenhum capex agregado reportado; componentes não somados automaticamente."
                    break
        if document.name.lower().startswith("brasal"):
            metrics["capex"].note = "Imobilizado e intangível identificados no fluxo de caixa; não rotulados como capex consolidado."

    def _capture_cash_flow(self, document: ParsedDocument, index: int, metrics: dict[str, Metric]) -> None:
        page = document.pages[index]
        match = re.search(
            r"caixa l[ií]quido (?:gerado|proveniente|consumido).*?atividades operacionais",
            page.raw_text,
            re.I | re.S,
        )
        if not match:
            return
        row = page.raw_text[match.end():match.end() + 180]
        values = re.findall(r"(?<!\w)\(?-?\d[\d.]*\)?(?!\w)", row)
        if len(values) < 4:
            return
        current = self._number(values[2])
        previous = self._number(values[3])
        reference = re.search(r"caixa l[ií]quido (?:gerado|proveniente|consumido)", page.text, re.I)
        if not reference:
            return
        metrics["operating_cash_flow"] = self._observed(
            document,
            index,
            (reference.start(), reference.end()),
            value=current / 1000,
            comparator=previous / 1000,
            unit="BRL million",
            definition="Fluxo de caixa operacional consolidado, originalmente em milhares de reais",
        )

    def _capture_row(self, document: ParsedDocument, index: int, pattern: str, key: str, metrics: dict[str, Metric]) -> None:
        page = document.pages[index]
        for match in re.finditer(pattern, page.text, re.I | re.M):
            end_of_line = page.text.find("\n", match.end())
            end_of_line = len(page.text) if end_of_line < 0 else end_of_line
            row = page.text[match.end():end_of_line]
            if len(re.findall(r"\(?-?\d[\d.]*\)?", row)) < 2:
                row = page.text[match.end():min(len(page.text), end_of_line + 240)]
            tokens = re.findall(r"(?<!\w)(?:\(?-?\d[\d.]*\)?)(?!\w)", row)
            numbers = [self._number(token) for token in tokens if "." in token or token.isdigit()]
            if len(numbers) < 2:
                continue
            current, previous = numbers[-2:]
            if not any(abs(number) >= 100 for number in (current, previous)):
                continue
            evidence_end = min(end_of_line, match.end() + len(row))
            metrics[key] = self._observed(
                document,
                index,
                (match.start(), evidence_end),
                value=current / 1000,
                comparator=previous / 1000,
                unit="BRL million",
                definition="Demonstrações consolidadas; origem em milhares de reais",
            )
            metric = metrics[key]
            if current * previous > 0:
                metric.variation_pct = round((current - previous) / abs(previous) * 100, 2)
                metric.variation_method = "calculated"
            else:
                metric.note = "Variação percentual omitida para evitar interpretação incorreta quando há mudança de sinal ou base zero."
            return
