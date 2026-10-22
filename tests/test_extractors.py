from pathlib import Path

import pytest

from intra_financial_ai.application.extraction import FinancialExtractor
from intra_financial_ai.domain.models import ExtractionStatus
from intra_financial_ai.infrastructure.pdf_reader import DocumentReader

INPUT = Path(__file__).resolve().parents[1] / "data" / "input"

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("filename", "revenue", "income"),
    [
        ("light.pdf", 12107.0, -5673.0),
        ("brasal.pdf", 1325.059, 174.602),
        ("millet.pdf", 462.127, 18.891),
    ],
)
def test_real_financial_documents(filename, revenue, income):
    result = FinancialExtractor().extract(DocumentReader().read(INPUT / filename))
    assert result.metrics["revenue"].value == pytest.approx(revenue)
    assert result.metrics["net_income"].value == pytest.approx(income)
    assert result.metrics["revenue"].evidence[0].page > 0
    assert result.metrics["revenue"].unit == "BRL million"


@pytest.mark.parametrize("filename", ["brasal.pdf", "millet.pdf"])
def test_ebitda_is_not_invented(filename):
    result = FinancialExtractor().extract(DocumentReader().read(INPUT / filename))
    assert result.metrics["ebitda"].status == ExtractionStatus.NOT_FOUND
    assert result.metrics["leverage"].status == ExtractionStatus.NOT_FOUND


def test_light_leverage_conflict():
    result = FinancialExtractor().extract(DocumentReader().read(INPUT / "light.pdf"))
    assert result.metrics["leverage"].status == ExtractionStatus.CONFLICT
    assert "2021" in result.metrics["leverage"].note
