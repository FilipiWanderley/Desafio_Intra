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
    categories = {
        "drivers": "Desempenho",
        "risks": "Risco",
        "guidance": "Perspectivas",
        "events": "Evento",
        "tone": "Tom",
    }
    status_labels = {
        "answered": "Respondida",
        "partial": "Parcial",
        "not_found": "Sem evidência suficiente",
    }
    companies = report.documents
    headers = "".join(
        f"<th scope=\"col\">{html.escape(item.company)}</th>" for item in companies
    )
    rows = []
    for key, label in HEADINGS.items():
        cells = "".join(
            f'<td data-label="{html.escape(item.company, quote=True)}">'
            f"{html.escape(number(item.metrics[key]))}</td>"
            for item in companies
        )
        rows.append(
            f'<tr><th scope="row" data-label="Indicador">{html.escape(label)}</th>{cells}</tr>'
        )

    panels = []
    for item in companies:
        findings = []
        for finding in item.findings:
            tag = categories.get(finding.category, "Achado")
            citation = source(finding.evidence) or "Fonte não vinculada"
            findings.append(
                '<li class="finding">'
                f'<span class="tag tag-{html.escape(finding.category, quote=True)}">{html.escape(tag)}</span>'
                f"<p>{html.escape(finding.statement)}</p>"
                f'<small>{html.escape(citation)}</small></li>'
            )
        alerts = []
        for issue in item.issues:
            if issue.level == "info":
                continue
            label = "Atenção" if issue.level == "warning" else "Erro"
            citation = source(issue.evidence)
            alerts.append(
                f'<li class="alert alert-{html.escape(issue.level, quote=True)}">'
                f'<span class="tag">{html.escape(label)}</span> '
                f"<strong>{html.escape(issue.code)}</strong>"
                f"<p>{html.escape(issue.message)}</p>"
                f"<small>{html.escape(citation)}</small></li>"
            )
        finding_content = "".join(findings) or '<li class="empty">Nenhuma constatação qualitativa disponível.</li>'
        alert_content = "".join(alerts) or '<li class="empty">Nenhum alerta de validação.</li>'
        panels.append(
            '<article class="company-card">'
            f"<h3>{html.escape(item.company)}</h3>"
            '<div class="metrics">'
            f'<div><span>Receita líquida</span><strong>{html.escape(number(item.metrics["revenue"]))}</strong></div>'
            f'<div><span>Lucro líquido</span><strong>{html.escape(number(item.metrics["net_income"]))}</strong></div>'
            "</div><h4>Achados com origem</h4>"
            f'<ul class="findings">{finding_content}</ul>'
            "<h4>Alertas de validação</h4>"
            f'<ul class="alerts">{alert_content}</ul></article>'
        )

    answer_cards: list[str] = []
    for answer in report.answers:
        label = status_labels.get(answer.status, "Status não definido")
        citations = source(answer.evidence) or "Nenhuma evidência vinculada"
        answer_cards.append(
            f'<article class="answer-card status-{html.escape(answer.status, quote=True)}">'
            '<div class="answer-top">'
            f'<span class="status-pill">{html.escape(label)}</span>'
            f'<span class="question-number">PERGUNTA {len(answer_cards) + 1:02d}</span></div>'
            f"<h3>{html.escape(answer.question)}</h3>"
            f'<p class="answer-text">{html.escape(answer.answer)}</p>'
            '<div class="citation"><b>Rastreabilidade</b>'
            f"<small>{html.escape(citations)}</small></div></article>"
        )

    answered = sum(a.status == "answered" for a in report.answers)
    partial = sum(a.status == "partial" for a in report.answers)
    not_found = sum(a.status == "not_found" for a in report.answers)
    css = """
    :root{color-scheme:light;--ink:#152b48;--soft:#344b67;--muted:#6b7d93;--blue:#2859a8;--line:#e0e8f2;--bg:#f3f6fb;--gold:#d49a43;--green:#18794e;--amber:#96620b;--red:#a83333}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 Inter,system-ui,-apple-system,"Segoe UI",Arial,sans-serif;overflow-wrap:anywhere;-webkit-font-smoothing:antialiased}
    .hero{color:white;background:radial-gradient(ellipse at 90% 0%,#416ba2 0,transparent 38%),linear-gradient(125deg,#10233d,#28538c)}
    .hero-inner,main{width:min(1200px,100%);margin:auto}.hero-inner{padding:52px 28px 44px}.eyebrow{margin:0 0 12px;color:#c6d9f7;font-size:11px;font-weight:800;letter-spacing:.2em;text-transform:uppercase}
    h1{max-width:780px;margin:0;font-size:clamp(30px,4.5vw,48px);line-height:1.08;letter-spacing:-.035em}.lead{max-width:700px;color:#dce8fa;margin:15px 0}.run{display:inline-flex;gap:8px;flex-wrap:wrap;margin-top:10px;padding:7px 12px;border:1px solid #ffffff40;border-radius:99px;background:#ffffff12;font-size:12px}
    main{padding:28px 28px 55px}.note{display:flex;gap:12px;padding:17px 19px;background:#fffdf7;border:1px solid #f0dfbd;border-left:4px solid var(--gold);border-radius:14px;color:#5c4b31}.note p{margin:0}.note-icon{display:grid;place-items:center;flex:0 0 28px;height:28px;border-radius:8px;background:#fff0d2;font-weight:900}
    section{margin-top:36px}.section-head{display:flex;justify-content:space-between;align-items:end;gap:12px;margin-bottom:15px}.section-head h2{margin:0;font-size:clamp(20px,2.4vw,25px);letter-spacing:-.025em}.section-head p{margin:5px 0 0;color:var(--muted);font-size:13px}.index{color:#8da0b8;font-size:11px;font-weight:800;letter-spacing:.12em}
    .summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px}.summary article,.company-card,.answer-card{min-width:0;background:white;border:1px solid var(--line);border-radius:17px;box-shadow:0 10px 28px #162f4e0c}.summary article{padding:17px}.summary span{display:block;color:var(--muted);font-size:12px;font-weight:650}.summary strong{display:block;margin:5px 0;font-size:30px;line-height:1.2;letter-spacing:-.04em}.summary small{color:var(--muted);font-size:11px}
    .table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:17px;background:white;box-shadow:0 10px 28px #162f4e0c}.comparison{width:100%;min-width:760px;border-collapse:separate;border-spacing:0;font-size:13px}.comparison th,.comparison td{padding:14px 15px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}.comparison thead th{background:#eaf1fb;color:#304967;font-size:12px}.comparison tbody th{font-weight:750}.comparison tbody tr:nth-child(even){background:#f8faff}.comparison tbody tr:last-child>*{border-bottom:0}
    .company-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));align-items:stretch;gap:15px}.company-card{padding:21px}.company-card h3,.answer-card h3{margin:0;font-size:17px;line-height:1.4;letter-spacing:-.02em}.metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin:16px 0}.metrics div{min-width:0;padding:11px;background:#f5f8fd;border-radius:11px}.metrics span{display:block;color:var(--muted);font-size:10px;font-weight:700}.metrics strong{display:block;margin-top:4px;font-size:13px;line-height:1.4}
    .company-card h4{margin:19px 0 9px;font-size:11px;text-transform:uppercase;letter-spacing:.06em}.findings,.alerts{display:grid;gap:11px;margin:0;padding:0;list-style:none}.finding,.alert{padding-bottom:11px;border-bottom:1px solid #edf1f6}.finding:last-child,.alert:last-child{padding-bottom:0;border-bottom:0}.finding p,.alert p{margin:6px 0;color:var(--soft);font-size:13px}.finding small,.alert small{display:block;color:var(--muted);font-size:10px;line-height:1.5}
    .tag,.status-pill{display:inline-flex;width:fit-content;padding:4px 8px;border-radius:99px;background:#eef2f7;color:#52657d;font-size:10px;font-weight:800}.tag-risks{background:#fff1e9;color:#98502d}.tag-drivers{background:#edf4ff;color:#2859a8}.tag-guidance{background:#f1edff;color:#6447a6}.tag-events{background:#e9f7f4;color:#1b7668}.tag-tone{background:#f2f3f6;color:#596579}.alert{padding-left:10px;border-left:3px solid #e7b75d}.alert-error{border-left-color:#d76d6d}.empty{padding:11px;border-radius:9px;background:#f7f9fc;color:var(--muted);font-size:12px}
    .answers{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.answer-card{display:flex;flex-direction:column;gap:12px;padding:21px}.answer-top{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}.question-number{color:#91a0b4;font-size:10px;font-weight:800;letter-spacing:.1em}.answer-card h3{font-size:16px}.answer-text{margin:0;color:var(--soft);font-size:14px;line-height:1.7}.status-answered .status-pill{background:#eaf7ef;color:var(--green)}.status-partial .status-pill{background:#fff5df;color:var(--amber)}.status-not_found .status-pill{background:#fff0ef;color:var(--red)}.citation{display:grid;gap:4px;margin-top:auto;padding-top:12px;border-top:1px solid var(--line)}.citation b{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.08em}.citation small{color:#566b85;font-size:11px;line-height:1.5}
    .legend{display:flex;flex-wrap:wrap;align-items:center;gap:9px;margin-top:14px;padding:13px 15px;border:1px solid var(--line);border-radius:13px;background:#ffffffa8}.legend p{flex-basis:100%;margin:0;color:var(--muted);font-size:12px}.legend .status-pill{background:#eef2f7}.legend .good{background:#eaf7ef;color:var(--green)}.legend .warn{background:#fff5df;color:var(--amber)}.legend .missing{background:#fff0ef;color:var(--red)}
    footer{display:flex;justify-content:space-between;gap:18px;margin-top:40px;padding-top:18px;border-top:1px solid var(--line);color:var(--muted);font-size:11px}footer p{max-width:780px;margin:0}.brand{flex:0 0 auto;font-weight:800;letter-spacing:.12em;color:#8b9bb0}
    @media(max-width:980px){.hero-inner{padding:42px 23px 36px}main{padding:24px 23px 42px}.summary{grid-template-columns:repeat(2,minmax(0,1fr))}.company-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
    @media(max-width:680px){body{font-size:14px}.hero-inner{padding:34px 17px 28px}h1{font-size:clamp(28px,8vw,36px)}.lead{font-size:13px}main{padding:17px 13px 34px}.note{padding:13px;font-size:13px}.section-head{align-items:flex-start}.index{display:none}section{margin-top:28px}.summary{gap:9px}.summary article{padding:13px;border-radius:13px}.summary strong{font-size:25px}.table-wrap{overflow:visible;border:0;background:transparent;box-shadow:none}.comparison{display:block;min-width:0}.comparison thead{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.comparison tbody{display:grid;gap:9px}.comparison tbody tr{display:block;padding:6px 13px;border:1px solid var(--line);border-radius:13px;background:#fff;box-shadow:0 8px 22px #162f4e0b}.comparison tbody tr:nth-child(even){background:#fff}.comparison tbody th{display:block;width:100%;padding:8px 0 10px;border-bottom:1px solid var(--line);font-size:13px}.comparison tbody td{display:flex;justify-content:space-between;gap:12px;width:100%;padding:9px 0;border-bottom:1px solid #edf1f6;text-align:right;font-size:12px}.comparison tbody td::before{content:attr(data-label);flex:1 1 48%;color:var(--muted);font-size:11px;font-weight:750;text-align:left}.comparison tbody td:last-child{border-bottom:0}.company-grid,.answers{grid-template-columns:minmax(0,1fr);gap:11px}.company-card,.answer-card{padding:17px;border-radius:15px}.company-card h3{font-size:16px}footer{flex-direction:column;gap:9px}}
    @media(max-width:360px){.summary{grid-template-columns:minmax(0,1fr)}.metrics{grid-template-columns:minmax(0,1fr)}.run{border-radius:12px}}
    @media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
    @media print{body{background:#fff;font-size:10pt}.hero{-webkit-print-color-adjust:exact;print-color-adjust:exact}.hero-inner{padding:28px}main{max-width:none;padding:18px 0}.summary article,.company-card,.answer-card,.table-wrap{box-shadow:none}.comparison{min-width:0;font-size:8pt}.comparison th,.comparison td{padding:7px}.company-card,.answer-card,.summary article{break-inside:avoid}}
    """
    question_count = len(report.answers)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Relatório auditável de análise financeira com evidências por documento e página.">
