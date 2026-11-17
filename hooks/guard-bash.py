#!/usr/bin/env python3
"""PreToolUse(Bash) 훅: 사고를 낸 적 있는 명령 모양을 막는다."""
import json, re, sys

d = json.load(sys.stdin)
cmd = (d.get("tool_input") or {}).get("command", "")
RULES = [
    (r"pytest[^\n;]*\|[^\n;]*&&[^\n]*(git\s+commit|gh\s+pr\s+merge)",
     "pytest 를 파이프(| tail 등)로 넘긴 뒤 && 로 커밋·머지하면 실패가 삼켜진다(실패한 테스트가 그대로 머지된 적이 있다). 테스트를 따로 돌려 결과 줄을 확인한 다음 커밋·머지를 따로 하라."),
]
def deny(why):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": why}}, ensure_ascii=False))
    sys.exit(0)


def merge_gate(pr, cwd, repo=None):
    """머지 직전에 바뀐 파일이 있는지, 체크가 다 붙고 다 초록인지 본다. 「no checks reported」는 초록이 아니다(체크가 아직 안 붙었을 수 있다)."""
    import subprocess, datetime
    sel = ["-R", repo] if repo else []
    try:
        info = json.loads(subprocess.run(["gh", "pr", "view", pr, *sel, "--json", "createdAt,headRefOid,files"], cwd=cwd, capture_output=True, text=True, timeout=10).stdout or "{}")
        checks = subprocess.run(["gh", "pr", "checks", pr, *sel], cwd=cwd, capture_output=True, text=True, timeout=10)
    except Exception:
        return None
    if "files" in info and not info["files"]:
        return "이 PR 은 바뀐 파일이 0개다(이미 main 에 들어갔거나 커밋이 빠졌다). 머지하지 말고 gh pr view <번호> --json files,commits 로 무엇이 빠졌는지 보라."
    out = (checks.stdout + checks.stderr).lower()
    if "could not resolve" in out:
        return f"이 폴더의 저장소에서 PR #{pr} 을 못 찾았다. 다른 저장소의 PR 이면 --repo <소유자/저장소> 를 붙이거나 그 폴더로 cd 한 뒤 && 로 이어 머지하라."
    if "no checks reported" in out:
        created = info.get("createdAt")
        if created:
            age = datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))
            if age.total_seconds() < 180:
                return "이 PR 에 아직 체크가 하나도 안 붙었다(만든 지 3분 안). 「no checks reported」는 초록이 아니다. 체크가 붙어 다 통과할 때까지 기다린 뒤 머지하라(gh pr checks <번호> --watch). 정말 체크가 없는 경로면 3분 뒤에 다시 머지하면 통과한다."
        return None
    if checks.returncode == 8 or "pending" in out:
        return "아직 도는 체크가 있다. gh pr checks <번호> --watch 로 끝까지 기다린 뒤 머지하라."
    if checks.returncode == 1 or "fail" in out:
        return "실패한 체크가 있다. 고치기 전에는 머지하지 않는다."
    return None


m = re.search(r"\bgh\s+pr\s+merge\s+(\d+)(?![^\n;&|]*--auto)", cmd)
if m:
    # 훅은 명령을 돌리기 전에 판정하므로, 명령 맨 앞의 cd 와 --repo 를 직접 읽어 그 저장소의 PR 을 본다
    import os
    lead = re.match(r"\s*cd\s+(\S+)\s*&&", cmd)
    cwd = os.path.join(d.get("cwd") or ".", os.path.expanduser(lead.group(1))) if lead else d.get("cwd")
    repo = re.search(r"(?:-R|--repo)[ =](\S+)", cmd[m.start():].split("\n")[0])
    why = merge_gate(m.group(1), cwd, repo.group(1) if repo else None)
    if why:
        deny(why)

for pat, why in RULES:
    if re.search(pat, cmd):
        deny(why)
