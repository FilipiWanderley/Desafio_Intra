from __future__ import annotations

import html
from pathlib import Path

from intra_financial_ai.domain.models import AnalysisReport, Evidence, ExtractionStatus, Metric

HEADINGS = {
    "revenue": "Receita líquida",
    "ebitda": "EBITDA",
    "ebitda_margin": "Margem EBITDA",
    "net_income": "Lucro líquido",
    "net_debt": "Dívida líquida",
    "leverage": "Alavancagem",
    "operating_cash_flow": "Caixa operacional",
    "capex": "Capex / Investimentos",
}


def source(evidence: list[Evidence]) -> str:
    return "; ".join(f"{item.document}, p. {item.page}" for item in evidence)


def number(metric: Metric) -> str:
    if metric.status == ExtractionStatus.CONFLICT:
        return "⚠ Conflito"
    if metric.status != ExtractionStatus.FOUND or metric.value is None:
        return "Não encontrado"
    formatted = f"{metric.value:,.3f}".replace(",", "~").replace(".", ",").replace("~", ".")
    if metric.unit == "BRL million":
        return f"R$ {formatted} mi"
    if metric.unit == "percent":
        return f"{formatted}%"
    return f"{formatted}x"


def markdown(report: AnalysisReport) -> str:
    output = [
        "# Análise Consolidada de Demonstrações Financeiras",
        "",
        f"Execução: `{report.run_id}` | Período: exercício findo em 31/12/2022 | Base: três PDFs originais",
        "",
        "## Premissas críticas",
        "",
        "Valores monetários apresentados em milhões de reais. Os PDFs se referem a 2022, não a trimestres de 2025. Comparações usam consolidado quando claramente identificável. Informação ausente é indicada explicitamente; não é convertida em zero. EBITDA CVM e EBITDA ajustado de covenants são conceitos diferentes. O valor de receita da Light exclui construção e não é plenamente comparável às outras DREs sem ajuste de escopo.",
        "",
        "## Resumo executivo",
        "",
    ]
    for doc in report.documents:
        risks = [f.statement for f in doc.findings if f.category == "risks"]
        output.extend(
            [
                f"### {doc.company}",
                f"- Receita líquida: **{number(doc.metrics['revenue'])}**; resultado líquido: **{number(doc.metrics['net_income'])}**.",
                f"- EBITDA: **{number(doc.metrics['ebitda'])}**; dívida líquida: **{number(doc.metrics['net_debt'])}**.",
                f"- Riscos identificados: {'; '.join(risks[:2]) if risks else 'não detalhados de forma inequívoca' }.",
                f"- Alertas: {sum(issue.level == 'warning' for issue in doc.issues)} aviso(s), {sum(issue.level == 'error' for issue in doc.issues)} erro(s) de validação.",
                "",
            ]
        )
    output.extend(["## Indicadores comparativos", "", "| Indicador | Light | Brasal | Millet |", "|---|---:|---:|---:|"])
    order = ["Light S.A.", "Brasal Brasília Holding S.A.", "Millet Participações S.A."]
    by_company = {d.company: d for d in report.documents}
    for key, label in HEADINGS.items():
        cells = [number(by_company[name].metrics[key]) if name in by_company else "Sem documento" for name in order]
        output.append(f"| {label} | {' | '.join(cells)} |")
    output.extend(["", "## Indicadores, comparação e evidências", ""])
    for doc in report.documents:
        output.append(f"### {doc.company}")
        for key, metric in doc.metrics.items():
            details = f"**{HEADINGS[key]}:** {number(metric)}"
            if metric.comparator is not None:
                details += f"; 2021: {number(Metric(status=ExtractionStatus.FOUND, value=metric.comparator, unit=metric.unit))}"
            if metric.variation_pct is not None:
                adjective = "calculada" if metric.variation_method == "calculated" else "informada"
                details += f"; variação {adjective}: {metric.variation_pct:+.2f}%"
            if metric.evidence:
                details += f" — {source(metric.evidence)}"
            if metric.note:
                details += f". {metric.note}"
            output.append(f"- {details}")
        output.append("")
    output.extend(["## Análise qualitativa", ""])
    for doc in report.documents:
        output.append(f"### {doc.company}")
        for category, title in (("drivers", "Drivers"), ("risks", "Riscos"), ("guidance", "Perspectivas/guidance"), ("events", "Eventos"), ("tone", "Tom")):
            candidates = [f for f in doc.findings if f.category == category]
            if candidates:
                for candidate in candidates:
                    output.append(f"- **{title}:** {candidate.statement} ({source(candidate.evidence)})")
            else:
                output.append(f"- **{title}:** Não encontrado explicitamente no documento.")
        output.append("")
    output.extend(["## Cinco perguntas obrigatórias", ""])
    for i, answer in enumerate(report.answers, 1):
        output.extend([f"### {i}. {answer.question}", answer.answer, "", f"**Fontes:** {source(answer.evidence) if answer.evidence else 'Não disponíveis / ausência de informação'}", ""])
    output.extend(["## Alertas de qualidade e lacunas", ""])
    for doc in report.documents:
        output.append(f"### {doc.company}")
        for issue in doc.issues:
            output.append(f"- **{issue.level.upper()} · {issue.code}:** {issue.message}" + (f" ({source(issue.evidence)})" if issue.evidence else ""))
        output.append("")
    output.extend(
        [
            "## Métricas de execução",
            "",
            f"- LLM habilitado: **{report.metrics.llm_enabled}**; modelo: {report.metrics.llm_model or 'não utilizado'}.",
            f"- Tokens contabilizados: entrada **{report.metrics.prompt_tokens}**, saída **{report.metrics.completion_tokens}**.",
            f"- Custo em USD: **{report.metrics.estimated_cost_usd:.6f}**." if report.metrics.estimated_cost_usd is not None else "- Custo em USD: **não calculado** sem tarifa contratual explicitamente configurada; tokens registrados para precificação externa.",
        ]
    )
    for timing in report.metrics.timings:
        output.append(f"- {timing.step}: {timing.seconds:.2f} s")
    output.extend(["", "_Relatório gerado automaticamente. Evidências devem ser conferidas antes de tomada de decisão financeira._", ""])
    return "\n".join(output)


