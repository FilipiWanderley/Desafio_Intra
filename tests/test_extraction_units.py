import pytest

from intra_financial_ai.application.extraction import FinancialExtractor
from intra_financial_ai.domain.models import ExtractionStatus, Page, ParsedDocument


def test_extracts_financial_metrics_from_synthetic_document():
    document = ParsedDocument(
        name="brasal-synthetic.pdf",
        sha256="synthetic-hash",
        pages=[
            Page(number=1, text="Brasal Brasília Holding S.A."),
            Page(
                number=2,
                text=(
                    "Demonstrações do resultado do exercício\n"
                    "Receita operacional líquida 1.325.059 1.200.000\n"
                    "Lucro líquido do exercício 174.602 150.000"
                ),
            ),
        ],
    )

    result = FinancialExtractor().extract(document)

    revenue = result.metrics["revenue"]
    income = result.metrics["net_income"]

    assert result.company == "Brasal Brasília Holding S.A."
    assert revenue.status == ExtractionStatus.FOUND
    assert revenue.value == pytest.approx(1325.059)
    assert revenue.unit == "BRL million"
    assert revenue.evidence[0].page == 2

    assert income.status == ExtractionStatus.FOUND
    assert income.value == pytest.approx(174.602)

    assert result.metrics["ebitda"].status == ExtractionStatus.NOT_FOUND
