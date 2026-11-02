#!/usr/bin/env python3
"""Export every notebook task of a job run, with its cell outputs, as .ipynb + readable .md into evidence/runs/.

Usage: uv run --with databricks-sdk tools/export_run_evidence.py <job_run_id>
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import urllib.parse
from pathlib import Path

import sys

from databricks.sdk import WorkspaceClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from settings import PROFILE, ROOT, redact  # noqa: E402


def notebook_model(html: str) -> dict:
    m = re.search(r"__DATABRICKS_NOTEBOOK_MODEL = '([^']+)'", html)
    if not m:
        raise ValueError("notebook model not found in exported HTML")
    return json.loads(urllib.parse.unquote(base64.b64decode(m.group(1)).decode("utf-8")))


def fmt_table(res: dict, max_rows: int = 40) -> str:
    cols = [c.get("name", f"c{i}") for i, c in enumerate(res.get("schema") or [])]
    rows = res.get("data") or []
    if not cols and rows and isinstance(rows[0], dict):
        cols = list(rows[0])
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows[:max_rows]:
        vals = [r.get(c) for c in cols] if isinstance(r, dict) else r
        out.append("| " + " | ".join(str(v).replace("|", "\\|").replace("\n", " ")[:300] for v in vals) + " |")
    if len(rows) > max_rows:
        out.append(f"\n_{len(rows) - max_rows} more rows not shown_")
    return "\n".join(out)


def result_text(results: dict | None) -> str:
    if not results:
        return ""
    t, data = results.get("type"), results.get("data")
    if t == "table":
        return fmt_table(results)
    if t == "listResults":
        return "\n\n".join(result_text(r) for r in data or [])
    if t in ("text", "ansi", None) and isinstance(data, str):
        return re.sub(r"\x1b\[[0-9;]*m", "", data)
    if t == "html" and isinstance(data, str):
        return re.sub(r"<[^>]+>", " ", data)[:4000]
    if t == "error":
        return "ERROR: " + str(results.get("summary") or data)[:4000]
    return str(data)[:4000] if data else ""


def to_ipynb(model: dict, lang: str) -> dict:
    cells = []
    for c in sorted(model.get("commands", []), key=lambda x: x.get("position", 0)):
        src = c.get("command", "")
        if src.lstrip().startswith("%md"):
            cells.append({"cell_type": "markdown", "metadata": {}, "source": src.lstrip()[3:].lstrip("\n")})
            continue
        txt = result_text(c.get("results"))
        outputs = [{"output_type": "stream", "name": "stdout", "text": txt}] if txt else []
        cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "source": src, "outputs": outputs})
    return {"nbformat": 4, "nbformat_minor": 5, "cells": cells,
            "metadata": {"language_info": {"name": lang}, "databricks": {"notebook_name": model.get("name")}}}


def to_md(nb: dict, title: str, meta: str) -> str:
    lang = nb["metadata"]["language_info"]["name"]
    parts = [f"# {title}\n\n{meta}\n"]
    for c in nb["cells"]:
        if c["cell_type"] == "markdown":
            parts.append(c["source"])
        else:
            parts.append(f"```{lang}\n{c['source'].strip()}\n```")
            for o in c["outputs"]:
                parts.append("**Output:**\n\n" + (o["text"] if o["text"].lstrip().startswith("|") else f"```\n{o['text'].strip()}\n```"))
    return "\n\n".join(parts) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_id", type=int)
    ap.add_argument("--profile", default=PROFILE)
    a = ap.parse_args()
    w = WorkspaceClient(profile=a.profile)
    run = w.jobs.get_run(a.run_id)
    out = ROOT / "evidence" / "runs"
    out.mkdir(parents=True, exist_ok=True)
    summary = [f"# Job run {a.run_id}: {run.run_name}\n", f"- Run page: {run.run_page_url}",
               f"- Result: {run.state.result_state.value if run.state.result_state else run.state.life_cycle_state.value}",
               f"- Started (epoch ms): {run.start_time}, ended: {run.end_time}\n",
               "| task | task run id | result | duration s |", "|---|---|---|---|"]
    for t in run.tasks or []:
        dur = round(((t.end_time or 0) - (t.start_time or 0)) / 1000)
        summary.append(f"| {t.task_key} | {t.run_id} | {t.state.result_state.value if t.state.result_state else t.state.life_cycle_state.value} | {dur} |")
        if not t.notebook_task:
            continue
        try:
            views = w.jobs.export_run(t.run_id).views or []
            model = notebook_model(views[0].content)
        except Exception as e:  # noqa: BLE001
            print(f"skip {t.task_key}: {e}")
            continue
        lang = "sql" if t.notebook_task.notebook_path.endswith(".sql") else "python"
        nb = to_ipynb(model, lang)
        stem = Path(t.notebook_task.notebook_path).stem
        (out / f"{stem}.ipynb").write_text(redact(json.dumps(nb, indent=1)))
        (out / f"{stem}.md").write_text(redact(to_md(nb, f"{stem} (executed)", f"Task `{t.task_key}` · task run {t.run_id} · job run {a.run_id}")))
        print("exported", stem)
    (out / "JOB_RUN_SUMMARY.md").write_text(redact("\n".join(summary) + "\n"))


if __name__ == "__main__":
    main()
