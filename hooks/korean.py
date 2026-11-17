import re

LETTERS_FOR_RATIO_TEST = 12


def outside_code(text):
    prose = re.sub(r"```.*?```", " ", text or "", flags=re.S)
    return re.sub(r"`[^`]*`|https?://\S+|\[[^\]]*\]\([^)]*\)|[\w./~-]*/[\w./-]+", " ", prose)


def has_hangul(word):
    return re.search(r"[가-힣ㄱ-ㅎㅏ-ㅣ]", word) is not None


def not_korean(text):
    prose = outside_code(text)
    words = [w for w in prose.split() if any(ch.isalpha() for ch in w)]
    korean_words = sum(1 for w in words if has_hangul(w))
    if sum(1 for ch in prose if ch.isalpha()) >= LETTERS_FOR_RATIO_TEST:
        return korean_words < len(words) / 2
    return korean_words == 0 and len(words) >= 2
