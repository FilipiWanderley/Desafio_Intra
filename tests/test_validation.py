from intra_financial_ai.application.evidence import verified
from intra_financial_ai.application.validation import FinancialValidator
from intra_financial_ai.domain.models import (
    DocumentResult,
    Evidence,
    ExtractionStatus,
    Metric,
    Page,
    ParsedDocument,
)


def test_citation_verification_uses_actual_page():
    doc = ParsedDocument(name="test.pdf", sha256="abc", pages=[Page(number=1, text="Receita líquida R$ 100 milhões")])
    good = Evidence(document="test.pdf", page=1, excerpt="Receita líquida R$ 100 milhões")
    wrong = Evidence(document="test.pdf", page=1, excerpt="Receita líquida R$ 900 milhões")
    assert verified(good, doc)
    assert not verified(wrong, doc)


def test_variation_mismatch_is_signaled():
    doc = ParsedDocument(name="test.pdf", sha256="abc", pages=[Page(number=1, text="Receita líquida R$ 100 milhões")])
    metric = Metric(status=ExtractionStatus.FOUND, value=100, comparator=50, variation_pct=20, year=2022, comparator_year=2021, unit="BRL million", evidence=[Evidence(document="test.pdf", page=1, excerpt="Receita líquida R$ 100 milhões")])
    result = DocumentResult(document="test.pdf", company="Test", period="FY2022", pages=1, sha256="abc", metrics={name: Metric() for name in ("revenue", "ebitda", "ebitda_margin", "net_income", "net_debt", "leverage", "operating_cash_flow", "capex")})
    result.metrics["revenue"] = metric
    issues = FinancialValidator().validate(result, doc)
    assert any(item.code == "VARIATION_MISMATCH" for item in issues)


def test_missing_is_not_zero():
    metric = Metric()
    assert metric.status == ExtractionStatus.NOT_FOUND
    assert metric.value is None
