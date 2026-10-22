from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class ExtractionStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    INVALID = "invalid"


class Evidence(BaseModel):
    document: str
    page: int = Field(ge=1)
    excerpt: str = Field(min_length=1)
    section: str | None = None


class Metric(BaseModel):
    status: ExtractionStatus = ExtractionStatus.NOT_FOUND
    value: float | None = None
    unit: str | None = None
    year: int | None = None
    comparator: float | None = None
    comparator_year: int | None = None
    variation_pct: float | None = None
    variation_method: Literal["reported", "calculated"] | None = None
    scope: str | None = None
    definition: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    note: str | None = None


class Finding(BaseModel):
    category: Literal["drivers", "risks", "guidance", "events", "tone"]
    statement: str
    evidence: list[Evidence] = Field(default_factory=list)
    sentiment: Literal["positive", "neutral", "negative"] | None = None


class Issue(BaseModel):
    document: str
    code: str
    level: Literal["info", "warning", "error"]
    message: str
    metric: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class DocumentResult(BaseModel):
    document: str
    company: str
    period: str
    pages: int
    sha256: str
    metrics: dict[str, Metric]
    findings: list[Finding] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)


class Answer(BaseModel):
    question: str
    answer: str
    status: Literal["answered", "partial", "not_found"]
    evidence: list[Evidence] = Field(default_factory=list)


class Timing(BaseModel):
    step: str
    seconds: float


class RunMetrics(BaseModel):
    run_id: str
    llm_enabled: bool
    llm_model: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float | None = None
    timings: list[Timing] = Field(default_factory=list)


class AnalysisReport(BaseModel):
    run_id: str
    documents: list[DocumentResult]
    answers: list[Answer]
    metrics: RunMetrics


class Page(BaseModel):
    number: int
    text: str
    raw_text: str = ""
    tables: list[list[list[str | None]]] = Field(default_factory=list)


class ParsedDocument(BaseModel):
    name: str
    pages: list[Page]
    sha256: str


FINANCIAL_FIELDS = (
    "revenue",
    "ebitda",
    "ebitda_margin",
    "net_income",
    "net_debt",
    "leverage",
    "operating_cash_flow",
    "capex",
)

QUESTIONS = (
    "Qual empresa teve a maior margem EBITDA no período?",
    "O que a administração de cada empresa apontou como principal motivo da variação da receita?",
    "Alguma das empresas está com alavancagem acima de 3x? Qual?",
    "Quais riscos são citados por mais de uma empresa?",
    "Qual é o guidance de cada empresa para o próximo ano?",
)
