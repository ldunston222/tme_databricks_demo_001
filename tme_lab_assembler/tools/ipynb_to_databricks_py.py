"""Convert a Jupyter/VS Code .ipynb to a Databricks 'source' notebook .py.

This exists to avoid merge conflicts in Databricks Repos caused by notebook JSON churn.

Usage:
  python tme_lab_assembler/tools/ipynb_to_databricks_py.py path/to/notebook.ipynb

By default, writes alongside the input as the same basename with .py extension.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def ipynb_to_databricks_py_text(ipynb: dict) -> str:
    cells = ipynb.get("cells", [])
    if not isinstance(cells, list) or not cells:
        raise ValueError("No cells found in notebook JSON")

    out_lines: list[str] = ["# Databricks notebook source"]

    for idx, cell in enumerate(cells):
        cell_type = cell.get("cell_type", "code")
        source = cell.get("source", [])

        if isinstance(source, str):
            src_text = source
        elif isinstance(source, list):
            src_text = "\n".join(source)
        else:
            src_text = ""

        if idx > 0:
            out_lines.append("")
            out_lines.append("# COMMAND ----------")

        if cell_type == "markdown":
            out_lines.append("# MAGIC %md")
            for line in src_text.splitlines():
                out_lines.append(f"# MAGIC {line}" if line else "# MAGIC")
        else:
            out_lines.append(src_text.rstrip())

    return "\n".join(out_lines).rstrip() + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python ipynb_to_databricks_py.py path/to/notebook.ipynb", file=sys.stderr)
        return 2

    ipynb_path = Path(argv[1])
    if not ipynb_path.exists():
        print(f"File not found: {ipynb_path}", file=sys.stderr)
        return 2

    ipynb = json.loads(ipynb_path.read_text(encoding="utf-8"))
    py_text = ipynb_to_databricks_py_text(ipynb)

    py_path = ipynb_path.with_suffix(".py")
    py_path.write_text(py_text, encoding="utf-8")
    print(f"Wrote {py_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
