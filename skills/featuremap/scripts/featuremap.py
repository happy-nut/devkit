#!/usr/bin/env python3
import argparse, datetime, html, json, os, re, subprocess, sys, tempfile

RUNNABLE = re.compile(r"\b(node|npm|npx|pnpm|yarn|bun|deno|python3?|pytest|bash|sh|go test|cargo|swift|xcodebuild|make)\b|\./|\.(mjs|js|ts|sh|py)\b")
GAP_HEADINGS = re.compile(r"^##\s+(Not mapped|지도에 없|아직 지도)", re.I)
SECTION = re.compile(r"^##\s+(.+?)\s*$", re.M)
SKIP = re.compile(r"(^|/)(node_modules|dist|build|vendor|\.git)/")
HANGUL = re.compile(r"[가-힣]")
FEATURE_ID = re.compile(r"^([A-Z][A-Z0-9_-]*)\s+[\u2014\u2013-]+\s+(.+)$")


def split_sections(text):
    parts = SECTION.split(text)
    head = parts[0]
    return head, {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def find_section(sections, *prefixes):
    for name, body in sections.items():
        if name.lower().startswith(prefixes):
            return name, body
    return None, ""


def bullets(body):
    out, cur = [], None
    for line in body.splitlines():
        if re.match(r"^[-*] ", line):
            cur = line[2:].strip()
            out.append(cur)
        elif cur is not None and line.startswith("  ") and line.strip():
            out[-1] += " " + line.strip()
        elif not line.strip():
            cur = None
    return out


def token(text):
    m = re.match(r"`([^`]+)`|\*\*([^*]+)\*\*", text)
    return (m.group(1) or m.group(2)).strip() if m else None


def inline(text):
    t = html.escape(text, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*([^*\s][^*]*)\*(?!\w)", r"<em>\1</em>", t)
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', t)


def markdown(text):
    out, para, items, fence = [], [], [], None
    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()
        if items:
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>")
            items.clear()
    for line in text.splitlines():
        if fence is not None:
            if line.strip().startswith("```"):
                out.append("<pre><code>" + html.escape("\n".join(fence)) + "</code></pre>")
                fence = None
            else:
                fence.append(line)
            continue
        if line.strip().startswith("```"):
            flush()
            fence = []
        elif re.match(r"^\s*[-*] ", line):
            if para:
                flush()
            items.append(re.sub(r"^\s*[-*] ", "", line))
        elif items and line.startswith("  ") and line.strip():
            items[-1] += " " + line.strip()
        elif re.match(r"^#{1,6} ", line):
            flush()
            out.append("<h4>" + inline(line.lstrip("#").strip()) + "</h4>")
        elif line.strip().startswith("|"):
            flush()
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                out.append("<div class='row'>" + "".join(f"<span>{inline(c)}</span>" for c in cells) + "</div>")
        elif not line.strip():
            flush()
        else:
            if items:
                flush()
            para.append(line.strip())
    flush()
    return "\n".join(out)


def repo_files(repo, features_dir, ignore=()):
    r = subprocess.run(["git", "-C", repo, "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True)
    paths = r.stdout.splitlines() if r.returncode == 0 else [
        os.path.relpath(os.path.join(d, f), repo) for d, _, fs in os.walk(repo) for f in fs]
    feat = os.path.relpath(os.path.realpath(features_dir), os.path.realpath(repo))
    for p in paths:
        full = os.path.join(repo, p)
        if SKIP.search(p) or p.startswith(feat + os.sep) or os.path.realpath(full) in ignore or not os.path.isfile(full) or os.path.getsize(full) > 1_000_000:
            continue
        try:
            yield p, open(full, encoding="utf-8").read().splitlines()
        except (UnicodeDecodeError, OSError):
            continue


def proofs_for(ids, files):
    found = {i: [] for i in ids}
    if not ids:
        return found
    pat = re.compile(r"(?<![\w-])(" + "|".join(sorted(map(re.escape, ids), key=len, reverse=True)) + r")(?![\w-])")
    for path, lines in files:
        prose = path.lower().endswith((".md", ".txt"))
        for n, line in enumerate(lines, 1):
            for m in pat.finditer(line):
                if not prose or RUNNABLE.search(line):
                    found[m.group(1)].append({"path": path, "line": n, "text": line.strip()[:160]})
    return found


def read_map(features_dir, repo, ignore=()):
    readme = os.path.join(features_dir, "README.md")
    index_text = open(readme, encoding="utf-8").read() if os.path.exists(readme) else ""
    _, index_sections = split_sections(index_text)
    gaps = [inline(b) for name, body in index_sections.items() if GAP_HEADINGS.match("## " + name) for b in bullets(body)]
    title = re.search(r"^# (.+)$", index_text, re.M)
    features = []
    for name in sorted(os.listdir(features_dir)):
        if not name.endswith(".md") or name == "README.md":
            continue
        text = open(os.path.join(features_dir, name), encoding="utf-8").read()
        head, sections = split_sections(text)
        h1 = re.search(r"^# (.+)$", head, re.M)
        purpose = re.sub(r"^# .+$", "", head, flags=re.M).strip()
        _, subs_body = find_section(sections, "sub-features", "하위 기능")
        drive_name, drive_body = find_section(sections, "driving", "몰기")
        _, how_body = find_section(sections, "how to get", "가는 길", "닿는 길", "진입")
        subs = []
        for b in bullets(subs_body):
            sid = token(b)
            if sid:
                named = MAP_NAME.match(b)
                subs.append({"id": sid, "name": default_name(b, sid), "map_name": re.sub(r"`", "", named.group(1)).strip() if named else "",
                             "map_desc": plain(named.group(2)) if named else "", "html": inline(b), "method": re.search(r"(?<![\w-])" + re.escape(sid) + r"(?![\w-])", drive_body) is not None})
        title_text = h1.group(1).strip() if h1 else name[:-3]
        fid = FEATURE_ID.match(title_text)
        own_id = fid.group(1) if fid else name if any(x["id"] == name[:-3] for x in subs) else name[:-3]
        fname = (fid.group(2) if fid else title_text).strip()
        features.append({"key": name[:-3], "id": own_id, "name": fname, "map_name": fname, "map_desc": plain(re.split(r"(?<=[.。])\s", purpose.strip())[0]) if purpose.strip() else "", "file": name, "title": title_text,
                         "purpose": markdown(purpose), "subs": subs, "claim": subs_body + "\n" + how_body,
                         "sections": [{"name": k, "html": markdown(v)} for k, v in sections.items()]})
    files = list(repo_files(repo, features_dir, ignore))
    proofs = proofs_for([s["id"] for f in features for s in f["subs"]], files)
    for f in features:
        for s in f["subs"]:
            s["proofs"] = proofs[s["id"]][:8]
            s["status"] = "auto" if s["proofs"] else "method" if s["method"] else "none"
    return {"title": title.group(1).strip() if title else os.path.basename(repo), "features": features, "gaps": gaps}


MAP_NAME = re.compile(r"^`[^`]+`\s*\*\*(.+?)\*\*\s*[\u2014\u2013:-]?\s*(.*)$", re.S)


def plain(text):
    return re.sub(r"\s+", " ", re.sub(r"[`*]", "", text or "")).strip()


def default_name(bullet, sid):
    rest = re.sub(r"^`[^`]+`|^\*\*[^*]+\*\*", "", bullet).strip()
    bold = re.match(r"\*\*(.+?)\*\*", rest)
    name = bold.group(1) if bold else re.split(r"\s+[\u2014\u2013]\s+|[.。]", rest)[0]
    return re.sub(r"[`*]", "", name).strip()[:60] or sid


def verified_by(repo, ref):
    path, _, symbol = ref.partition("::")
    full = os.path.join(repo, path)
    if not os.path.isfile(full):
        return None
    lines = open(full, encoding="utf-8", errors="replace").read().splitlines()
    needle = symbol.split("::")[-1]
    hit = next((n for n, line in enumerate(lines, 1) if needle in line), None) if needle else 1
    return hit and {"path": path, "line": hit, "text": (lines[hit - 1].strip() if lines else "")[:160], "named": True}


def apply_names(data, names, repo="."):
    problems = []
    for f in data["features"]:
        for item in [f] + f["subs"]:
            given = names.get(item["id"]) or (names.get(f["key"]) if item is f else None) or {}
            item["name"] = item["map_name"] or given.get("name") or item["name"]
            item["desc"] = item["map_desc"] if HANGUL.search(item["map_desc"]) else given.get("desc", "")
            if not item["map_name"]:
                problems.append(f"영어 이름이 지도에 없음 {item['id']}")
            if not HANGUL.search(item["map_desc"]):
                problems.append(f"한국어 설명이 지도에 없음 {item['id']}")
            for ref in given.get("verified_by", []) if item is not f else []:
                proof = verified_by(repo, ref)
                if proof:
                    item["proofs"].append(proof)
                    item["status"] = "auto"
                else:
                    problems.append(f"근거를 못 찾음 {item['id']}: {ref}")
            if HANGUL.search(item["name"]):
                problems.append(f"이름에 한글 {item['id']}: {item['name']}")
    for f in data["features"]:
        for item in [f] + f["subs"]:
            del item["map_name"], item["map_desc"]
    return problems


def mentions(text, needle):
    if re.fullmatch(r"[A-Za-z0-9]{1,2}", needle or ""):
        return f"`{needle}`" in text
    return bool(needle) and re.search(r"(?<![\w⌘⌥⇧⌃])" + re.escape(needle) + r"(?!\w)", text) is not None


def match_surfaces(surfaces, features):
    by = {k: f for f in features for k in (f["key"], f["id"])}
    for s in surfaces:
        s["claimed_in"] = [f["key"] for f in features if any(mentions(f["claim"], t) for t in s.get("match") or [s.get("label", "")])]
        owner = by.get(s.get("owner"))
        s["owner_key"] = owner["key"] if owner else None
        s["mapped_in"] = [owner["key"]] if owner and owner["key"] in s["claimed_in"] else []
    return surfaces


def mece_problems(data):
    out, seen = [], {}
    for f in data["features"]:
        for sub in f["subs"]:
            seen.setdefault(sub["id"], []).append(f["key"])
    out += [f"하위 기능 ID 겹침 {i}: {', '.join(ks)}" for i, ks in seen.items() if len(ks) > 1]
    for s in data["surfaces"]:
        name = s.get("label") or s.get("id")
        others = [k for k in s["claimed_in"] if k != s["owner_key"]] if s["owner_key"] else []
        if "exclude" in s:
            if not str(s["exclude"]).strip():
                out.append(f"제외 이유 없음 {name}")
            if s["claimed_in"]:
                out.append(f"제외했는데 기능 파일에 적힘 {name}: {', '.join(s['claimed_in'])}")
            continue
        if not s.get("owner"):
            out.append(f"주인 안 정함 {name} (후보: {', '.join(s['claimed_in']) or '없음'})")
        elif not s["owner_key"]:
            out.append(f"주인 기능 파일 없음 {name} → {s['owner']}")
        elif s["owner_key"] not in s["claimed_in"]:
            out.append(f"주인 기능 파일에 안 적힘 {name} → {s['owner_key']}")
        if others:
            out.append(f"겹침 {name}: 주인 아닌 {', '.join(others)} 에도 적힘")
    return out


def summary(data):
    subs = [s for f in data["features"] for s in f["subs"]]
    count = {k: sum(s["status"] == k for s in subs) for k in ("auto", "method", "none")}
    surf = data["surfaces"]
    excluded = sum("exclude" in s for s in surf)
    return {"features": len(data["features"]), "subs": len(subs), **count,
            "surfaces": len(surf), "mapped": sum(bool(s["mapped_in"]) for s in surf), "excluded": excluded,
            "unowned": sum(not s["mapped_in"] and "exclude" not in s for s in surf), "gaps": len(data["gaps"]),
            "naming_problems": len(data["problems"]), "mece_problems": len(data["mece"]), "mece": not data["mece"]}


def build(features_dir, repo, surfaces_path=None, names_path=None):
    data = read_map(features_dir, repo, {os.path.realpath(p) for p in (surfaces_path, names_path) if p})
    data["problems"] = apply_names(data, json.load(open(names_path, encoding="utf-8")) if names_path else {}, repo)
    surfaces = json.load(open(surfaces_path, encoding="utf-8")) if surfaces_path else []
    data["surfaces"] = match_surfaces(surfaces, data["features"])
    data["mece"] = mece_problems(data)
    for f in data["features"]:
        del f["claim"]
    data["summary"] = summary(data)
    data["generated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    data["repo"] = os.path.basename(os.path.realpath(repo))
    return data


def render(data):
    template = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.html"), encoding="utf-8").read()
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return template.replace("__TITLE__", html.escape(data["title"])).replace("__DATA__", payload)


def self_test():
    here = os.path.dirname(os.path.abspath(__file__))
    example = os.path.join(here, "..", "..", "verify-setup", "references", "feature-map-example")
    with tempfile.TemporaryDirectory() as t:
        feat = os.path.join(t, "features")
        os.makedirs(feat)
        for n in os.listdir(example):
            open(os.path.join(feat, n), "w").write(open(os.path.join(example, n), encoding="utf-8").read())
        driven = open(os.path.join(feat, "create-note.md")).read().replace("- **저장.**", "- `create-save` **저장.**").replace("`create-save` **save**", "`create-save` **저장**").replace("`create-cli` **create from CLI**: 터미널에서 같은 모양의 노트를 만든다.", "`create-cli` 는 터미널에서 만든다.")
        open(os.path.join(feat, "create-note.md"), "w").write(driven)
        with open(os.path.join(feat, "README.md"), "a") as f:
            f.write("\n## Not mapped yet\n\n- 내보내기 메뉴,\n  설정 화면\n- 휴지통\n")
        open(os.path.join(t, "drive.sh"), "w").write("node drive.mjs create-open\n")
        open(os.path.join(feat, "inbox.md"), "w").write("# Inbox\n\n## Sub-features\n\n- `inbox` 받은 편지함 목록.\n")
        surf = os.path.join(t, "surfaces.json")
        json.dump([{"id": "new", "label": "새 노트", "match": ["New note"], "owner": "create-note"}, {"id": "export", "label": "내보내기", "match": ["Export all"]},
                   {"id": "disc", "label": "앞부분만 겹침", "match": ["Disc"], "owner": "create-note"}, {"id": "to", "label": "짧은 키", "match": ["to"], "exclude": "영역 이름"},
                   {"id": "slash", "label": "검색 키", "match": ["/"], "owner": "search"}, {"id": "ghost", "label": "없는 화면", "match": ["Ghost"], "owner": "ghost"},
                   {"id": "searchbtn", "label": "검색 단추", "match": ["Search"]}], open(surf, "w"))
        sp = os.path.join(feat, "search.md")
        body = open(sp).read()
        open(sp, "w").write(body.replace("## How to get to it (user POV)\n", "## How to get to it (user POV)\n\n- 도구 막대에는 `New note` 와 `Search` 단추가 나란히 있다.\n"))
        names = os.path.join(t, "names.json")
        json.dump({"create-cli": {"name": "cli", "desc": "터미널에서 만든다."},
                   "create-cancel": { "verified_by": ["tests/test_notes.py::test_cancel_keeps_nothing", "tests/missing.py::test_x"]}}, open(names, "w"), ensure_ascii=False)
        os.makedirs(os.path.join(t, "tests"))
        open(os.path.join(t, "tests", "test_notes.py"), "w").write("def test_cancel_keeps_nothing():\n    pass\n")
        data = build(feat, t, surf, names)
        named = {s["id"]: s for f in data["features"] for s in [f] + f["subs"]}
        assert named["create-open"]["name"] == "open editor" and named["create-open"]["desc"].startswith("브라우저 진입점마다"), "영어 이름(굵게)과 한국어 설명은 지도 글머리에서 읽는다"
        assert named["create-note"]["name"] == "Create a note" and named["create-note"]["desc"].startswith("사용자는"), "기능 이름은 H1, 설명은 첫 문장"
        assert "이름에 한글 create-save: 저장" in data["problems"], "이름에 한글이 있으면 잡는다"
        assert "영어 이름이 지도에 없음 create-cli" in data["problems"] and named["create-cli"]["name"] == "cli", "이름 파일에만 있는 이름은 쓰되 지도에 없다고 잡는다(유비쿼터스 언어는 지도에 산다)"
        assert not any(x.endswith("create-open") for x in data["problems"]), "지도에 이름·설명이 다 있으면 문제가 없다"
        status = {s["id"]: s["status"] for f in data["features"] for s in f["subs"]}
        assert status["create-open"] == "auto", "실행 파일이 ID 를 가리키면 자동 검증"
        assert status["create-save"] == "method", "Driving 글머리에 ID 가 있으면 방법만"
        assert status["create-cancel"] == "auto", "이름 파일의 verified_by 가 짚은 시험이 실제로 있으면 자동 검증(ID 를 안 담는 백엔드·라이브러리 시험)"
        assert "근거를 못 찾음 create-cancel: tests/missing.py::test_x" in data["problems"], "짚은 시험 파일이 없으면 잡는다"
        named_proof = next(s for f in data["features"] for s in f["subs"] if s["id"] == "create-cancel")["proofs"][0]
        assert named_proof["path"] == "tests/test_notes.py" and named_proof["line"] == 1, "근거는 그 시험이 정의된 줄"
        assert [s["mapped_in"] for s in data["surfaces"]] == [["create-note"], [], [], [], ["search"], [], []], str([s["mapped_in"] for s in data["surfaces"]]) + " 진입점은 주인 기능의 Sub-features·How to get 절에 낱말째 있어야 그 주인에 든다(Disc 는 Discard 에 걸리지 않는다)"
        m = data["mece"]
        assert "주인 안 정함 내보내기 (후보: 없음)" in m, "주인 없는 진입점은 빠짐(CE)으로 잡는다"
        assert "겹침 새 노트: 주인 아닌 search 에도 적힘" in m, "주인 아닌 기능 파일에도 적히면 겹침(ME)으로 잡는다(탭 이름을 나열만 한 줄)"
        assert "주인 기능 파일에 안 적힘 앞부분만 겹침 → create-note" in m, "주인 파일이 그 진입점을 적지 않으면 잡는다"
        assert "주인 기능 파일 없음 없는 화면 → ghost" in m, "주인 기능 파일이 없으면 잡는다(새 기능 파일을 만들 곳)"
        assert "주인 안 정함 검색 단추 (후보: search)" in m and not any(x.startswith("겹침 검색 단추") for x in m), "주인을 안 정한 진입점은 빠짐 하나로만 센다(겹침으로 두 번 세지 않는다)"
        assert not any("짧은 키" in x for x in m) and data["summary"]["excluded"] == 1, "이유를 단 제외는 문제가 아니다"
        assert data["summary"]["mece"] is False and data["summary"]["unowned"] == 4, "MECE 가 아니면 summary 가 그렇게 말한다"
        assert data["gaps"] == ["내보내기 메뉴, 설정 화면", "휴지통"], "빈칸 글머리는 이어지는 줄까지 하나로 읽는다"
        assert next(f["id"] for f in data["features"] if f["key"] == "inbox") == "inbox.md", "파일 이름 ID 가 하위 기능 ID 와 겹치면 기능 ID 는 파일 이름(.md 포함)이다"
        page = render(data)
        assert "create-cancel" in page and "__DATA__" not in page, "HTML 에 데이터가 들어간다"
    kit = os.path.join(here, "..", "..")
    with tempfile.TemporaryDirectory() as t:
        blocks = re.findall(r"```markdown\n(# .+?)```", open(os.path.join(kit, "repro-fix", "references", "feature-map.md"), encoding="utf-8").read(), re.S)
        for i, b in enumerate(blocks):
            open(os.path.join(t, f"ex{i}.md"), "w").write(b)
        for folder in (example, t):
            data = read_map(folder, folder)
            assert data["features"] and not apply_names(data, {}), f"키트의 기능 지도 예시({folder})는 영어 이름과 한국어 설명을 지도에 담는다: {apply_names(read_map(folder, folder), {})}"
    vague = re.compile(r"지도에 (든|듦|들었|있는 진입점|없는 진입점)|지도 밖|mapped yet 이 아닌")
    for f in ("template.html", os.path.join("..", "SKILL.md")):
        text = open(os.path.join(here, f), encoding="utf-8").read()
        hit = vague.search(text.replace("「지도에 든」", ""))
        assert not hit, f"{f} 에 애매한 낱말 「{hit and hit.group(0)}」. 낱말 표의 말(주인 있음·주인 없음·제외·README 빈칸)을 쓴다"
    print("featuremap self-test OK")
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="기능 지도를 커버리지가 붙은 인터랙티브 HTML 로 만든다")
    ap.add_argument("features", nargs="?", help="기능 지도 폴더 (보통 .claude/skills/verify-<앱>/features)")
    ap.add_argument("--repo", default=".", help="저장소 루트")
    ap.add_argument("--surfaces", help="코드에서 뽑은 사용자 진입점 JSON")
    ap.add_argument("--names", help="기능·하위 기능 ID 마다 영어 이름(name)과 한국어 설명(desc)을 준 JSON")
    ap.add_argument("--out", help="쓸 HTML 경로")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if not a.features:
        ap.error("기능 지도 폴더를 준다")
    data = build(a.features, a.repo, a.surfaces, a.names)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(render(data))
    s = data["summary"]
    print(json.dumps(s, ensure_ascii=False))
    for line in data["problems"] + data["mece"]:
        print(line)
    for f in data["features"]:
        for sub in f["subs"]:
            if sub["status"] == "none":
                print(f"방법 없음 {f['key']} {sub['id']}")
    for sf in data["surfaces"]:
        if not sf["mapped_in"]:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
