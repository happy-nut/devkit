#!/usr/bin/env python3
"""hooks/guard-bash.py 의 merge_gate 가 자기 docstring의 약속을 지키는지 전수 검사한다.

약속(merge_gate 의 docstring): "바뀐 파일이 있는지, 체크가 다 붙고 다 초록인지 본다.
'no checks reported' 는 초록이 아니다(아직 안 붙었을 수 있다)."

이 약속은 fail-closed 다: gh 호출이 실패했거나, PR 나이를 알 수 없어 "아직 안 붙었을 수
있다"를 배제할 수 없으면, 머지를 허용(None)하지 말고 막아야 한다(deny). 이 스크립트는
실제 merge_gate 함수를 불러서, 파일 유무·createdAt 유무·checks 신호의 모든 조합에 대해
이 fail-closed 약속이 지켜지는지 본다. 코드를 손으로 베낀 모델이 아니라 fake gh 를 PATH
에 꽂아 진짜 함수를 돌린다.

실행: python3 .claude/skills/formal-guard-bash/check_merge_gate.py
"""
import datetime
import importlib.util
import io
import itertools
import os
import stat
import subprocess
import sys
import tempfile

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
GUARD_BASH = os.path.join(ROOT, "hooks", "guard-bash.py")

# "d = json.load(sys.stdin)" 가 import 시점에 바로 돈다. 빈 JSON 을 먹여서 그 한 줄만
# 무해하게 넘기고, 모듈이 끝까지 실행된 뒤 merge_gate 함수만 꺼내 쓴다. 코드를 복붙해
# 다시 쓰지 않는다. 검증이 보는 건 항상 이 파일 안의 진짜 함수다.
def load_merge_gate():
    old_stdin = sys.stdin
    sys.stdin = io.StringIO("{}")
    try:
        spec = importlib.util.spec_from_file_location("guard_bash_under_test", GUARD_BASH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.stdin = old_stdin
    return mod.merge_gate


def write_fake_gh(bindir, pr_json, checks_stdout, checks_rc):
    path = os.path.join(bindir, "gh")
    with open(path, "w") as f:
        f.write(f"""#!/bin/sh
if [ "$2" = "view" ]; then echo '{pr_json}'; exit 0; fi
printf '%s' '{checks_stdout}'; exit {checks_rc}
""")
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)


def pr_json(files, created):
    files_part = {"empty": '"files":[]', "nonempty": '"files":[{"path":"a"}]', "absent": ""}[files]
    now = datetime.datetime.now(datetime.timezone.utc)
    created_part = {
        "present_new": f'"createdAt":"{(now - datetime.timedelta(seconds=10)).strftime("%Y-%m-%dT%H:%M:%SZ")}"',
        "present_old": f'"createdAt":"{(now - datetime.timedelta(seconds=600)).strftime("%Y-%m-%dT%H:%M:%SZ")}"',
        "absent": "",
    }[created]
    parts = [p for p in (files_part, created_part, '"headRefOid":"abc"') if p]
    return "{" + ",".join(parts) + "}"


CHECKS_SIGNALS = {
    "no_checks": ("no checks reported on the branch", 1),
    "pending_rc8": ("test\\tpending\\t0", 8),
    "pending_substr": ("test\\tpending-ish\\t0", 0),
    "fail_rc1": ("test\\tfail\\t1m", 1),
    "fail_substr": ("test\\tfailure-note\\t0", 0),
    "pass": ("test\\tpass\\t1m", 0),
}


def expected(files, created, checks_signal):
    """docstring 이 말하는 fail-closed 약속. '확인 못 함'은 늘 deny."""
    if files == "empty":
        return "deny"
    if checks_signal == "no_checks":
        if created == "present_new":
            return "deny"
        if created == "present_old":
            return "allow"
        return "deny"  # createdAt 을 모르면 "아직 안 붙었을 수 있다"를 배제 못 한다
    if checks_signal in ("pending_rc8", "pending_substr", "fail_rc1", "fail_substr"):
        return "deny"
    return "allow"  # pass


KNOWN_GAPS = {
    # (files, created, checks_signal, exc) -> 지금 코드가 실제로 그렇게 동작한다고
    # 이미 확인한, 아직 고치지 않은 어긋남. 새 어긋남과 구별하려고 따로 둔다.
    ("nonempty", "absent", "no_checks", False): "createdAt 이 없으면 나이를 모르는데도 허용한다",
    ("absent", "absent", "no_checks", False): "createdAt 이 없으면 나이를 모르는데도 허용한다",
    ("exception",): "gh 호출 자체가 실패하면 아무것도 확인 못 한 채로 허용한다",
}


def run_once(merge_gate, files, created, checks_signal, exc):
    with tempfile.TemporaryDirectory() as t:
        if not exc:
            stdout, rc = CHECKS_SIGNALS[checks_signal]
            write_fake_gh(t, pr_json(files, created), stdout, rc)
            env_path = t + os.pathsep + os.environ["PATH"]
        else:
            env_path = t  # gh 가 없는 PATH. subprocess 가 FileNotFoundError 를 던진다.
        old_path = os.environ.get("PATH")
        os.environ["PATH"] = env_path
        try:
            reason = merge_gate("1", t)
        finally:
            if old_path is not None:
                os.environ["PATH"] = old_path
    return "deny" if reason else "allow"


def main():
    merge_gate = load_merge_gate()
    findings = []
    new_mismatches = []

    actual = run_once(merge_gate, "nonempty", "present_old", "pass", True)
    key = ("exception",)
    if actual != "deny":
        msg = f"gh 자체가 없는 PATH -> {actual} (기대 deny): {KNOWN_GAPS[key]}"
        if key in KNOWN_GAPS:
            findings.append(msg)
        else:
            new_mismatches.append(msg)

    for files, created, checks_signal in itertools.product(("empty", "nonempty", "absent"), ("present_new", "present_old", "absent"), CHECKS_SIGNALS):
        exp = expected(files, created, checks_signal)
        actual = run_once(merge_gate, files, created, checks_signal, False)
        if actual != exp:
            key = (files, created, checks_signal, False)
            msg = f"files={files} created={created} checks={checks_signal} -> {actual} (기대 {exp})"
            if key in KNOWN_GAPS:
                findings.append(f"{msg}: {KNOWN_GAPS[key]}")
            else:
                new_mismatches.append(msg)

    print(f"조합 {3*3*6 + 1}개 돌림.")
    if findings:
        print("\n알려진 어긋남(고치지 않고 보고만 함):")
        for f in findings:
            print(f"  - {f}")
    if new_mismatches:
        print("\n새 어긋남(지금까지 모르던 것, 코드나 이 모델을 확인해야 함):")
        for m in new_mismatches:
            print(f"  - {m}")
        sys.exit(1)
    print("\n새 어긋남 없음. 알려진 어긋남 수가 바뀌면(늘거나 줄면) 이 스킬을 다시 맞춘다.")
    if len(findings) != len(KNOWN_GAPS):
        print(f"알려진 어긋남 개수가 {len(KNOWN_GAPS)}개여야 하는데 {len(findings)}개다. 동기화가 깨졌다.")
        sys.exit(1)


if __name__ == "__main__":
    main()
