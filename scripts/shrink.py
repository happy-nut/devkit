import os, re, subprocess, sys

FACT = re.compile(r"`[^`\n]+`|「[^」\n]+」|\d+(?:\.\d+)?")


def facts(text):
    return set(FACT.findall(text))


def lost(old, new):
    return sorted(facts(old) - facts(new))


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout


def report(base):
    shrunk = 0
    for path in git("diff", "--name-only", base, "--", "skills", "agents", "docs", "README.md").split():
        if not path.endswith(".md"):
            continue
        old = git("show", f"{base}:{path}")
        new = open(path).read() if os.path.exists(path) else ""
        gone = lost(old, new)
        if gone:
            shrunk += 1
            print(f"{path}: {len(old.splitlines())} → {len(new.splitlines())}줄, 사라진 것 {len(gone)}개")
            print("  " + " · ".join(gone))
    if not shrunk:
        print(f"{base} 대비 사라진 숫자·코드 이름·인용 낱말 없음")


def self_test():
    old = "3번 실패하면 `opus` 로 올린다. 「사람 확인」 없이 0.5초 기다린다."
    assert lost(old, "`opus` 로 올린다. 0.5초 기다린다.") == ["3", "「사람 확인」"], "빠진 숫자와 인용 낱말을 찾는다"
    assert lost(old, old.replace("올린다", "바꾼다")) == [], "낱말만 바꾼 줄은 세지 않는다"
    assert lost("", "새 줄 1개") == [], "새로 생긴 것은 세지 않는다"
    print("shrink self-test OK")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        report(sys.argv[1] if len(sys.argv) > 1 else "origin/main")
