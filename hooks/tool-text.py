#!/usr/bin/env python3
"""PreToolUse 훅: 사용자가 읽는 도구 인자(요약·작업 목록·버튼·질문·명령 설명)가 한국어가 아니면 막는다.
AskUserQuestion 은 질문이 둘 이상이어도 막는다. 판정은 korean.py."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from korean import not_korean

d = json.load(sys.stdin)
tool, i = d.get("tool_name", ""), d.get("tool_input") or {}


def each(key):
    return [x for x in i.get(key) or [] if isinstance(x, dict)]


FIELDS = {
    "mcp__ccd_turn__wrap_up": lambda: [i.get("recap"), i.get("ask")] + [a.get("label") for a in each("actions")],
    "mcp__ccd_turn__update_plan": lambda: [x.get("content") for x in each("items")],
    "SendUserFile": lambda: [i.get("caption")],
    "AskUserQuestion": lambda: [t for q in each("questions") for t in [q.get("question"), q.get("header")] + [x for o in q.get("options") or [] if isinstance(o, dict) for x in (o.get("label"), o.get("description"))]],
    "Bash": lambda: [i.get("description")],
}


def deny(why):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": why}}, ensure_ascii=False))
    sys.exit(0)


if tool == "AskUserQuestion" and len(each("questions")) >= 2:
    deny("질문은 가장 중요한 하나만 한다. 나머지는 가장 나은 기본값으로 정해 진행하고, 무엇으로 정했는지 보고에 적어라.")
for text in (FIELDS.get(tool) or list)():
    if isinstance(text, str) and not_korean(text):
        deny(f"사용자가 읽는 글은 한국어로 다시 써라(코드·경로·고유 이름만 그대로): {text[:80]!r}")
