"""Score supplied quote-extraction predictions without calling a model provider."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from evidhist.domain.citations import Citation, CitationError, TextVersion, locate_quote


class EvalCase(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: str
    task: str
    source: TextVersion
    expected: Citation | None


class Prediction(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: str
    output: object


class CaseResult(BaseModel):
    id: str
    passed: bool
    reason: str


class EvalReport(BaseModel):
    total: int
    passed: int
    results: list[CaseResult]


def _score_prediction(case: EvalCase, output: object) -> tuple[bool, str]:
    """Classify one model output against the case expectation."""
    if output is None:
        passed = case.expected is None
        return passed, "correct_abstention" if passed else "unexpected_abstention"
    try:
        citation = Citation.model_validate(output)
        locate_quote(case.source, citation)
    except ValidationError:
        return False, "invalid_schema"
    except CitationError as error:
        return False, error.code
    passed = citation == case.expected
    return passed, "matched_expected_quote" if passed else "wrong_answer"


def evaluate(cases: Sequence[EvalCase], predictions: Sequence[Prediction]) -> EvalReport:
    if not cases:
        raise ValueError("case set is empty")
    case_ids = {case.id for case in cases}
    outputs = {prediction.id: prediction.output for prediction in predictions}
    if len(case_ids) != len(cases) or len(outputs) != len(predictions):
        raise ValueError("duplicate case or prediction IDs")
    if set(outputs) - case_ids:
        raise ValueError("predictions contain unknown case IDs")
    results: list[CaseResult] = []
    for case in cases:
        if case.expected is not None:
            locate_quote(case.source, case.expected)
        if case.id not in outputs:
            results.append(CaseResult(id=case.id, passed=False, reason="missing_prediction"))
            continue
        passed, reason = _score_prediction(case, outputs[case.id])
        results.append(CaseResult(id=case.id, passed=passed, reason=reason))
    return EvalReport(
        total=len(cases), passed=sum(result.passed for result in results), results=results
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = [
        EvalCase.model_validate_json(line)
        for line in args.cases.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    predictions = [
        Prediction.model_validate_json(line)
        for line in args.predictions.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = evaluate(cases, predictions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"Quote cases passed: {report.passed}/{report.total}")
    return 0 if report.passed == report.total else 1
