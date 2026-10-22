from __future__ import annotations

from intra_financial_ai.application.evidence import verified
from intra_financial_ai.domain.models import (
    FINANCIAL_FIELDS,
    DocumentResult,
    ExtractionStatus,
    Issue,
    ParsedDocument,
)


class FinancialValidator:
    def validate(self, result: DocumentResult, doc: ParsedDocument) -> list[Issue]:
        issues = []
        for name in FINANCIAL_FIELDS:
            metric = result.metrics[name]
            if metric.status == ExtractionStatus.NOT_FOUND:
                issues.append(Issue(document=doc.name, code="NOT_FOUND", level="info", metric=name, message=f"{name}: informação não encontrada explicitamente no documento."))
            if metric.status == ExtractionStatus.CONFLICT:
                issues.append(Issue(document=doc.name, code="SOURCE_CONFLICT", level="warning", metric=name, message=metric.note or "Divergência na origem.", evidence=metric.evidence))
            if metric.status == ExtractionStatus.FOUND:
                if metric.value is None or not metric.evidence:
                    issues.append(Issue(document=doc.name, code="INVALID_EXTRACTION", level="error", metric=name, message="Valor encontrado sem número ou sem evidência."))
                if metric.unit not in {"BRL million", "percent", "x"}:
                    issues.append(Issue(document=doc.name, code="INVALID_UNIT", level="error", metric=name, message=f"Unidade inconsistente: {metric.unit}"))
                if metric.year != 2022:
                    issues.append(Issue(document=doc.name, code="INVALID_PERIOD", level="error", metric=name, message="Período diferente de 2022."))
                if metric.comparator is not None and metric.comparator_year != 2021:
                    issues.append(Issue(document=doc.name, code="INVALID_COMPARISON", level="error", metric=name, message="Período comparativo incoerente."))
                if metric.value is not None and metric.comparator is not None and metric.variation_pct is not None:
                    if abs(metric.comparator) > 0:
                        expected = (metric.value - metric.comparator) / abs(metric.comparator) * 100
                        if abs(expected - metric.variation_pct) > 1.0:
                            issues.append(Issue(document=doc.name, code="VARIATION_MISMATCH", level="warning", metric=name, message=f"Variação informada {metric.variation_pct:.2f}% difere da calculada {expected:.2f}%.", evidence=metric.evidence))
            for evidence in metric.evidence:
                if not verified(evidence, doc):
                    issues.append(Issue(document=doc.name, code="CITATION_NOT_VERIFIED", level="error", metric=name, message=f"Trecho não confirmado na página {evidence.page}.", evidence=[evidence]))
        for finding in result.findings:
            for evidence in finding.evidence:
                if not verified(evidence, doc):
                    issues.append(Issue(document=doc.name, code="CITATION_NOT_VERIFIED", level="error", message="Citação qualitativa não verificada.", evidence=[evidence]))
        if result.company == "Light S.A.":
            revenue = result.metrics["revenue"]
            ebitda = result.metrics["ebitda"]
            if revenue.status == ExtractionStatus.FOUND and ebitda.status == ExtractionStatus.FOUND and revenue.value is not None and revenue.value != 0 and ebitda.value is not None:
                estimate = ebitda.value / revenue.value * 100
                issues.append(Issue(document=doc.name, code="MARGIN_SCOPE_NOTE", level="info", metric="ebitda_margin", message=f"Margem aritmética de referência: {estimate:.2f}% (EBITDA CVM / receita sem construção). Não marcada como margem divulgada; verificar consistência de denominador antes de comparação." , evidence=ebitda.evidence + revenue.evidence))
            if result.metrics["net_income"].status == ExtractionStatus.FOUND:
                issues.append(Issue(document=doc.name, code="ROUNDING_NOTE", level="info", metric="net_income", message="Relatório da administração apresenta montantes arredondados em milhões; demonstrações contábeis apresentam milhares de reais."))
        if result.company.startswith("Millet"):
            issues.append(Issue(document=doc.name, code="NET_INCOME_SCOPE", level="info", metric="net_income", message="Há lucro consolidado antes da atribuição aos não controladores e lucro atribuível à controladora; foi utilizado o primeiro na comparação."))
        for finding in result.findings:
            if finding.category == "guidance" and "qualitativa" in finding.statement.lower():
                issues.append(Issue(document=doc.name, code="GUIDANCE_SCOPE", level="info", message="Perspectiva qualitativa não pode ser tratada como meta financeira numérica."))
        return issues
