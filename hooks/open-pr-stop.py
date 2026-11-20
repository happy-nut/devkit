#!/usr/bin/env python3
import importlib.util, json, os, re, subprocess, sys

PR_URL = re.compile(r"https://github\.com/([\w.-]+)/([\w.-]+)/pull/(\d+)")
WAIVED = "머지 안 함"
HUMAN_SAYS_NO_MERGE = re.compile(r"머지(하지| ?말|는 하지| ?안 ?해)|merge 하지")
HERE = os.path.dirname(os.path.abspath(__file__))


def open_plan():
    spec = importlib.util.spec_from_file_location("open_plan_stop", os.path.join(HERE, "open-plan-stop.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def text_of(content):
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") if isinstance(b, dict) else "" for b in content or [])


def opened_prs(lines):
    creates, prs, waived, human_no, blocked = set(), [], False, False, False
    for line in lines:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("isSidechain"):
            continue
        content = (d.get("message") or {}).get("content")
        if d.get("type") == "user":
            if isinstance(content, str) and not d.get("isMeta") and not d.get("isCompactSummary") and HUMAN_SAYS_NO_MERGE.search(content):
                human_no = True
            for b in content if isinstance(content, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") in creates:
                    for m in PR_URL.finditer(text_of(b.get("content"))):
                        if m.group(0) not in prs:
                            prs.append(m.group(0))
            continue
        if d.get("type") != "assistant" or not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "text" and WAIVED in b.get("text", ""):
                waived = True
            if b.get("type") != "tool_use":
                continue
            inp = b.get("input") or {}
            if b.get("name") == "Bash" and "gh pr create" in inp.get("command", ""):
                creates.add(b.get("id"))
            if b.get("name") == "mcp__ccd_turn__wrap_up":
                blocked = bool(inp.get("blocked"))
            if b.get("name") == "mcp__ccd_turn__wrap_up" and WAIVED in (inp.get("recap") or ""):
                waived = True
    return prs, waived or human_no or blocked


def personal_owners():
    path = os.path.expanduser("~/.claude/devkit.json")
    if not os.path.exists(path):
        return set()
    return set(json.load(open(path)).get("personal", {}).get("owners", []))


def still_open(url):
    r = subprocess.run(["gh", "pr", "view", url, "--json", "state", "-q", ".state"], capture_output=True, text=True, timeout=8)
    return r.returncode == 0 and r.stdout.strip() == "OPEN"


def verdict(path):
    prs, excused = opened_prs(open(path, encoding="utf-8", errors="replace"))
    if not prs or excused:
        return None
    _, waiting = open_plan().replay(open(path, encoding="utf-8", errors="replace"))
    if waiting:
        return None
    owners = personal_owners()
    left = [u for u in prs if PR_URL.match(u).group(1) in owners and still_open(u)]
    if not left:
        return None
    return (
        f"이 세션이 연 개인 저장소 PR 이 머지되지 않은 채 열려 있다: {', '.join(left)}. "
        "개인 저장소에서 「고쳐」는 머지까지다. 체크를 gh pr checks <번호> --watch 로 끝까지 기다리고, 실패하면 고쳐서 머지하라. "
        "사람이 머지하지 말라고 했거나 사람만 정할 일이 남았으면 보고에 「머지 안 함: <이유>」 를 쓰고 끝낸다.")


if __name__ == "__main__":
    d = json.load(sys.stdin)
    if d.get("stop_hook_active"):
        sys.exit(0)
    try:
        reason = verdict(d["transcript_path"])
    except Exception:
        sys.exit(0)
    if reason:
        print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
