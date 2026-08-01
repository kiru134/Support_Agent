from __future__ import annotations

from pathlib import Path

from evaluation.models import RunReport


def write_json_report(report: RunReport, out_path: str) -> None:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(report.model_dump_json(indent=2))
