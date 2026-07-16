from __future__ import annotations

import re
import unicodedata

from ..schemas import OutcomePrediction, PrivateCase, RetrievedChunk


def _ascii_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    without_marks = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    ).replace("đ", "d")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", without_marks).split())


_PARTIAL_A_PATTERNS = (
    "chap nhan mot phan yeu cau khoi kien",
    "chap nhan mot phan yeu cau cua nguyen don",
)
_PARTIAL_B_PATTERNS = (
    "chap nhan mot phan yeu cau phan to",
    "chap nhan mot phan yeu cau cua bi don",
)
_NEGATIVE_PATTERNS = (
    "khong chap nhan yeu cau khoi kien",
    "khong chap nhan toan bo yeu cau khoi kien",
    "bac toan bo yeu cau khoi kien",
    "bac yeu cau khoi kien cua nguyen don",
    "yeu cau khoi kien khong co can cu",
)
_POSITIVE_PATTERNS = (
    "chap nhan toan bo yeu cau khoi kien",
    "chap nhan yeu cau khoi kien cua nguyen don",
    "chap nhan yeu cau cua nguyen don",
    "yeu cau khoi kien la co can cu",
    "buoc bi don",
)


def _count_patterns(text: str, patterns: tuple[str, ...]) -> int:
    return sum(text.count(pattern) for pattern in patterns)


def _fallback_from_query(query: str) -> OutcomePrediction:
    normalized = _ascii_text(query)
    strong_claims = (
        "ngan hang",
        "tra no",
        "hop dong vay",
        "tien hui",
        "hoan tra",
    )
    if any(pattern in normalized for pattern in strong_claims):
        return OutcomePrediction(
            prediction="A_WIN",
            confidence=0.38,
            rationale="Fallback: yêu cầu nghĩa vụ thanh toán/bồi thường có chứng cứ mô tả rõ.",
        )
    partial_claims = (
        "boi thuong",
        "thua ke",
        "chia di san",
        "chia tai san",
        "quyen su dung dat",
        "huy giay chung nhan",
        "nhieu khoan",
    )
    if any(pattern in normalized for pattern in partial_claims):
        return OutcomePrediction(
            prediction="PARTIAL_A_WIN",
            confidence=0.34,
            rationale="Fallback: tranh chấp thường có nhiều hạng mục nên ưu tiên khả năng chấp nhận một phần.",
        )
    return OutcomePrediction(
        prediction="PARTIAL_A_WIN",
        confidence=0.30,
        rationale="Fallback: chưa có tín hiệu phán quyết; dùng prior chấp nhận một phần.",
    )


_JUDICIAL_MARKERS = (
    "quyet dinh",
    "tuyen xu",
    "hoi dong xet xu nhan dinh",
    "hoi dong xet xu xet thay",
    "xet thay",
    "vi cac le tren",
)
_PARTY_SPEECH_MARKERS = (
    "nguyen don trinh bay",
    "bi don trinh bay",
    "nguyen don yeu cau",
    "bi don yeu cau",
    "yeu cau toa an",
    "khong dong y boi thuong",
    "tai don khoi kien",
    "kiem sat vien de nghi",
)


def _decision_evidence(chunks: list[RetrievedChunk] | tuple[RetrievedChunk, ...]) -> str:
    accepted: list[str] = []
    for chunk in chunks:
        normalized = _ascii_text(chunk.text)
        judicial_positions = [
            normalized.find(marker)
            for marker in _JUDICIAL_MARKERS
            if marker in normalized
        ]
        if judicial_positions:
            accepted.append(normalized[min(judicial_positions) :])
            continue
        if any(marker in normalized for marker in _PARTY_SPEECH_MARKERS):
            continue
        accepted.append(normalized)
    return " ".join(accepted)


def predict_outcome(
    case: PrivateCase, chunks: list[RetrievedChunk] | tuple[RetrievedChunk, ...] = ()
) -> OutcomePrediction:
    if not isinstance(case, PrivateCase):
        raise TypeError("predict_outcome only accepts PrivateCase")
    if any(not isinstance(chunk, RetrievedChunk) for chunk in chunks):
        raise TypeError("chunks must contain RetrievedChunk objects")
    if not chunks:
        return _fallback_from_query(case.case_query)

    evidence = _decision_evidence(chunks)
    if not evidence:
        return _fallback_from_query(case.case_query)
    partial_a = _count_patterns(evidence, _PARTIAL_A_PATTERNS)
    partial_b = _count_patterns(evidence, _PARTIAL_B_PATTERNS)
    negative = _count_patterns(evidence, _NEGATIVE_PATTERNS)

    positive_text = evidence
    for pattern in _NEGATIVE_PATTERNS + _PARTIAL_A_PATTERNS + _PARTIAL_B_PATTERNS:
        positive_text = positive_text.replace(pattern, " ")
    positive = _count_patterns(positive_text, _POSITIVE_PATTERNS)

    if partial_b and negative >= positive:
        return OutcomePrediction(
            prediction="PARTIAL_B_WIN",
            confidence=0.78,
            rationale="Chunk có quyết định chấp nhận một phần yêu cầu của bị đơn/phản tố.",
        )
    if partial_a:
        return OutcomePrediction(
            prediction="PARTIAL_A_WIN",
            confidence=0.82,
            rationale="Chunk nêu rõ chấp nhận một phần yêu cầu của nguyên đơn.",
        )
    if positive and negative:
        return OutcomePrediction(
            prediction="PARTIAL_A_WIN",
            confidence=0.62,
            rationale="Chunk đồng thời có phần chấp nhận và phần bác yêu cầu.",
        )
    if negative:
        return OutcomePrediction(
            prediction="B_WIN",
            confidence=0.80,
            rationale="Chunk có tín hiệu bác/không chấp nhận yêu cầu khởi kiện.",
        )
    if positive:
        return OutcomePrediction(
            prediction="A_WIN",
            confidence=0.80,
            rationale="Chunk có tín hiệu chấp nhận yêu cầu của nguyên đơn.",
        )
    return _fallback_from_query(case.case_query)
