#!/usr/bin/env python3
"""Stop 훅: 사용자에게 한 마지막 말이 한국어가 아니면 한 번 되돌린다. 판정은 korean.py."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from korean import not_korean

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
if not_korean(text):
    print(json.dumps({"decision": "block", "reason": (
        "사용자에게 하는 말은 한국어로 쓴다. 방금 마지막 말이 한국어가 아니었다(한국어 낱말이 절반이 안 됨). "
        "코드·명령·경로·고유 이름만 그대로 두고 같은 내용을 한국어로 다시 써라.")}, ensure_ascii=False))
