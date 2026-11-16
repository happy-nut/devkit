#!/usr/bin/env python3
"""Stop 훅: 사용자에게 한 마지막 말이 한국어가 아니면 한 번 되돌린다. 코드·경로·URL·백틱 안은 세지 않는다.

「한국어가 아니다」 = 낱말(글자가 든 토막) 중 한글이 든 낱말이 절반이 안 된다. 영어·일본어·중국어 모두 해당.
글자 수가 아니라 낱말 수로 센다: 한글 한 음절이 영어 여러 글자만큼의 뜻을 실어서, 글자로 세면 영어 낱말이 섞인 한국어 문장이 잘못 걸린다."""
import json, re, sys

d = json.load(sys.stdin)
if d.get("stop_hook_active"):
    sys.exit(0)
text = ""
try:
    for line in open(d["transcript_path"], encoding="utf-8"):
        m = json.loads(line)
        if m.get("type") == "assistant" and not m.get("isSidechain"):
            t = "".join(c.get("text", "") for c in m["message"].get("content", []) if isinstance(c, dict) and c.get("type") == "text")
            if t.strip():
                text = t
except Exception:
    sys.exit(0)
prose = re.sub(r"```.*?```", " ", text, flags=re.S)
prose = re.sub(r"`[^`]*`|https?://\S+|\[[^\]]*\]\([^)]*\)|[\w./~-]*/[\w./-]+", " ", prose)
words = [w for w in prose.split() if any(ch.isalpha() for ch in w)]
korean = sum(1 for w in words if re.search(r"[가-힣ㄱ-ㅎㅏ-ㅣ]", w))
letters = sum(1 for ch in prose if ch.isalpha())
if letters >= 12 and korean * 2 < len(words):
    print(json.dumps({"decision": "block", "reason": (
        "사용자에게 하는 말은 한국어로 쓴다. 방금 마지막 말이 한국어가 아니었다(한국어 낱말이 절반이 안 됨). "
        "코드·명령·경로·고유 이름만 그대로 두고 같은 내용을 한국어로 다시 써라.")}, ensure_ascii=False))
