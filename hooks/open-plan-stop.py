#!/usr/bin/env python3
import json, re, sys

PLAN_TOOLS = ("mcp__ccd_turn__update_plan", "TodoWrite")
NOT_HUMAN = ("<task-notification", "<system-reminder", "This session is being continued", "<local-command", "<side-sessions", "<ci-monitor", "Stop hook feedback")
NOTIFIED = re.compile(r"<tool-use-id>(toolu_[A-Za-z0-9]+)</tool-use-id>")


def states(lines):
    plan, waiting, paused, resumed = None, set(), None, None
    for line in lines:
        yield (0 if plan is None else sum(s != "completed" for s in plan)), len(waiting)
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("isSidechain"):
            continue
        content = (d.get("message") or {}).get("content")
        if d.get("type") != "assistant":
            if paused and isinstance(content, str) and not d.get("isMeta") and not content.startswith(NOT_HUMAN):
                plan, resumed, paused = paused, list(paused), None
            waiting -= set(NOTIFIED.findall(line))
            for b in content if isinstance(content, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_result" and "background" not in json.dumps(b.get("content")) and "Async" not in json.dumps(b.get("content")):
                    waiting.discard(b.get("tool_use_id"))
            continue
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            name, inp = b.get("name"), b.get("input") or {}
            if inp.get("run_in_background") or name == "Agent":
                waiting.add(b.get("id"))
            if name == "mcp__ccd_turn__wrap_up":
                if inp.get("blocked") and plan and any(x != "completed" for x in plan):
                    paused, plan = plan, None
                elif not (resumed is not None and plan == resumed):
                    plan, resumed = None, None
            elif name in PLAN_TOOLS and ("items" in inp or "todos" in inp):
                plan = [i.get("status") for i in inp.get("items") or inp.get("todos") or []]
            elif name == PLAN_TOOLS[0] and plan:
                for k in inp.get("done") or []:
                    if 0 < k <= len(plan):
                        plan[k - 1] = "completed"
                if inp.get("advance"):
                    cur = next((i for i, s in enumerate(plan) if s == "in_progress"), None)
                    if cur is not None:
                        plan[cur] = "completed"
                    nxt = next((i for i, s in enumerate(plan) if s == "pending"), None)
                    if nxt is not None:
                        plan[nxt] = "in_progress"
                start = inp.get("start")
                if isinstance(start, int) and 0 < start <= len(plan):
                    plan[start - 1] = "in_progress"
    yield (0 if plan is None else sum(s != "completed" for s in plan)), len(waiting)


def replay(lines):
    *_, last = states(lines)
    return last


if __name__ == "__main__":
    d = json.load(sys.stdin)
    if d.get("stop_hook_active"):
        sys.exit(0)
    try:
        left, waiting = replay(open(d["transcript_path"], encoding="utf-8", errors="replace"))
    except Exception:
        sys.exit(0)
    if left and not waiting:
        print(json.dumps({"decision": "block", "reason": (
            f"작업 목록에 끝나지 않은 단계가 {left}개 남았는데 마무리(wrap_up) 없이 턴을 닫으려 한다. "
            "남은 단계를 지금 이어서 하라. 사람에게 물어 기다렸다가 답을 받았으면 멈춘 단계부터 끝까지 간다. 사람만 할 수 있는 일(비밀번호, 결제, 취향 결정)에 막혔으면 "
            "그 이유를 recap 에 적어 wrap_up 을 부르고 끝낸다. 계획이 바뀌었으면 update_plan 으로 목록을 고친다.")},
            ensure_ascii=False))
