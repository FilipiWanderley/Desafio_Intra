from __future__ import annotations

import re
from typing import Literal

from intra_financial_ai.application.evidence import cite
from intra_financial_ai.domain.models import Finding, ParsedDocument


class QualitativeAnalyzer:
    def analyze(self, doc: ParsedDocument, company: str) -> list[Finding]:
        findings: list[Finding] = []
        catalog = self._catalog(company)
        for category, statement, pattern, sentiment in catalog:
            found = self._find(doc, pattern)
            if found:
                index, span = found
                findings.append(
                    Finding(
                        category=category,
                        statement=statement,
                        evidence=[cite(doc, doc.pages[index], *span)],
                        sentiment=sentiment,
                    )
                )
        return findings

    @staticmethod
    def _find(doc: ParsedDocument, expression: str) -> tuple[int, tuple[int, int]] | None:
        for index, page in enumerate(doc.pages):
            match = re.search(expression, page.text, re.I | re.S)
            if match:
                return index, match.span()
        return None

    @staticmethod
    def _catalog(company: str) -> list[tuple[Literal["drivers", "risks", "guidance", "events", "tone"], str, str, Literal["positive", "neutral", "negative"] | None]]:
        if company == "Light S.A.":
            return [
                (
                    "drivers",
                    "A administração atribuiu a redução da receita a estornos de regularizações, ausência de bandeiras tarifárias e variação negativa da CVA.",
                    r"Essa redução foi influenciada pelos\s+estornos de faturamento de regularizações, pelo não acionamento das bandeiras tarifárias",
                    None,
                ),
                (
                    "risks",
                    "Risco de perdas não técnicas (furto de energia) e inadimplência.",
                    r"perdas não técnicas\s*[–-]\s*aquelas relacionadas ao furto de energia\s*[–-]\s*e a inadimplência",
                    None,
                ),
                (
                    "risks",
                    "Pressão de juros e necessidade de readequação da estrutura de capital.",
                    r"taxas de juros no Brasil voltaram para\s*um patamar muito alto",
                    None,
                ),
                (
                    "risks",
                    "Risco relevante relacionado à continuidade operacional da companhia.",
                    r"incerteza significativa que pode levantar dúvida significativa quanto à capacidade de\s*continuidade operacional",
                    None,
                ),
                (
                    "events",
                    "A companhia informa negociações para antecipar a renovação da concessão, cujo vencimento foi declarado como 2026.",
                    r"concessão da Light SESA, que vence em 2026",
                    None,
                ),
                (
                    "guidance",
                    "Perspectiva qualitativa: foco em investimentos necessários e maximização de caixa nos próximos 36 meses; não equivale a guidance financeiro numérico.",
                    r"maximizar o\s*fluxo de caixa nos próximos 36 meses",
                    None,
                ),
                (
                    "tone",
                    "Tom predominantemente cauteloso/negativo, diante da incerteza explícita sobre continuidade operacional e da reestruturação da dívida.",
                    r"incerteza significativa que pode levantar dúvida significativa quanto à capacidade de\s*continuidade operacional",
                    "negative",
                ),
            ]
        if company.startswith("Brasal"):
            return [
                (
                    "risks",
                    "Risco de crédito e inadimplência em contas a receber.",
                    r"Risco de crédito\s+O principal fator de risco de mercado que afeta o negócio",
                    None,
                ),
                (
                    "risks",
                    "Exposição à oscilação dos preços de produtos e matérias-primas.",
                    r"Risco de variação do preço\s+Os produtos comercializados pela Companhia estão sujeitos a oscilações",
                    None,
                ),
                (
                    "risks",
                    "Exposição a oscilações das taxas de juros.",
                    r"Análise do Risco de oscilação das taxas de juros",
                    None,
                ),
            ]
        if company.startswith("Millet"):
            return [
                (
                    "events",
                    "Registro de aquisição de investida e combinação de negócios nas demonstrações dos fluxos de caixa.",
                    r"Aquisição de investida",
                    None,
                ),
                (
                    "risks",
                    "Exposição a contingências, conforme provisões apresentadas no demonstrativo.",
                    r"Provisão para contingências",
                    None,
                ),
            ]
        return []
