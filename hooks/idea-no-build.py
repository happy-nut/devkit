#!/usr/bin/env python3
import json, os, re, sys

COMMAND = re.compile(r"<command-name>/dev:([\w-]+)</command-name>")
SHIP = re.compile(r"\b(git\s+(commit|push|merge|rebase|cherry-pick)|gh\s+pr\s+(create|merge))\b")
SCRATCH = ("/tmp/", "/private/tmp/", "/var/folders/", os.path.expanduser("~/.claude/"))


def last_command(path):
    last = None
    for line in open(path, encoding="utf-8", errors="replace"):
        if "<command-name>/dev:" not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        c = (d.get("message") or {}).get("content")
        if d.get("type") == "user" and not d.get("isSidechain") and isinstance(c, str) and c.lstrip().startswith("<command-"):
            found = COMMAND.findall(c)
            if found:
                last = found[-1]
    return last


def main():
    d = json.load(sys.stdin)
    try:
        if last_command(d["transcript_path"]) != "idea":
            return
    except Exception:
        return
    inp = d.get("tool_input") or {}
    if d.get("tool_name") == "Bash":
        if not SHIP.search(inp.get("command", "")):
            return
        what = "커밋·푸시·PR"
    else:
        path = os.path.realpath(inp.get("file_path") or inp.get("notebook_path") or "")
        if path.startswith(tuple(os.path.realpath(p) + "/" for p in SCRATCH)):
            return
        what = f"작업 폴더 파일 편집({path})"
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": (
        f"/dev:idea 는 문제를 정하고 멈춘다. 구현하지 않는다. 방금 {what}을 하려 했다. "
        "고른 문제와 /dev:mode 프롬프트를 보고에 쓰고 턴을 끝내라. 구현은 사람이 그 프롬프트로 /dev:mode 를 불러서 한다. "
        "세기 스크립트는 /tmp 나 스크래치패드에 쓴다.")}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
