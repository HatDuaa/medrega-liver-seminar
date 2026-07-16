from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from ..schemas import ALLOWED_LABELS, OutcomePrediction, PrivateCase, RetrievedChunk
from .llm_runner import BackendMetadata
from .outcome_predictor import predict_outcome


def _tokens(text: str) -> list[str]:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    without_marks = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    ).replace("đ", "d")
    return re.findall(r"[a-z0-9]+", without_marks)


def _features(case: PrivateCase, chunks: tuple[RetrievedChunk, ...]) -> Counter[str]:
    text = case.case_query + "\n" + "\n".join(chunk.text for chunk in chunks)
    return Counter(_tokens(text))


@dataclass(frozen=True)
class TrainingExample:
    case: PrivateCase
    chunks: tuple[RetrievedChunk, ...]
    label: str

    def __post_init__(self) -> None:
        if not isinstance(self.case, PrivateCase):
            raise TypeError("training example requires PrivateCase")
        if any(not isinstance(chunk, RetrievedChunk) for chunk in self.chunks):
            raise TypeError("training chunks must contain RetrievedChunk objects")
        if self.label not in ALLOWED_LABELS:
            raise ValueError(f"invalid training label: {self.label!r}")


class NaiveBayesOutcomeRunner:
    metadata = BackendMetadata(
        backend_id="naive_bayes_v1",
        model_id="multinomial-nb-public-calibration",
        version="0.1.0",
        eligible_for_submission=False,
        prompt_hash=hashlib.sha256(b"naive_bayes_v1_unigram_alpha").hexdigest(),
    )

    def __init__(self, examples: list[TrainingExample], *, alpha: float = 1.0) -> None:
        if not examples:
            raise ValueError("naive Bayes requires training examples")
        if alpha <= 0:
            raise ValueError("alpha must be positive")
        self.alpha = float(alpha)
        self.labels = tuple(sorted(ALLOWED_LABELS))
        self.document_count = len(examples)
        self.label_document_counts: Counter[str] = Counter()
        self.term_counts = {label: Counter() for label in self.labels}
        self.total_terms: Counter[str] = Counter()
        self.vocabulary: set[str] = set()
        for example in examples:
            features = _features(example.case, example.chunks)
            self.label_document_counts[example.label] += 1
            self.term_counts[example.label].update(features)
            self.total_terms[example.label] += sum(features.values())
            self.vocabulary.update(features)

    def predict(
        self, case: PrivateCase, chunks: list[RetrievedChunk]
    ) -> OutcomePrediction:
        if not isinstance(case, PrivateCase):
            raise TypeError("naive Bayes predictor only accepts PrivateCase")
        if any(not isinstance(chunk, RetrievedChunk) for chunk in chunks):
            raise TypeError("chunks must contain RetrievedChunk objects")
        features = _features(case, tuple(chunks))
        label_count = len(self.labels)
        vocabulary_size = max(len(self.vocabulary), 1)
        scores: dict[str, float] = {}
        for label in self.labels:
            prior = (
                self.label_document_counts[label] + self.alpha
            ) / (self.document_count + self.alpha * label_count)
            score = math.log(prior)
            denominator = (
                self.total_terms[label] + self.alpha * vocabulary_size
            )
            for term, frequency in features.items():
                probability = (
                    self.term_counts[label][term] + self.alpha
                ) / denominator
                score += frequency * math.log(probability)
            scores[label] = score
        prediction = max(scores, key=scores.get)
        maximum = max(scores.values())
        weights = {label: math.exp(score - maximum) for label, score in scores.items()}
        confidence = weights[prediction] / sum(weights.values())
        return OutcomePrediction(
            prediction=prediction,
            confidence=confidence,
            rationale=f"Naive Bayes unigram; alpha={self.alpha:g}; private text + cached chunks.",
        )


def fit_naive_bayes(
    examples: list[TrainingExample], *, alpha: float = 1.0
) -> NaiveBayesOutcomeRunner:
    return NaiveBayesOutcomeRunner(examples, alpha=alpha)


def apply_high_precision_override(
    case: PrivateCase,
    chunks: list[RetrievedChunk],
    base_prediction: OutcomePrediction,
) -> OutcomePrediction:
    rule_prediction = predict_outcome(case, chunks)
    if (
        rule_prediction.prediction == "A_WIN"
        and rule_prediction.rationale
        == "Chunk có tín hiệu chấp nhận yêu cầu của nguyên đơn."
    ):
        return OutcomePrediction(
            prediction="A_WIN",
            confidence=max(base_prediction.confidence, rule_prediction.confidence),
            rationale="High-precision positive court-decision override over Naive Bayes.",
        )
    return base_prediction


def leave_one_out_predictions(
    examples: list[TrainingExample],
    *,
    alpha: float = 1.0,
    high_precision_override: bool = False,
) -> dict[str, OutcomePrediction]:
    if len(examples) < 2:
        raise ValueError("leave-one-out requires at least two examples")
    predictions: dict[str, OutcomePrediction] = {}
    for index, held_out in enumerate(examples):
        training = examples[:index] + examples[index + 1 :]
        runner = fit_naive_bayes(training, alpha=alpha)
        prediction = runner.predict(
            held_out.case, list(held_out.chunks)
        )
        if high_precision_override:
            prediction = apply_high_precision_override(
                held_out.case, list(held_out.chunks), prediction
            )
        predictions[held_out.case.case_id] = prediction
    return predictions
