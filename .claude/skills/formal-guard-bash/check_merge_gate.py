#!/usr/bin/env python3
import datetime
import importlib.util
import itertools
import os
import stat
import subprocess
import sys
import tempfile

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
GUARD_BASH = os.path.join(ROOT, "hooks", "guard-bash.py")


def load_merge_block_reason():
    spec = importlib.util.spec_from_file_location("guard_bash_under_test", GUARD_BASH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.merge_block_reason


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


def fail_closed_verdict(files, created, checks_signal):
    if files == "empty":
        return "deny"
    if checks_signal == "no_checks":
        return "allow" if created == "present_old" else "deny"
    if checks_signal == "pass":
        return "allow"
    return "deny"


KNOWN_GAPS = {
    ("nonempty", "absent", "no_checks", False): "createdAt 이 없으면 나이를 모르는데도 허용한다",
    ("absent", "absent", "no_checks", False): "createdAt 이 없으면 나이를 모르는데도 허용한다",
    ("exception",): "gh 호출 자체가 실패하면 아무것도 확인 못 한 채로 허용한다",
}


def run_once(merge_block_reason, files, created, checks_signal, exc):
    with tempfile.TemporaryDirectory() as t:
        if not exc:
            stdout, rc = CHECKS_SIGNALS[checks_signal]
            write_fake_gh(t, pr_json(files, created), stdout, rc)
            env_path = t + os.pathsep + os.environ["PATH"]
        else:
            env_path = t
        old_path = os.environ.get("PATH")
        os.environ["PATH"] = env_path
        try:
            reason = merge_block_reason("1", t)
        finally:
            if old_path is not None:
                os.environ["PATH"] = old_path
    return "deny" if reason else "allow"


def main():
    merge_block_reason = load_merge_block_reason()
    findings = []
    new_mismatches = []

    actual = run_once(merge_block_reason, "nonempty", "present_old", "pass", True)
    key = ("exception",)
    if actual != "deny":
        msg = f"gh 자체가 없는 PATH -> {actual} (기대 deny): {KNOWN_GAPS[key]}"
        if key in KNOWN_GAPS:
            findings.append(msg)
        else:
            new_mismatches.append(msg)

    for files, created, checks_signal in itertools.product(("empty", "nonempty", "absent"), ("present_new", "present_old", "absent"), CHECKS_SIGNALS):
        exp = fail_closed_verdict(files, created, checks_signal)
        actual = run_once(merge_block_reason, files, created, checks_signal, False)
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
