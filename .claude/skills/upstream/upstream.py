import fnmatch, json, os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BASE_IN_README = re.compile(r"\]\(https://github\.com/([\w.-]+/[\w.-]+)/tree/main/([\w./-]+)\)\(커밋 ([0-9a-f]{7,40})\)")
TABLE_HEADING = "## 이름 대응"
NOT_PORTED = "(옮기지 않음)"


def read_base(readme):
    m = BASE_IN_README.search(readme)
    if not m:
        sys.exit("README.md 에서 「[...](https://github.com/<저장소>/tree/main/<폴더>)(커밋 <sha>)」 줄을 못 찾았다")
    return {"repo": m.group(1), "dir": m.group(2).rstrip("/"), "base": m.group(3)}


def expand(name):
    m = re.match(r"^([\w]+)/([\w]+)(-.+)$", name)
    return [m.group(1) + m.group(3), m.group(2) + m.group(3)] if m else [name]


def read_table(authoring):
    body = authoring.split(TABLE_HEADING, 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in body.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set("-: ") or cells[0] in ("pstack", "원본"):
            continue
        names = [x for n in re.split(r"[+,]", cells[0]) for x in expand(re.sub(r"\(.*?\)|\s.*$", "", n.strip()))]
        target = re.search(r"`([^`]+)`", cells[1])
        rows.append({"names": [n for n in names if n], "kit": target.group(1) if target else None,
                     "skipped": NOT_PORTED in cells[1], "note": cells[2] if len(cells) > 2 else ""})
    return rows


def row_for(name, table):
    return next((r for r in table if any(fnmatch.fnmatch(name, n) for n in r["names"])), None)


def kit_target(kit):
    if "/" in kit:
        return kit
    return f"skills/{kit}" if os.path.isdir(os.path.join(ROOT, "skills", kit)) or not os.path.exists(os.path.join(ROOT, "agents", kit + ".md")) else f"agents/{kit}.md"


def map_path(path, upstream_dir, table, exists=lambda p: os.path.exists(os.path.join(ROOT, p))):
    rel = path[len(upstream_dir) + 1:] if path.startswith(upstream_dir + "/") else None
    if rel is None:
        return None
    parts = rel.split("/")
    name = parts[1].removesuffix(".md") if len(parts) > 1 and parts[0] in ("skills", "agents", "automations") else None
    if name is None:
        return {"kind": "기타", "target": rel}
    row = row_for(name, table)
    if row is None:
        return {"kind": "대응표에 없음", "target": name}
    if row["skipped"]:
        return {"kind": "옮기지 않기로 함", "target": name}
    if parts[0] == "skills" and len(parts) > 3 and parts[2] == "playbooks":
        mirror = f"skills/{row['kit']}/playbooks/{parts[3]}"
        return {"kind": "대응", "target": mirror if exists(mirror) else f"skills/{row['kit']}/playbooks/ (없는 플레이북 {parts[3]})"}
    return {"kind": "대응", "target": kit_target(row["kit"])}


def gh(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"gh api {path} 실패: {r.stderr.strip()}")
    return json.loads(r.stdout)


def report(src, table):
    cmp = gh(f"repos/{src['repo']}/compare/{src['base']}...main")
    detail = {c["sha"]: gh(f"repos/{src['repo']}/commits/{c['sha']}") for c in cmp["commits"] if len(c["parents"]) == 1}
    commits = [c for c in cmp["commits"] if c["sha"] in detail and any(f["filename"].startswith(src["dir"] + "/") for f in detail[c["sha"]]["files"])]
    head = cmp["commits"][-1]["sha"][:7] if cmp["commits"] else src["base"]
    print(f"원본 {src['repo']}/{src['dir']} · 기준 {src['base']} → main {head} · 원본 폴더를 건드린 커밋 {len(commits)}개")
    for c in commits:
        files = detail[c["sha"]]["files"]
        print(f"\n{c['sha'][:7]} {c['commit']['author']['date'][:10]} {c['commit']['message'].splitlines()[0]}")
        grouped = {}
        for f in files:
            m = map_path(f["filename"], src["dir"], table)
            if m:
                grouped.setdefault((m["kind"], m["target"]), []).append(f"{f['filename'][len(src['dir']) + 1:]} +{f['additions']} -{f['deletions']}")
        for (kind, target), fs in sorted(grouped.items()):
            if kind == "기타":
                continue
            print(f"  [{kind}] {target}")
            for x in fs:
                print(f"      {x}")
        other = [t for k, t in grouped if k == "기타"]
        if other:
            print(f"  [기타] {', '.join(sorted(other))}")
    listed = gh(f"repos/{src['repo']}/contents/{src['dir']}/skills")
    missing = [s["name"] for s in listed if row_for(s["name"], table) is None]
    print(f"\n대응표에 없는 원본 스킬: {', '.join(missing) if missing else '없음'}")
    if commits:
        print(f"다 처리하면 README 의 기준 커밋을 {head} 로 올린다.")


def self_test():
    readme = "고쳐 썼다. [pstack 원본 저장소](https://github.com/cursor/plugins/tree/main/pstack)(커밋 bf0c7cd)를"
    assert read_base(readme) == {"repo": "cursor/plugins", "dir": "pstack", "base": "bf0c7cd"}, "README 의 원본 링크와 기준 커밋을 읽는다"
    authoring = "\n".join([
        "## 이름 대응 (pstack → devkit)", "", "| pstack | devkit | 비고 |", "|---|---|---|",
        "| poteto-mode | `mode` | 라우터 |",
        "| principle-* 24개 | `skills/mode/principles.md` | 한 파일 |",
        "| interrogate + blast-radius | `review` | |",
        "| figure-it-out, sharpen | `mode` 안의 절 | |",
        "| benny(자동화 팩) | `triage` + `repro-fix` | |",
        "| create/maintain-verification-skill | `verify-setup` | |",
        "| bro | (옮기지 않음) | /dev:write 가 같은 일 |",
        "", "## 다음 절", "| x | `y` | |"])
    table = read_table(authoring)
    assert len(table) == 7, f"다음 절의 표는 읽지 않는다: {table}"
    have = {"skills/mode/playbooks/bug-fix.md"}.__contains__
    cases = {
        "pstack/skills/poteto-mode/SKILL.md": ("대응", "skills/mode"),
        "pstack/skills/poteto-mode/playbooks/bug-fix.md": ("대응", "skills/mode/playbooks/bug-fix.md"),
        "pstack/skills/poteto-mode/playbooks/new-one.md": ("대응", "skills/mode/playbooks/ (없는 플레이북 new-one.md)"),
        "pstack/skills/principle-fix-root-causes/SKILL.md": ("대응", "skills/mode/principles.md"),
        "pstack/skills/blast-radius/SKILL.md": ("대응", "skills/review"),
        "pstack/skills/sharpen/SKILL.md": ("대응", "skills/mode"),
        "pstack/automations/benny/x.md": ("대응", "skills/triage"),
        "pstack/skills/maintain-verification-skill/SKILL.md": ("대응", "skills/verify-setup"),
        "pstack/skills/create-verification-skill/SKILL.md": ("대응", "skills/verify-setup"),
        "pstack/skills/bro/SKILL.md": ("옮기지 않기로 함", "bro"),
        "pstack/skills/brand-new/SKILL.md": ("대응표에 없음", "brand-new"),
        "pstack/docs/guide/01-setup.md": ("기타", "docs/guide/01-setup.md"),
    }
    for path, want in cases.items():
        got = map_path(path, "pstack", table, have)
        assert (got["kind"], got["target"]) == want, f"{path}: {got} != {want}"
    assert map_path("harness/pstack/claude-code/skills/why/SKILL.md", "pstack", table, have) is None, "원본 폴더 밖(다른 하네스 포트)은 세지 않는다"
    real = read_table(open(os.path.join(ROOT, "docs", "authoring.md"), encoding="utf-8").read())
    assert row_for("poteto-mode", real) and row_for("principle-attack-the-premise", real), "저장소의 대응표를 읽을 수 있다"
    read_base(open(os.path.join(ROOT, "README.md"), encoding="utf-8").read())
    print("upstream self-test OK")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        report(read_base(open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()),
               read_table(open(os.path.join(ROOT, "docs", "authoring.md"), encoding="utf-8").read()))
