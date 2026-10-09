from pathlib import Path

import pytest

from evidhist.domain.citations import Citation, TextVersion
from evidhist.evaluation import EvalCase, Prediction, evaluate, main


def sample_case(expected: Citation | None = None) -> EvalCase:
    return EvalCase(
        id="one", task="extract", source=TextVersion(version_id="a", text="春"), expected=expected
    )


def test_missing_predictions_remain_in_the_denominator() -> None:
    report = evaluate([sample_case()], [])

    assert report.total == 1
    assert report.passed == 0
    assert report.results[0].reason == "missing_prediction"


def test_unanswerable_case_requires_abstention() -> None:
    report = evaluate([sample_case()], [Prediction(id="one", output=None)])

    assert report.passed == 1
    assert report.results[0].reason == "correct_abstention"


@pytest.mark.parametrize(
    "output,reason",
    [
        (None, "unexpected_abstention"),
        ({"start": 0}, "invalid_schema"),
        ({"version_id": "b", "start": 0, "end": 1, "exact_quote": "春"}, "version_mismatch"),
        ({"version_id": "a", "start": 0, "end": 1, "exact_quote": "秋"}, "quote_mismatch"),
    ],
)
def test_bad_model_outputs_cannot_be_reported_as_success(output: object, reason: str) -> None:
    case = sample_case(Citation(version_id="a", start=0, end=1, exact_quote="春"))

    report = evaluate([case], [Prediction(id="one", output=output)])

    assert report.passed == 0
    assert report.results[0].reason == reason


def test_valid_quote_is_not_sufficient_when_the_task_requires_abstention() -> None:
    output = {"version_id": "a", "start": 0, "end": 1, "exact_quote": "春"}

    report = evaluate([sample_case()], [Prediction(id="one", output=output)])

    assert report.passed == 0
    assert report.results[0].reason == "wrong_answer"


@pytest.mark.parametrize("kind", ["empty", "duplicate_case", "duplicate_prediction", "unknown_id"])
def test_invalid_evaluation_inputs_fail_instead_of_changing_the_score(kind: str) -> None:
    cases = [] if kind == "empty" else [sample_case()]
    predictions = [Prediction(id="one", output=None)]
    if kind == "duplicate_case":
        cases.append(sample_case())
    if kind == "duplicate_prediction":
        predictions.append(Prediction(id="one", output=None))
    if kind == "unknown_id":
        predictions = [Prediction(id="unknown", output=None)]

    with pytest.raises(ValueError):
        evaluate(cases, predictions)


def test_fixture_evaluation_cli_writes_a_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "result.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "evidhist-eval-quotes",
            "--cases",
            "evals/quotes.jsonl",
            "--predictions",
            "evals/fixtures/quotes.predictions.jsonl",
            "--output",
            str(output),
        ],
    )

    assert main() == 0
    assert '"passed": 4' in output.read_text()