<title>Intra | Inteligência Financeira</title>
<style>{css}</style>
</head>
<body>
<header class="hero"><div class="hero-inner">
<p class="eyebrow">INTRA / Inteligência financeira</p>
<h1>Análise inteligente de demonstrações financeiras</h1>
<p class="lead">Comparativo financeiro, achados documentais e respostas rastreáveis — sem preencher lacunas com suposições.</p>
<div class="run"><span>Exercício 2022</span><span aria-hidden="true">·</span><span>Execução {html.escape(report.run_id)}</span></div>
</div></header>
<main>
<aside class="note" aria-label="Premissas importantes"><span class="note-icon" aria-hidden="true">i</span>
<p><strong>Antes de interpretar os números:</strong> os documentos são demonstrações anuais de 2022. Indicadores ausentes não foram inventados. A receita da Light exclui construção; EBITDA CVM e EBITDA ajustado para covenants não são equivalentes. Valores ausentes não significam zero.</p></aside>
<section aria-labelledby="overview-title"><div class="section-head"><div><h2 id="overview-title">Visão geral</h2><p>Resumo da execução e das perguntas do analista.</p></div><span class="index">01 / RESUMO</span></div>
<div class="summary">
<article><span>Documentos analisados</span><strong>{len(companies)}</strong><small>PDFs nesta execução</small></article>
<article><span>Perguntas avaliadas</span><strong>{question_count}</strong><small>Perguntas obrigatórias</small></article>
<article><span>Respostas conclusivas</span><strong>{answered}</strong><small>Com evidência suficiente</small></article>
<article><span>Com ressalvas</span><strong>{partial + not_found}</strong><small>{partial} parciais · {not_found} sem evidência suficiente</small></article>
</div></section>
<section aria-labelledby="comparison-title"><div class="section-head"><div><h2 id="comparison-title">Comparativo financeiro</h2><p>Indicadores identificados nos documentos; ausência de dado é mantida explícita.</p></div><span class="index">02 / INDICADORES</span></div>
<div class="table-wrap"><table class="comparison" aria-label="Comparativo de indicadores financeiros por empresa"><thead><tr><th scope="col">Indicador</th>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>
<section aria-labelledby="companies-title"><div class="section-head"><div><h2 id="companies-title">Análise por companhia</h2><p>Números, achados com origem e alertas de validação.</p></div><span class="index">03 / EMPRESAS</span></div><div class="company-grid">{"".join(panels)}</div></section>
<section aria-labelledby="answers-title"><div class="section-head"><div><h2 id="answers-title">Perguntas do analista</h2><p>Conclusões, respostas parciais e ausência de evidência em estados distintos.</p></div><span class="index">04 / RESPOSTAS</span></div>
<div class="answers">{"".join(answer_cards)}</div>
<div class="legend" aria-label="Legenda dos estados das respostas"><p>Como interpretar os estados</p><span class="status-pill good">Respondida</span><span class="status-pill warn">Parcial</span><span class="status-pill missing">Sem evidência suficiente</span><p>Uma resposta parcial ou sem evidência suficiente não confirma que o fato não existe.</p></div></section>
<footer><p>Relatório gerado automaticamente a partir dos documentos fornecidos. Confira as evidências originais antes de tomar decisões financeiras. Este relatório apoia a análise e não substitui auditoria contábil ou julgamento profissional.</p><span class="brand">INTRA · FINANCIAL AI</span></footer>
</main></body></html>"""

def write_reports(report: AnalysisReport, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "report.md").write_text(markdown(report), encoding="utf-8")
    (folder / "report.html").write_text(html_report(report), encoding="utf-8")
