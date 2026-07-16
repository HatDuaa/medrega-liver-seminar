from __future__ import annotations

import re
import unicodedata

from ..schemas import LawEvidence
from .index import LawIndex


LAW_ALIASES: dict[str, tuple[str, ...]] = {
    "92/2015/QH13": ("bo luat to tung dan su 2015", "bo luat to tung dan su"),
    "91/2015/QH13": ("bo luat dan su nam 2015", "bo luat dan su 2015"),
    "52/2014/QH13": ("luat hon nhan va gia dinh nam 2014", "luat hon nhan va gia dinh"),
    "45/2013/QH13": ("luat dat dai nam 2013", "luat dat dai 2013"),
    "326/2016/UBTVQH14": ("nghi quyet so 326 2016 ubtvqh14", "nghi quyet 326 2016"),
    "26/2008/QH12": ("luat thi hanh an dan su",),
    "60/2014/QH13": ("luat ho tich",),
    "52/2010/QH12": ("luat nuoi con nuoi",),
    "66/2014/QH13": ("luat kinh doanh bat dong san",),
    "47/2010/QH12": ("luat cac to chuc tin dung",),
    "100/2015/QH13": ("bo luat hinh su 2015", "bo luat hinh su"),
    "93/2015/QH13": ("luat to tung hanh chinh",),
    "02/2011/QH13": ("luat khieu nai",),
    "39/2009/QH12": ("luat nguoi cao tuoi",),
    "50/2014/QH13": ("luat xay dung",),
    "37/2015/NĐ-CP": ("nghi dinh 37 2015 nd cp",),
    "24/2012/NĐ-CP": ("nghi dinh 24 2012 nd cp",),
}


def _ascii_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    without_marks = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    ).replace("đ", "d")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", without_marks).split())


def resolve_law_citations(index: LawIndex, text: str) -> tuple[LawEvidence, ...]:
    evidence: list[LawEvidence] = []
    seen: set[tuple[str, int]] = set()
    for raw_line in text.splitlines() or [text]:
        line = _ascii_text(raw_line)
        if not line:
            continue
        law_id = next(
            (
                candidate
                for candidate, aliases in LAW_ALIASES.items()
                if any(alias in line for alias in aliases)
            ),
            None,
        )
        if law_id is None:
            continue
        for match in re.finditer(r"\bdieu\s+(\d{1,4})\b", line):
            article = index.article_by_number(law_id, int(match.group(1)))
            if article is None:
                continue
            pair = (article.law_id, article.aid)
            if pair in seen:
                continue
            seen.add(pair)
            evidence.append(LawEvidence(law_id=pair[0], aid=pair[1]))
    return tuple(evidence)


def retrieve_law_evidence(
    index: LawIndex, query: str, *, top_k: int = 3
) -> tuple[LawEvidence, ...]:
    seen: set[tuple[str, int]] = set()
    evidence: list[LawEvidence] = []
    for item in resolve_law_citations(index, query):
        pair = (item.law_id, item.aid)
        seen.add(pair)
        evidence.append(item)
        if len(evidence) == top_k:
            return tuple(evidence)
    for hit in index.search(query, top_k=max(top_k * 2, top_k)):
        pair = (hit.article.law_id, hit.article.aid)
        if pair in seen:
            continue
        seen.add(pair)
        evidence.append(LawEvidence(law_id=pair[0], aid=pair[1]))
        if len(evidence) == top_k:
            break
    return tuple(evidence)
