from __future__ import annotations

"""Run pytest and persist a structured unit-test report (JSON + HTML)."""

import argparse
import html
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


def _parse_junit_xml(junit_path: Path) -> dict:
  root = ET.parse(junit_path).getroot()
  suites = [root] if root.tag == "testsuite" else root.findall("testsuite")

  totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}
  failed_cases: list[dict[str, str]] = []
  test_cases: list[dict[str, str | float]] = []

  for suite in suites:
    totals["tests"] += int(suite.attrib.get("tests", 0))
    totals["failures"] += int(suite.attrib.get("failures", 0))
    totals["errors"] += int(suite.attrib.get("errors", 0))
    totals["skipped"] += int(suite.attrib.get("skipped", 0))
    totals["time"] += float(suite.attrib.get("time", 0.0))

    for case in suite.findall("testcase"):
      failure = case.find("failure")
      error = case.find("error")
      skipped = case.find("skipped")
      status = "passed"
      reason = ""

      if failure is not None:
        status = "failed"
        reason = failure.attrib.get("message", "") or (failure.text or "")
      elif error is not None:
        status = "error"
        reason = error.attrib.get("message", "") or (error.text or "")
      elif skipped is not None:
        status = "skipped"
        reason = skipped.attrib.get("message", "") or (skipped.text or "")

      test_cases.append(
        {
          "classname": case.attrib.get("classname", ""),
          "name": case.attrib.get("name", ""),
          "status": status,
          "time": float(case.attrib.get("time", 0.0)),
          "reason": reason.strip(),
        }
      )

      if failure is not None or error is not None:
        failed_cases.append(
          {
            "classname": case.attrib.get("classname", ""),
            "name": case.attrib.get("name", ""),
            "reason": reason.strip(),
          }
        )

  totals["passed"] = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
  totals["status"] = "pass" if (totals["failures"] == 0 and totals["errors"] == 0) else "fail"
  totals["failed_cases"] = failed_cases
  totals["test_cases"] = test_cases
  return totals


def _write_html_report(payload: dict, html_path: Path) -> None:
  status = payload["status"]
  status_color = "#127a45" if status == "pass" else "#b42318"

  rows = "\n".join(
    f"<tr><td>{html.escape(case['classname'])}</td><td>{html.escape(case['name'])}</td><td>{html.escape(case['reason'][:240])}</td></tr>"
    for case in payload["failed_cases"]
  )
  if not rows:
    rows = "<tr><td colspan=\"3\">No failing test cases.</td></tr>"

  case_rows = "\n".join(
    (
      "<tr>"
      f"<td>{html.escape(str(case['classname']))}</td>"
      f"<td>{html.escape(str(case['name']))}</td>"
      f"<td><span class=\"case-status {str(case['status'])}\">{str(case['status']).upper()}</span></td>"
      f"<td>{float(case['time']):.4f}</td>"
      f"<td>{html.escape(str(case['reason'])[:240])}</td>"
      "</tr>"
    )
    for case in payload["test_cases"]
  )
  if not case_rows:
    case_rows = "<tr><td colspan=\"5\">No test cases found.</td></tr>"

  html_text = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Unit Test Run Summary</title>
  <style>
  body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; color: #1f2933; }}
  .status {{ color: {status_color}; font-weight: 700; }}
  .grid {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); margin: 16px 0; }}
  .card {{ border: 1px solid #d9e2ec; border-radius: 8px; padding: 10px; background: #fff; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #d9e2ec; padding: 8px; text-align: left; vertical-align: top; }}
  th {{ background: #f0f4f8; }}
  .case-status {{ font-weight: 700; }}
  .passed {{ color: #127a45; }}
  .failed {{ color: #b42318; }}
  .error {{ color: #7a1b9a; }}
  .skipped {{ color: #8d6e00; }}
  </style>
</head>
<body>
  <h1>Unit Test Run Summary</h1>
  <p>Status: <span class=\"status\">{status.upper()}</span></p>
  <p>Generated: {payload['generated_at_utc']}</p>
  <p>Command: <code>{payload['command']}</code></p>

  <div class=\"grid\">
  <div class=\"card\"><strong>tests</strong><br>{payload['tests']}</div>
  <div class=\"card\"><strong>passed</strong><br>{payload['passed']}</div>
  <div class=\"card\"><strong>failures</strong><br>{payload['failures']}</div>
  <div class=\"card\"><strong>errors</strong><br>{payload['errors']}</div>
  <div class=\"card\"><strong>skipped</strong><br>{payload['skipped']}</div>
  <div class=\"card\"><strong>duration_sec</strong><br>{payload['time']:.3f}</div>
  </div>

  <h2>Failing Cases</h2>
  <table>
  <thead><tr><th>Class</th><th>Test</th><th>Reason (truncated)</th></tr></thead>
  <tbody>
    {rows}
  </tbody>
  </table>

  <h2>All Test Cases</h2>
  <table>
  <thead><tr><th>Class</th><th>Test</th><th>Status</th><th>Duration (s)</th><th>Reason (if any)</th></tr></thead>
  <tbody>
    {case_rows}
  </tbody>
  </table>
</body>
</html>
"""
  html_path.write_text(html_text, encoding="utf-8")


def main() -> int:
  parser = argparse.ArgumentParser(description="Run pytest and generate report artifacts.")
  parser.add_argument("--output-dir", default="reports/tests/latest", help="Directory to write test report artifacts.")
  args, pytest_args = parser.parse_known_args()

  output_dir = Path(args.output_dir)
  output_dir.mkdir(parents=True, exist_ok=True)
  junit_path = output_dir / "junit.xml"

  cmd = [sys.executable, "-m", "pytest", *pytest_args, f"--junitxml={junit_path}"]
  result = subprocess.run(cmd)

  summary = _parse_junit_xml(junit_path)
  payload = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "command": " ".join(cmd),
    **summary,
  }

  json_path = output_dir / "test_run_summary.json"
  json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
  _write_html_report(payload, output_dir / "test_run_summary.html")

  print(f"Wrote unit-test report artifacts to: {output_dir}")
  return result.returncode


if __name__ == "__main__":
  raise SystemExit(main())
