"""korean-stop.py 와 tool-text.py 가 같이 쓰는 「한국어가 아닌가」 판정. 코드·경로·URL·백틱 안은 세지 않는다.

낱말(글자가 든 토막) 수로 센다: 한글 한 음절이 영어 여러 글자만큼의 뜻을 실어서, 글자로 세면 영어 낱말이 섞인 한국어 문장이 잘못 걸린다.
- 글자 12개 이상: 한글이 든 낱말이 절반이 안 되면 한국어가 아니다.
- 그보다 짧으면(버튼·짧은 줄): 한글 낱말이 하나도 없고 글자 낱말이 둘 이상일 때만. 「Yes, fix 1」은 걸리고 「Done.」「OK」「PR 머지」는 통과."""
import re


def not_korean(text):
    prose = re.sub(r"```.*?```", " ", text or "", flags=re.S)
    prose = re.sub(r"`[^`]*`|https?://\S+|\[[^\]]*\]\([^)]*\)|[\w./~-]*/[\w./-]+", " ", prose)
    words = [w for w in prose.split() if any(ch.isalpha() for ch in w)]
    korean = sum(1 for w in words if re.search(r"[가-힣ㄱ-ㅎㅏ-ㅣ]", w))
    if sum(1 for ch in prose if ch.isalpha()) >= 12:
        return korean * 2 < len(words)
    return korean == 0 and len(words) >= 2
