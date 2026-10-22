from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, TypedDict
from uuid import uuid4

from intra_financial_ai.application.extraction import FinancialExtractor
from intra_financial_ai.application.qualitative import QualitativeAnalyzer
from intra_financial_ai.application.questions import QuestionAnswerer
from intra_financial_ai.application.reporting import write_reports
from intra_financial_ai.application.validation import FinancialValidator
from intra_financial_ai.domain.models import (
    AnalysisReport,
    DocumentResult,
    Issue,
    ParsedDocument,
    RunMetrics,
    Timing,
)
from intra_financial_ai.infrastructure.llm import OptionalLLMAnalyzer
from intra_financial_ai.infrastructure.llm_financial import FinancialLLMAdapter
from intra_financial_ai.infrastructure.pdf_reader import DocumentReader


class WorkflowState(TypedDict, total=False):
    paths: list[str]
    documents: list[ParsedDocument]
    results: list[DocumentResult]
    answers: list[Any]
    run_id: str
    metrics: RunMetrics


class AnalysisWorkflow:
    def __init__(self) -> None:
        self.reader = DocumentReader(
            max_mb=int(os.getenv("INTRA_MAX_PDF_MB", "30")),
            max_pages=int(os.getenv("INTRA_MAX_PAGES", "200")),
        )
        self.extractor = FinancialExtractor()
        self.analyst = QualitativeAnalyzer()
        self.llm = OptionalLLMAnalyzer()
        self.financial_llm = FinancialLLMAdapter()
        self.validator = FinancialValidator()
        self.question_answerer = QuestionAnswerer()
        self.engine = "sequential"
        self.document_timings: list[Timing] = []

    @staticmethod
    def _timed(state: WorkflowState, label: str, callback: Any) -> WorkflowState:
        start = time.perf_counter()
        updates = callback()
        metrics = state["metrics"].model_copy(deep=True)
        metrics.timings.append(Timing(step=label, seconds=round(time.perf_counter() - start, 3)))
        return {**updates, "metrics": metrics}

    def ingest(self, state: WorkflowState) -> WorkflowState:
        def call() -> dict[str, Any]:
            documents = []
            for value in state["paths"]:
                start = time.perf_counter()
                document = self.reader.read(Path(value))
                documents.append(document)
                self.document_timings.append(Timing(step=f"ingestion:{document.name}", seconds=round(time.perf_counter() - start, 3)))
            return {"documents": documents}

        return self._timed(state, "ingestion", call)

    def extract(self, state: WorkflowState) -> WorkflowState:
        def call() -> dict[str, Any]:
            results = []
            for doc in state["documents"]:
                start = time.perf_counter()
                result = self.extractor.extract(doc)
                if self.financial_llm.enabled:
                    try:
                        suggestions = self.financial_llm.propose(doc)
                        for field, candidate in suggestions.items():
                            if result.metrics[field].status == "not_found":
                                result.metrics[field] = candidate
                    except Exception as error:
                        result.issues.append(Issue(document=doc.name, code="LLM_EXTRACTION_UNAVAILABLE", level="warning", message=f"Extração LLM opcional falhou: {type(error).__name__}. Baseline determinístico preservado."))
                results.append(result)
                self.document_timings.append(Timing(step=f"extraction:{doc.name}", seconds=round(time.perf_counter() - start, 3)))
            return {"results": results}

        return self._timed(state, "financial_extraction", call)

    def qualitative(self, state: WorkflowState) -> WorkflowState:
        def call() -> dict[str, Any]:
            results = [report.model_copy(deep=True) for report in state["results"]]
            for doc, report in zip(state["documents"], results, strict=True):
                report.findings = self.analyst.analyze(doc, report.company)
                if self.llm.enabled:
                    try:
                        extended = self.llm.analyze(doc, report.company)
                        existing = {(finding.category, finding.statement) for finding in report.findings}
                        report.findings.extend(finding for finding in extended if (finding.category, finding.statement) not in existing)
                    except Exception as error:
                        report.issues.append(Issue(document=doc.name, code="LLM_UNAVAILABLE", level="warning", message=f"Extração qualitativa opcional falhou: {type(error).__name__}. Fallback determinístico aplicado."))
            return {"results": results}

        updates = self._timed(state, "qualitative_analysis", call)
        metrics = updates["metrics"]
        metrics.prompt_tokens = self.llm.usage.prompt_tokens + self.financial_llm.prompt_tokens
        metrics.completion_tokens = self.llm.usage.completion_tokens + self.financial_llm.completion_tokens
        return updates

    def validate(self, state: WorkflowState) -> WorkflowState:
        def call() -> dict[str, Any]:
            results = [report.model_copy(deep=True) for report in state["results"]]
            for doc, result in zip(state["documents"], results, strict=True):
                result.issues.extend(self.validator.validate(result, doc))
            return {"results": results}

        return self._timed(state, "validation", call)

    def answer(self, state: WorkflowState) -> WorkflowState:
        def call() -> dict[str, Any]:
            return {"answers": self.question_answerer.answer_required(state["results"])}

        return self._timed(state, "questions", call)

    def _compile_graph(self) -> Any:
        from langgraph.graph import END, START, StateGraph

        graph = StateGraph(WorkflowState)
        graph.add_node("ingest", self.ingest)
        graph.add_node("extract", self.extract)
        graph.add_node("qualitative", self.qualitative)
        graph.add_node("validate", self.validate)
        graph.add_node("answer", self.answer)
        graph.add_edge(START, "ingest")
        graph.add_edge("ingest", "extract")
        graph.add_edge("extract", "qualitative")
        graph.add_edge("qualitative", "validate")
        graph.add_edge("validate", "answer")
        graph.add_edge("answer", END)
        return graph.compile()

    def run(self, input_folder: Path, output_folder: Path) -> tuple[AnalysisReport, Path]:
        if not input_folder.is_dir():
            raise ValueError(f"Pasta de entrada inválida: {input_folder}")
        files = sorted(input_folder.glob("*.pdf"))
        if not files:
            raise ValueError("Nenhum PDF encontrado na pasta de entrada")
        run_id = uuid4().hex[:12]
        state: WorkflowState = {
            "paths": [str(path) for path in files],
            "run_id": run_id,
            "metrics": RunMetrics(run_id=run_id, llm_enabled=self.llm.enabled, llm_model=self.llm.model if self.llm.enabled else None),
        }
        try:
            graph = self._compile_graph()
            self.engine = "langgraph"
        except ImportError:
            graph = None
            self.engine = "sequential_fallback"
        pipeline_start = time.perf_counter()
        if graph:
            final = graph.invoke(state)
        else:
            final = state
            for method in (self.ingest, self.extract, self.qualitative, self.validate, self.answer):
                final = {**final, **method(final)}
        final["metrics"].timings.extend(self.document_timings)
        final["metrics"].timings.append(Timing(step="total_pipeline", seconds=round(time.perf_counter() - pipeline_start, 3)))
        input_rate = os.getenv("INTRA_INPUT_COST_PER_MILLION_TOKENS_USD")
        output_rate = os.getenv("INTRA_OUTPUT_COST_PER_MILLION_TOKENS_USD")
        if input_rate and output_rate:
            final["metrics"].estimated_cost_usd = round(
                (final["metrics"].prompt_tokens * float(input_rate) + final["metrics"].completion_tokens * float(output_rate)) / 1_000_000,
                6,
            )
        report = AnalysisReport(run_id=run_id, documents=final["results"], answers=final["answers"], metrics=final["metrics"])
        folder = output_folder / f"run_{run_id}"
        folder.mkdir(parents=True, exist_ok=True)
        for document in report.documents:
            (folder / f"{document.company.split()[0].lower()}.json").write_text(document.model_dump_json(indent=2), encoding="utf-8")
        (folder / "questions.json").write_text(json.dumps([answer.model_dump(mode="json") for answer in report.answers], ensure_ascii=False, indent=2), encoding="utf-8")
        (folder / "metrics.json").write_text(report.metrics.model_dump_json(indent=2), encoding="utf-8")
        (folder / "validation.json").write_text(json.dumps([issue.model_dump(mode="json") for result in report.documents for issue in result.issues], ensure_ascii=False, indent=2), encoding="utf-8")
        with (folder / "evidence.jsonl").open("w", encoding="utf-8") as output:
            for document in final["documents"]:
                for page in document.pages:
                    output.write(json.dumps({"document": document.name, "page": page.number, "text": page.text, "tables": page.tables}, ensure_ascii=False) + "\n")
        (folder / "manifest.json").write_text(json.dumps({"run_id": run_id, "engine": self.engine, "documents": [{"name": d.name, "sha256": d.sha256, "pages": len(d.pages)} for d in final["documents"]]}, ensure_ascii=False, indent=2), encoding="utf-8")
        write_reports(report, folder)
        return report, folder
