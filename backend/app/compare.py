"""Align expected vs observed sequences and judge the target sound.

Two views of the same attempt:
  * letters  - Sarvam's verbatim transcript in native script (Tamil and
               Devanagari spell sounds almost one-to-one, so ழ/ள/ல are distinct)
  * phonemes - IPA symbols from the local wav2vec2 model
Each returns, for every place the target sound should occur, one of
"correct", "substituted" (with what) or "unclear".
"""
from collections import Counter

from . import g2p

# Sounds that are easy to swap for one another cost less to substitute,
# so the aligner pairs ழ with ள rather than with an unrelated letter.
_LETTER_GROUPS = [set("ழளலயரற"), set(g2p.normalize("रलयवड़")), set("शषसछच"), set("कखगघह"), set("டதணநன")]
_PHONE_GROUPS = [
    {"l", "ɭ", "ɻ", "ɾ", "r", "ɹ", "j", "ɽ", "ʐ", "ɖ", "ʋ", "w"},
    {"s", "ʃ", "ʂ", "ɕ", "tʃ", "tɕ", "ʈʂ", "z", "ʒ"},
    {"k", "kʰ", "ɡ", "g", "ɡʱ", "x", "h", "ɦ", "q"},
    {"n", "ɳ", "n̪", "ɲ", "ŋ", "m"},
    {"t", "t̪", "ʈ", "d", "d̪", "ɖ"},
]
_VOWELS = set("aeiouəɪʊɛɔæɐɑɒʌɨʉ")


def _phone_base(p: str) -> str:
    return p.replace("ː", "").replace("̪", "")


def _letter_cost(a: str, b: str) -> float:
    if a == b:
        return 0.0
    return 0.5 if any(a in g and b in g for g in _LETTER_GROUPS) else 1.0


def _phone_cost(a: str, b: str) -> float:
    a2, b2 = _phone_base(a), _phone_base(b)
    if a2 == b2:
        return 0.0
    if a2[0] in _VOWELS and b2[0] in _VOWELS:
        return 0.4
    return 0.5 if any(a2 in g and b2 in g for g in _PHONE_GROUPS) else 1.0


def align(expected: list[str], observed: list[str], cost) -> tuple[list[tuple[int | None, int | None]], float]:
    """Weighted Levenshtein alignment; returns index pairs and the total cost."""
    n, m = len(expected), len(observed)
    d = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        d[i][0] = float(i)
    for j in range(1, m + 1):
        d[0][j] = float(j)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost(expected[i - 1], observed[j - 1]))
    pairs = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + cost(expected[i - 1], observed[j - 1]):
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            pairs.append((i - 1, None))
            i -= 1
        else:
            pairs.append((None, j - 1))
            j -= 1
    return pairs[::-1], d[n][m]


def _summarize(checks: list[dict], similarity: float) -> dict:
    if not checks:
        return {"verdict": "unclear", "heard_as": None, "checks": checks, "similarity": similarity}
    subs = Counter(c["heard"] for c in checks if c["result"] == "substituted")
    correct = sum(c["result"] == "correct" for c in checks)
    if subs:
        heard, _ = subs.most_common(1)[0]
        verdict = "substitution"
    elif correct == len(checks):
        heard, verdict = None, "on_target"
    else:
        heard, verdict = None, "unclear"
    return {"verdict": verdict, "heard_as": heard, "checks": checks, "similarity": round(similarity, 2),
            "correct": correct, "total": len(checks)}


