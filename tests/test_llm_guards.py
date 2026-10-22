from intra_financial_ai.domain.models import Page, ParsedDocument
from intra_financial_ai.infrastructure.llm_financial import FinancialCandidate, FinancialLLMAdapter


def test_grounded_candidate_acceptance():
    doc = ParsedDocument(name="sample.pdf", sha256="abc", pages=[Page(number=1, text="Consolidado Receita líquida 462.127 mil reais")])
    candidate = FinancialCandidate(field="revenue", value_raw="462.127", unit_raw="BRL thousand", year=2022, scope="Consolidado", page=1, exact_quote="Receita líquida 462.127 mil reais")
    metric = FinancialLLMAdapter().accept(doc, candidate)
    assert metric is not None
    assert metric.value == 462.127


def test_hallucinated_quote_is_rejected():
    doc = ParsedDocument(name="sample.pdf", sha256="abc", pages=[Page(number=1, text="Receita líquida 462.127 mil reais")])
    candidate = FinancialCandidate(field="ebitda", value_raw="900", unit_raw="BRL million", year=2022, scope="Consolidado", page=1, exact_quote="EBITDA de 900 milhões")
    assert FinancialLLMAdapter().accept(doc, candidate) is None


def test_segment_scope_is_rejected():
    doc = ParsedDocument(name="sample.pdf", sha256="abc", pages=[Page(number=1, text="Receita líquida 462.127 mil reais")])
    candidate = FinancialCandidate(field="revenue", value_raw="462.127", unit_raw="BRL thousand", year=2022, scope="Subsidiária", page=1, exact_quote="Receita líquida 462.127 mil reais")
    assert FinancialLLMAdapter().accept(doc, candidate) is None
