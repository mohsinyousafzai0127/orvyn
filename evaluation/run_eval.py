"""Prompt evaluation runner.

Runs every case in evaluation/prompts.json against the real Orvyn agent (fresh
session per case), checks tool usage and expected/forbidden wording, and writes
JSON and Markdown results to evaluation/results/.

Run from the project root:
    python -m evaluation.run_eval
    python -m evaluation.run_eval --delay 3

To compare prompt versions (PowerShell):
    $env:ORVYN_PROMPT_VERSION = "v1"; python -m evaluation.run_eval
    $env:ORVYN_PROMPT_VERSION = "v2"; python -m evaluation.run_eval
"""
import argparse
import json
import time
from pathlib import Path

from src import config

CASES_FILE = Path(__file__).parent / "prompts.json"
RESULTS_DIR = Path(__file__).parent / "results"


def load_cases(path=CASES_FILE) -> list:
    """Load the evaluation cases from a JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _normalize(text: str) -> str:
    return text.lower().replace("\u2019", "'")


def evaluate_case(case: dict, reply: str, tools_used: list) -> list:
    """Return a list of failure reasons (an empty list means the case passed)."""
    failures = []
    text = _normalize(reply)

    include_any = case.get("must_include_any")
    if include_any and not any(_normalize(word) in text for word in include_any):
        failures.append(f"reply contains none of {include_any}")
    for word in case.get("must_not_include", []):
        if _normalize(word) in text:
            failures.append(f"reply contains forbidden text '{word}'")
    for tool in case.get("expect_tools", []):
        if tool not in tools_used:
            failures.append(f"expected tool '{tool}' was not used")
    if case.get("expect_no_tool") and tools_used:
        failures.append(f"no tool was expected but used {tools_used}")
    return failures


def run_cases(cases: list, orvyn_factory, delay: float = 2.0) -> list:
    """Run each case on a fresh Orvyn and collect the results."""
    results = []
    for case in cases:
        orvyn = orvyn_factory()
        started = time.perf_counter()
        reply = orvyn.ask(case["prompt"])
        latency = time.perf_counter() - started
        failures = evaluate_case(case, reply, orvyn.last_tool_calls)
        results.append({
            "id": case["id"],
            "category": case["category"],
            "prompt": case["prompt"],
            "reply": reply,
            "tools_used": list(orvyn.last_tool_calls),
            "latency_seconds": round(latency, 2),
            "passed": not failures,
            "failures": failures,
        })
        print(f"[{'PASS' if not failures else 'FAIL'}] {case['id']:<22} {latency:5.1f}s  tools={orvyn.last_tool_calls}")
        time.sleep(delay)
    return results


def write_reports(results: list, version: str, out_dir=RESULTS_DIR) -> tuple:
    """Write results_<version>.json and results_<version>.md. Returns both paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for r in results if r["passed"])

    json_path = out_dir / f"results_{version}.json"
    json_path.write_text(json.dumps({"prompt_version": version, "passed": passed, "total": len(results),
                                     "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [f"# Evaluation results - prompt {version}", "",
             f"**Passed {passed} of {len(results)} cases.**", "",
             "| ID | Category | Result | Tools used | Latency (s) | Notes |",
             "|---|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['id']} | {r['category']} | {'PASS' if r['passed'] else 'FAIL'} | "
                     f"{', '.join(r['tools_used']) or '-'} | {r['latency_seconds']} | "
                     f"{'; '.join(r['failures']) or '-'} |")
    md_path = out_dir / f"results_{version}.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Orvyn prompt evaluation")
    parser.add_argument("--cases", default=str(CASES_FILE), help="path to the cases JSON file")
    parser.add_argument("--delay", type=float, default=2.0, help="seconds to wait between cases")
    args = parser.parse_args()

    from src.agent import Orvyn  # imported here so unit tests do not need an API key

    try:
        Orvyn()  # fail early with a clear message if the key is missing
    except config.ConfigError as exc:
        print(f"Cannot run evaluation: {exc}")
        return 1

    version = config.PROMPT_VERSION
    print(f"Running evaluation with prompt {version} ...\n")
    results = run_cases(load_cases(args.cases), Orvyn, delay=args.delay)
    json_path, md_path = write_reports(results, version)
    passed = sum(1 for r in results if r["passed"])
    print(f"\nPassed {passed} of {len(results)}. Results written to {md_path} and {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
