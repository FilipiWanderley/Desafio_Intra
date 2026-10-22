from __future__ import annotations

from intra_financial_ai.domain.models import (
    QUESTIONS,
    Answer,
    DocumentResult,
    Evidence,
    ExtractionStatus,
)


def _refs(reports: list[DocumentResult], field: str) -> list[Evidence]:
    return [e for result in reports for e in result.metrics[field].evidence]


def _findings(reports: list[DocumentResult], category: str) -> list[Evidence]:
    return [e for result in reports for finding in result.findings if finding.category == category for e in finding.evidence]


class QuestionAnswerer:
    def answer_required(self, reports: list[DocumentResult]) -> list[Answer]:
        return [
            self._margin(reports),
            self._revenue_drivers(reports),
            self._leverage(reports),
            self._shared_risks(reports),
            self._guidance(reports),
        ]

    @staticmethod
    def _margin(reports: list[DocumentResult]) -> Answer:
        eligible = [r for r in reports if r.metrics["ebitda_margin"].status == ExtractionStatus.FOUND]
        if len(eligible) != len(reports):
            missing = ", ".join(r.company for r in reports if r.metrics["ebitda_margin"].status != ExtractionStatus.FOUND)
            return Answer(question=QUESTIONS[0], answer=f"Não é possível determinar um ranking válido das três empresas: margem EBITDA explicitamente reportada não encontrada para {missing}. Não é correto tratar EBITDA ausente como zero.", status="not_found", evidence=_refs(reports, "ebitda") + _refs(reports, "revenue"))
        winner = max(eligible, key=lambda r: r.metrics["ebitda_margin"].value or float("-inf"))
        return Answer(question=QUESTIONS[0], answer=f"{winner.company}: {winner.metrics['ebitda_margin'].value:.2f}%.", status="answered", evidence=winner.metrics["ebitda_margin"].evidence)

    @staticmethod
    def _revenue_drivers(reports: list[DocumentResult]) -> Answer:
        parts = []
        evidences: list[Evidence] = []
        for r in reports:
            factors = [f for f in r.findings if f.category == "drivers"]
            if factors:
                parts.append(f"{r.company}: " + "; ".join(f.statement for f in factors))
                evidences.extend(e for f in factors for e in f.evidence)
            else:
                parts.append(f"{r.company}: motivo gerencial explícito não encontrado; a DRE comprova números, mas não sua causa.")
                evidences.extend(r.metrics["revenue"].evidence)
        return Answer(question=QUESTIONS[1], answer=" ".join(parts), status="partial", evidence=evidences)

    @staticmethod
    def _leverage(reports: list[DocumentResult]) -> Answer:
        above = [r for r in reports if r.metrics["leverage"].status == ExtractionStatus.FOUND and (r.metrics["leverage"].value or 0) > 3]
        unresolved = [r.company for r in reports if r.metrics["leverage"].status != ExtractionStatus.FOUND]
        answer = "; ".join(f"{r.company}: {r.metrics['leverage'].value:.2f}x" for r in above)
        if unresolved:
            answer = (answer + ". " if answer else "") + "Não é possível concluir para todas as empresas. Alavancagem ausente ou temporalmente conflitante em: " + ", ".join(unresolved) + "."
        return Answer(question=QUESTIONS[2], answer=answer, status="partial" if unresolved else "answered", evidence=_refs(reports, "leverage") + _refs(reports, "net_debt"))

    @staticmethod
    def _shared_risks(reports: list[DocumentResult]) -> Answer:
        taxonomy = {
            "inadimplência e crédito": ("inadimpl", "crédito"),
            "taxas de juros": ("juros",),
            "contingências": ("conting",),
        }
        matches = []
        sources: list[Evidence] = []
        for label, terms in taxonomy.items():
            members = []
            for report in reports:
                findings = [f for f in report.findings if f.category == "risks" and any(term in f.statement.lower() for term in terms)]
                if findings:
                    members.append(report.company)
                    sources.extend(e for f in findings for e in f.evidence)
            if len(members) >= 2:
                matches.append(f"{label} ({', '.join(members)})")
        if not matches:
            return Answer(question=QUESTIONS[3], answer="Não foi possível demonstrar, nas evidências classificadas, riscos compartilhados por pelo menos duas empresas.", status="not_found", evidence=_findings(reports, "risks"))
        return Answer(question=QUESTIONS[3], answer="; ".join(matches) + ".", status="answered", evidence=sources)

    @staticmethod
    def _guidance(reports: list[DocumentResult]) -> Answer:
        items = []
        sources: list[Evidence] = []
        for report in reports:
            prospects = [finding for finding in report.findings if finding.category == "guidance"]
            if prospects:
                items.append(f"{report.company}: " + "; ".join(f.statement for f in prospects))
                sources.extend(e for f in prospects for e in f.evidence)
            else:
                items.append(f"{report.company}: guidance para o próximo ano não encontrado.")
                sources.extend(report.metrics["revenue"].evidence)
        return Answer(question=QUESTIONS[4], answer=" ".join(items), status="partial", evidence=sources)
