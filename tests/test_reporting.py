from intra_financial_ai.application.reporting import html_report
from intra_financial_ai.domain.models import (
    FINANCIAL_FIELDS,
    AnalysisReport,
    Answer,
    DocumentResult,
    Evidence,
    Finding,
    Issue,
    Metric,
    RunMetrics,
)


def sample_report() -> AnalysisReport:
    evidence = Evidence(
        document="brasal.pdf",
        page=2,
        excerpt="Risco de crédito mencionado no relatório.",
    )
    metrics = {name: Metric() for name in FINANCIAL_FIELDS}
    metrics["revenue"] = Metric(
        status="found",
        value=1325.059,
        unit="BRL million",
        evidence=[evidence],
    )
    return AnalysisReport(
        run_id="test-run-123",
        documents=[
            DocumentResult(
                document="brasal.pdf",
                company="Brasal S.A.",
                period="FY2022",
                pages=12,
                sha256="test-hash",
                metrics=metrics,
                findings=[
                    Finding(
                        category="risks",
                        statement="<script>alert(1)</script>",
                        evidence=[evidence],
                    )
                ],
                issues=[
                    Issue(
                        document="brasal.pdf",
                        code="SOURCE_CONFLICT",
                        level="warning",
                        message="Há uma divergência a revisar.",
                        evidence=[evidence],
                    )
                ],
            )
        ],
        answers=[
            Answer(
                question="Qual é o principal risco?",
                answer="Resposta parcial com base na evidência disponível.",
                status="partial",
                evidence=[evidence],
            ),
            Answer(
                question="O EBITDA foi encontrado?",
                answer="Não foi possível confirmar o indicador.",
                status="not_found",
            ),
        ],
        metrics=RunMetrics(run_id="test-run-123", llm_enabled=False),
    )


def test_html_report_has_mobile_layout_and_accessible_labels():
    rendered = html_report(sample_report())
    assert 'name="viewport"' in rendered
    assert 'class="comparison"' in rendered
    assert 'data-label="Brasal S.A."' in rendered
    assert "@media(max-width:680px)" in rendered
    assert 'aria-labelledby="answers-title"' in rendered
    assert "Documentos analisados" in rendered


def test_html_report_escapes_untrusted_document_content():
    rendered = html_report(sample_report())
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "<script>alert(1)</script>" not in rendered


def test_html_report_explains_answer_statuses_and_citations():
    rendered = html_report(sample_report())
    assert "Parcial" in rendered
    assert "Sem evidência suficiente" in rendered
    assert "brasal.pdf, p. 2" in rendered
    assert "Valores ausentes não significam zero." in rendered