def html_report(report: AnalysisReport) -> str:
    rows = []
    companies = report.documents
    for key, label in HEADINGS.items():
        cells = "".join(f"<td>{html.escape(number(item.metrics[key]))}</td>" for item in companies)
        rows.append(f"<tr><th>{html.escape(label)}</th>{cells}</tr>")
    heads = "".join(f"<th>{html.escape(item.company)}</th>" for item in companies)
    company_panels = []
    for item in companies:
        risk_html = "".join(f"<li>{html.escape(f.statement)}<span>{html.escape(source(f.evidence))}</span></li>" for f in item.findings)
        alerts = "".join(f"<li><strong>{html.escape(i.code)}</strong> — {html.escape(i.message)}</li>" for i in item.issues if i.level != "info")
        company_panels.append(f"<article><h3>{html.escape(item.company)}</h3><p>Receita: <b>{html.escape(number(item.metrics['revenue']))}</b> · Lucro: <b>{html.escape(number(item.metrics['net_income']))}</b></p><h4>Achados com origem</h4><ul>{risk_html or '<li>Nenhuma constatação qualitativa automática.</li>'}</ul><h4>Alertas</h4><ul>{alerts or '<li>Sem alertas críticos.</li>'}</ul></article>")
    qa = "".join(f"<article><h4>{html.escape(a.question)}</h4><p>{html.escape(a.answer)}</p><small>Fonte: {html.escape(source(a.evidence) or 'Não encontrada')}</small></article>" for a in report.answers)
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Intra · Financial Intelligence</title><style>:root{{--ink:#15263b;--blue:#315bb5;--bg:#f4f7fb;--border:#e1e8f1}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,"Segoe UI",Arial,sans-serif;line-height:1.55}}header{{background:linear-gradient(120deg,#11243e,#274c86);padding:55px min(7vw,80px);color:#fff}}header small{{letter-spacing:.18em;text-transform:uppercase;color:#b9d2fd}}header h1{{font-size:clamp(29px,4vw,46px);max-width:850px;line-height:1.12;margin:14px 0}}header p{{color:#d6e5fa}}main{{max-width:1170px;margin:auto;padding:30px 24px 80px}}h2{{margin-top:40px}}section{{margin:26px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(285px,1fr));gap:16px}}article{{border:1px solid var(--border);background:white;border-radius:14px;padding:22px;box-shadow:0 5px 20px #1b2b4310;min-width:0}}article h3{{margin-top:0}}article li{{margin:12px 0}}article li span,article small{{display:block;color:#617289;font-size:12px;margin-top:5px}}.scroll{{overflow-x:auto;border-radius:14px;border:1px solid var(--border);background:white}}table{{border-collapse:collapse;width:100%;min-width:760px}}th,td{{padding:14px;text-align:left;border-bottom:1px solid var(--border)}}thead th{{background:#edf3fb}}tbody th{{width:25%}}tbody tr:nth-child(even){{background:#f9fbfe}}.note{{background:#fff;padding:18px 22px;border-left:4px solid #cc9640;border-radius:6px}}footer{{color:#64748b;font-size:12px;margin-top:50px}}@media print{{header{{print-color-adjust:exact}}article{{break-inside:avoid}}body{{background:#fff}}}}</style></head><body><header><small>INTRA / Inteligência financeira</small><h1>Análise inteligente de demonstrações financeiras</h1><p>2022 · Light, Brasal e Millet · Execução {html.escape(report.run_id)}</p></header><main><div class="note"><strong>Premissa importante:</strong> os PDFs são demonstrações anuais de 2022. Indicadores ausentes não foram inventados. A receita da Light exclui a receita de construção; EBITDA de covenants e EBITDA CVM não são equivalentes.</div><section><h2>Comparativo financeiro</h2><div class="scroll"><table><thead><tr><th>Indicador</th>{heads}</tr></thead><tbody>{''.join(rows)}</tbody></table></div></section><section><h2>Análise por companhia</h2><div class="grid">{''.join(company_panels)}</div></section><section><h2>Perguntas do analista</h2><div class="grid">{qa}</div></section><footer>Gerado automaticamente a partir dos documentos fornecidos. Verifique as evidências originais antes de utilizar as informações em decisões financeiras.</footer></main></body></html>'''


def write_reports(report: AnalysisReport, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "report.md").write_text(markdown(report), encoding="utf-8")
    (folder / "report.html").write_text(html_report(report), encoding="utf-8")
