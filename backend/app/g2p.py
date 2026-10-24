"""Approximate grapheme-to-IPA for Tamil and Hindi.

Good enough to give the phoneme aligner an expected sequence; not a full
phonology. Each output phoneme keeps the index of the letter it came from,
so a target letter can be found again after alignment.
"""
import unicodedata

TA_CONS = {
    "க": "k", "ங": "ŋ", "ச": "tʃ", "ஞ": "ɲ", "ட": "ʈ", "ண": "ɳ", "த": "t̪", "ந": "n",
    "ப": "p", "ம": "m", "ய": "j", "ர": "ɾ", "ல": "l", "வ": "ʋ", "ழ": "ɻ", "ள": "ɭ",
    "ற": "r", "ன": "n", "ஜ": "dʒ", "ஷ": "ʂ", "ஸ": "s", "ஹ": "h",
}
TA_VOWELS = {
    "அ": "a", "ஆ": "aː", "இ": "i", "ஈ": "iː", "உ": "u", "ஊ": "uː", "எ": "e", "ஏ": "eː",
    "ஐ": "ai", "ஒ": "o", "ஓ": "oː", "ஔ": "au",
}
TA_SIGNS = {
    "ா": "aː", "ி": "i", "ீ": "iː", "ு": "u", "ூ": "uː", "ெ": "e", "ே": "eː", "ை": "ai",
    "ொ": "o", "ோ": "oː", "ௌ": "au",
}
TA_VIRAMA = "்"

HI_CONS = {
    "क": "k", "ख": "kʰ", "ग": "ɡ", "घ": "ɡʱ", "ङ": "ŋ", "च": "tʃ", "छ": "tʃʰ", "ज": "dʒ",
    "झ": "dʒʱ", "ञ": "ɲ", "ट": "ʈ", "ठ": "ʈʰ", "ड": "ɖ", "ढ": "ɖʱ", "ण": "ɳ", "त": "t̪",
    "थ": "t̪ʰ", "द": "d̪", "ध": "d̪ʱ", "न": "n", "प": "p", "फ": "pʰ", "ब": "b", "भ": "bʱ",
    "म": "m", "य": "j", "र": "ɾ", "ल": "l", "व": "ʋ", "श": "ʃ", "ष": "ʃ", "स": "s", "ह": "ɦ",
    # precomposed nukta letters (see normalize)
    "ड़": "ɽ", "ढ़": "ɽʱ", "ज़": "z", "फ़": "f", "ख़": "x", "क़": "q", "ग़": "ɣ",
}
HI_VOWELS = {
    "अ": "ə", "आ": "aː", "इ": "ɪ", "ई": "iː", "उ": "ʊ", "ऊ": "uː", "ए": "eː", "ऐ": "ɛː",
    "ओ": "oː", "औ": "ɔː", "ऋ": "ɾɪ",
}
HI_SIGNS = {
    "ा": "aː", "ि": "ɪ", "ी": "iː", "ु": "ʊ", "ू": "uː", "े": "eː", "ै": "ɛː", "ो": "oː",
    "ौ": "ɔː", "ृ": "ɾɪ",
}
HI_VIRAMA = "्"
NUKTA = "़"
_NUKTA_LETTERS = {"ड": "ड़", "ढ": "ढ़", "ज": "ज़", "फ": "फ़",
                  "ख": "ख़", "क": "क़", "ग": "ग़"}


def normalize(text: str) -> str:
    """NFC, then fold consonant+nukta into one precomposed letter.

    NFC itself decomposes these (they are composition exclusions), so without
    this step ड़ would be two letters and never match a single-letter key.
    """
    text = unicodedata.normalize("NFC", text)
    for base, composed in _NUKTA_LETTERS.items():
        text = text.replace(base + NUKTA, composed)
    return text


def letters(text: str) -> list[str]:
    """Split normalized text into letters, keeping precomposed nukta letters whole."""
    return list(normalize(text))


def _word_to_ipa(chars: list[tuple[int, str]], lang: str) -> list[tuple[str, int, bool]]:
    """Return (phoneme, letter_index, is_inherent_schwa) for one word."""
    if lang == "ta-IN":
        cons, vowels, signs, virama, inherent = TA_CONS, TA_VOWELS, TA_SIGNS, TA_VIRAMA, "a"
    else:
        cons, vowels, signs, virama, inherent = HI_CONS, HI_VOWELS, HI_SIGNS, HI_VIRAMA, "ə"

    out: list[tuple[str, int, bool]] = []
    i = 0
    while i < len(chars):
        idx, ch = chars[i]
        nxt = chars[i + 1][1] if i + 1 < len(chars) else ""
        if ch in cons:
            out.append((cons[ch], idx, False))
            if nxt == virama:
                i += 2
                continue
            if nxt in signs:
                out.append((signs[nxt], chars[i + 1][0], False))
                i += 2
                continue
            out.append((inherent, idx, True))
        elif ch in vowels:
            out.append((vowels[ch], idx, False))
        elif ch == "ं":
            out.append(("n", idx, False))
        elif ch == "ः":
            out.append(("h", idx, False))
        # chandrabindu and other marks only nasalize/modify; skip them
        i += 1

    if lang == "hi-IN":
        out = _hindi_schwa_deletion(out)
    return out


def _is_vowel(p: str) -> bool:
    return p[0] in "aeiouəɪʊɛɔ"


def _hindi_schwa_deletion(seq):
    seq = list(seq)
    # word-final inherent schwa
    if len(seq) > 2 and seq[-1][2]:
        seq.pop()
    # medial: V C ə C V  ->  V C C V  (applied left to right, once per position)
    i = 2
    while i < len(seq) - 2:
        p, _, inherent = seq[i]
        if inherent and _is_vowel(seq[i - 2][0]) and not _is_vowel(seq[i - 1][0]) \
                and not _is_vowel(seq[i + 1][0]) and _is_vowel(seq[i + 2][0]):
            seq.pop(i)
            i += 2
            continue
        i += 1
    return seq


def to_ipa(text: str, lang: str) -> list[tuple[str, int]]:
    """Phonemes for a phrase, each paired with the index of its source letter."""
    chars = letters(text)
    result: list[tuple[str, int]] = []
    word: list[tuple[int, str]] = []
    for idx, ch in enumerate(chars + [" "]):
        if ch.isspace() or ch in ",.?!।":
            if word:
                result.extend((p, li) for p, li, _ in _word_to_ipa(word, lang))
                word = []
        else:
            word.append((idx, ch))
    return result