def check_transcript(item_text: str, transcript: str, target: dict) -> dict:
    letter = g2p.normalize(target["letter"])
    accept = {letter, *(g2p.normalize(a) for a in target.get("accept", []))}
    confusions = {g2p.normalize(k) for k in target["confusions"]}

    exp = [c for c in g2p.letters(item_text) if not c.isspace()]
    obs = [c for c in g2p.letters(transcript) if c.isalpha() or 0x0B80 <= ord(c) <= 0x0BFF or 0x0900 <= ord(c) <= 0x097F]
    if not obs:
        return {"verdict": "unclear", "heard_as": None, "checks": [], "similarity": 0.0, "reason": "empty transcript"}
    pairs, dist = align(exp, obs, _letter_cost)
    similarity = max(0.0, 1 - dist / max(len(exp), len(obs), 1))

    checks = []
    for i, j in pairs:
        if i is None or exp[i] != letter:
            continue
        got = obs[j] if j is not None else None
        if got in accept:
            res = "correct"
        elif got in confusions:
            res = "substituted"
        else:
            res = "unclear"
        checks.append({"position": i, "expected": letter, "heard": got, "result": res})

    out = _summarize(checks, similarity)
    # A transcript that barely resembles the item means a different word was
    # heard (or the recognizer guessed); don't draw sound-level conclusions.
    if similarity < 0.45:
        out.update(verdict="unclear", heard_as=None, reason="transcript does not match the target text")
    return out


def _to_vocab(p: str, vocab: set[str]) -> str:
    if not vocab or p in vocab:
        return p
    for cand in (p.replace("̪", ""), p.replace("ː", ""), _phone_base(p),
                 {"ɡ": "g", "ʋ": "v", "ɾ": "r", "ɻ": "ɹ", "ɡʱ": "ɡ", "ɦ": "h"}.get(p, "")):
        if cand and cand in vocab:
            return cand
    return p


def check_phonemes(item_text: str, tokens: list[dict], target: dict, vocab: set[str]) -> dict:
    lang = target["language"]
    letter = target["letter"]
    expected = g2p.to_ipa(item_text, lang)
    chars = g2p.letters(item_text)
    exp = [_to_vocab(p, vocab) for p, _ in expected]
    obs = [t["symbol"] for t in tokens]
    if not obs:
        return {"verdict": "unclear", "heard_as": None, "checks": [], "similarity": 0.0, "reason": "no phonemes detected",
                "expected_ipa": " ".join(exp), "observed_ipa": ""}

    target_ipa = _to_vocab(target["ipa"], vocab)
    accept = {_to_vocab(p, vocab) for p in target.get("accept_ipa", [target["ipa"]])} | {target_ipa}
    conf_by_ipa = {}
    for conf_letter, info in target["confusions"].items():
        conf_by_ipa.setdefault(_to_vocab(info["ipa"], vocab), conf_letter)
    # A confusion that maps to the same symbol as the target can't be told apart here.
    for a in accept:
        conf_by_ipa.pop(a, None)

    pairs, dist = align(exp, obs, _phone_cost)
    similarity = max(0.0, 1 - dist / max(len(exp), len(obs), 1))

    checks = []
    for i, j in pairs:
        if i is None or chars[expected[i][1]] != letter or _phone_base(expected[i][0]) != _phone_base(target["ipa"]):
            continue
        got = obs[j] if j is not None else None
        alts = tokens[j]["alts"] if j is not None else {}
        p_target = sum(v for k, v in alts.items() if k in accept)
        p_conf = {conf_by_ipa[k]: v for k, v in alts.items() if k in conf_by_ipa}
        if got in accept:
            res, heard = "correct", got
        elif got in conf_by_ipa:
            res, heard = "substituted", conf_by_ipa[got]
        else:
            res, heard = "unclear", got
        checks.append({"position": i, "expected": target_ipa, "heard": heard, "symbol": got, "result": res,
                       "p_target": round(p_target, 3), "p_confusions": p_conf})

    out = _summarize(checks, similarity)
    out["expected_ipa"] = " ".join(exp)
    out["observed_ipa"] = " ".join(obs)
    if target_ipa not in vocab and vocab:
        out.update(verdict="unclear", heard_as=None, reason=f"model has no symbol for {target['ipa']}")
    elif similarity < 0.5:
        out.update(verdict="unclear", heard_as=None, reason="phonemes do not match the target text")
    return out
