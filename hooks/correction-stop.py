#!/usr/bin/env python3
import json, os, re, subprocess, sys

CORRECT_COMMAND = re.compile(r"<command-name>/[\w-]*:?correct</command-name>")
CORRECTION_WORDS = re.compile(
    r"제대로|아직도|재발|자꾸|또 (안|않|그러|이러|틀)|왜 (안|않|자꾸|또|이렇게|그렇게)|하지 ?마|하지 ?말|말라고|라고 했"
    r"|할 때만|말했잖|했잖|잖아|안 ?하고|빼먹|틀렸|아니잖|직접 ?해야|해야지")
NOT_HUMAN = ("<task-notification", "<system-reminder", "This session is being continued", "<local-command", "<side-sessions", "<ci-monitor")
DEVICE_PATH = re.compile(r"test|spec|check|lint|guard|gate|verify|hook|\.github/workflows|pre-commit|ruff|eslint|clippy", re.I)
PROSE = (".md", ".txt")
WAIVED = ("장치화 불가", "교정 아님")
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
CORRECT_SKILL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills", "correct", "SKILL.md")


def human_text(d):
    if d.get("type") != "user" or d.get("isSidechain") or d.get("isMeta"):
        return None
    c = (d.get("message") or {}).get("content")
    if isinstance(c, list) and c and all(isinstance(b, dict) and b.get("type") == "text" for b in c):
        c = "".join(b["text"] for b in c)
    if not isinstance(c, str) or c.startswith(NOT_HUMAN):
        return None
    return c


def last_turn(lines):
    turn = None
    for line in lines:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        text = human_text(d)
        if text is not None:
            turn = {"text": text, "at": d.get("timestamp"), "edited": [], "said": []}
        elif turn and d.get("type") == "assistant" and not d.get("isSidechain"):
            for b in (d.get("message") or {}).get("content") or []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text":
                    turn["said"].append(b.get("text", ""))
                elif b.get("type") == "tool_use" and b.get("name") in EDIT_TOOLS:
                    turn["edited"].append((b.get("input") or {}).get("file_path") or (b.get("input") or {}).get("notebook_path") or "")
    return turn


def is_correction(text):
    if CORRECT_COMMAND.search(text):
        return True
    return bool(CORRECTION_WORDS.search(re.sub(r"<command-message>.*?</command-name>", "", text, flags=re.S)))


def changed_in_repo(cwd, since):
    if not cwd or not since:
        return []
    def git(*args):
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=3)
        return r.stdout.splitlines() if r.returncode == 0 else []
    committed = git("log", "--all", f"--since={since}", "--name-only", "--format=")
    dirty = [l[3:].split(" -> ")[-1] for l in git("status", "--porcelain", "--untracked-files=all")]
    return committed + dirty


def is_device(path):
    home_claude = os.path.join(os.path.expanduser("~"), ".claude") + os.sep
    return bool(path) and not path.startswith(home_claude) and not path.lower().endswith(PROSE) and bool(DEVICE_PATH.search(path))


def verdict(turn, repo_files):
    if not turn or not is_correction(turn["text"]):
        return None
    if any(w in t for t in turn["said"] for w in WAIVED):
        return None
    if any(is_device(p) for p in turn["edited"] + repo_files):
        return None
    quote = re.sub(r"<command-message>.*?</command-name>|</?command-args>", "", turn["text"], flags=re.S).strip()[:60]
    return (
        f"이번 턴의 사람 메시지 「{quote}」 는 교정이다. 그런데 이 턴에 저장소의 검사·테스트·훅·린트 파일이 하나도 바뀌지 않았다. "
        "메모리나 글로만 남긴 교정은 다음 에이전트가 건너뛰어도 아무것도 실패하지 않는다. "
        f"{CORRECT_SKILL} 를 Read 로 읽고 그 절차대로 이 저장소의 가장 높은 층(구조, 타입, 린트·검사, 테스트, 훅)에 장치를 넣고, "
        "그 장치가 이번 실수에서 실패하는 출력을 보고에 붙여라. "
        "판단이라 장치로 만들 수 없으면 보고에 「판단이라 장치화 불가: <이유>」 를, 교정이 아니었으면 「교정 아님: <이유>」 를 쓰고 끝낸다.")


if __name__ == "__main__":
    d = json.load(sys.stdin)
    if d.get("stop_hook_active"):
        sys.exit(0)
    try:
        turn = last_turn(open(d["transcript_path"], encoding="utf-8", errors="replace"))
        reason = verdict(turn, changed_in_repo(d.get("cwd"), turn and turn["at"]) if turn and is_correction(turn["text"]) else [])
    except Exception:
        sys.exit(0)
    if reason:
        print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
