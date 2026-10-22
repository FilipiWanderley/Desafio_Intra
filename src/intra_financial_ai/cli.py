from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated

import typer

from intra_financial_ai.application.evaluation import evaluate as run_evaluation
from intra_financial_ai.application.workflow import AnalysisWorkflow

app = typer.Typer(
    add_completion=False,
    help="Intra Financial AI — análise auditável de demonstrações financeiras",
)


@app.callback()
def main() -> None:
    return None


@app.command()
def analyze(
    input_folder: Annotated[
        Path,
        typer.Argument(help="Diretório contendo PDFs"),
    ],
    output: Annotated[
        Path,
        typer.Option("--output", "-o"),
    ] = Path("outputs"),
    llm: Annotated[
        bool,
        typer.Option("--llm", help="Habilita enriquecimento qualitativo via OpenAI"),
    ] = False,
) -> None:
    if llm:
        os.environ["INTRA_LLM_ENABLED"] = "true"

    try:
        workflow = AnalysisWorkflow()
        report, path = workflow.run(input_folder, output)
    except (ValueError, OSError) as error:
        typer.secho(f"Erro: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from error

    typer.echo(f"Processados {len(report.documents)} PDFs")
    typer.echo(f"Motor de orquestração: {workflow.engine}")
    typer.echo(f"Relatório: {path / 'report.html'}")
    typer.echo(f"Saída: {path}")


@app.command()
def evaluate(
    run_folder: Annotated[
        Path,
        typer.Argument(help="Diretório outputs/run_*"),
    ],
    golden: Annotated[
        Path,
        typer.Option("--golden"),
    ] = Path("evals/golden_dataset.json"),
) -> None:
    result = run_evaluation(run_folder, golden)

    (run_folder / "evaluation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
