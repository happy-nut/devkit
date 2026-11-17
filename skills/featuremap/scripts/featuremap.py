#!/usr/bin/env python3
import argparse, datetime, html, json, os, re, subprocess, sys, tempfile

RUNNABLE = re.compile(r"\b(node|npm|npx|pnpm|yarn|bun|deno|python3?|pytest|bash|sh|go test|cargo|swift|xcodebuild|make)\b|\./|\.(mjs|js|ts|sh|py)\b")
GAP_HEADINGS = re.compile(r"^##\s+(Not mapped|지도에 없|아직 지도)", re.I)
SECTION = re.compile(r"^##\s+(.+?)\s*$", re.M)
SKIP = re.compile(r"(^|/)(node_modules|dist|build|vendor|\.git)/")


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


def repo_files(repo, features_dir):
    r = subprocess.run(["git", "-C", repo, "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True)
    paths = r.stdout.splitlines() if r.returncode == 0 else [
        os.path.relpath(os.path.join(d, f), repo) for d, _, fs in os.walk(repo) for f in fs]
    feat = os.path.relpath(os.path.realpath(features_dir), os.path.realpath(repo))
    for p in paths:
        full = os.path.join(repo, p)
        if SKIP.search(p) or p.startswith(feat + os.sep) or not os.path.isfile(full) or os.path.getsize(full) > 1_000_000:
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


def read_map(features_dir, repo):
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
        subs = []
        for b in bullets(subs_body):
            sid = token(b)
            if sid:
                subs.append({"id": sid, "html": inline(b), "method": re.search(r"(?<![\w-])" + re.escape(sid) + r"(?![\w-])", drive_body) is not None})
        features.append({"key": name[:-3], "file": name, "title": h1.group(1).strip() if h1 else name[:-3],
                         "purpose": markdown(purpose), "subs": subs, "text": text,
                         "sections": [{"name": k, "html": markdown(v)} for k, v in sections.items()]})
    files = list(repo_files(repo, features_dir))
    proofs = proofs_for([s["id"] for f in features for s in f["subs"]], files)
    for f in features:
        for s in f["subs"]:
            s["proofs"] = proofs[s["id"]][:8]
            s["status"] = "auto" if s["proofs"] else "method" if s["method"] else "none"
    return {"title": title.group(1).strip() if title else os.path.basename(repo), "features": features, "gaps": gaps}


def mentions(text, needle):
    return bool(needle) and re.search(r"(?<![\w⌘⌥⇧⌃])" + re.escape(needle) + r"(?!\w)", text) is not None


def match_surfaces(surfaces, features):
    for s in surfaces:
        s["mapped_in"] = [f["key"] for f in features if any(mentions(f["text"], t) for t in s.get("match") or [s.get("label", "")])]
    return surfaces


def summary(data):
    subs = [s for f in data["features"] for s in f["subs"]]
    count = {k: sum(s["status"] == k for s in subs) for k in ("auto", "method", "none")}
    surf = data["surfaces"]
    return {"features": len(data["features"]), "subs": len(subs), **count,
            "surfaces": len(surf), "mapped": sum(bool(s["mapped_in"]) for s in surf), "gaps": len(data["gaps"])}


def build(features_dir, repo, surfaces_path=None):
    data = read_map(features_dir, repo)
    surfaces = json.load(open(surfaces_path, encoding="utf-8")) if surfaces_path else []
    data["surfaces"] = match_surfaces(surfaces, data["features"])
    for f in data["features"]:
        del f["text"]
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
        driven = open(os.path.join(feat, "create-note.md")).read().replace("- **저장.**", "- `create-save` **저장.**")
        open(os.path.join(feat, "create-note.md"), "w").write(driven)
        with open(os.path.join(feat, "README.md"), "a") as f:
            f.write("\n## Not mapped yet\n\n- 내보내기 메뉴,\n  설정 화면\n- 휴지통\n")
        open(os.path.join(t, "drive.sh"), "w").write("node drive.mjs create-open\n")
        surf = os.path.join(t, "surfaces.json")
        json.dump([{"id": "new", "label": "새 노트", "match": ["New note"]}, {"id": "export", "label": "내보내기", "match": ["Export all"]}, {"id": "disc", "label": "앞부분만 겹침", "match": ["Disc"]}], open(surf, "w"))
        data = build(feat, t, surf)
        status = {s["id"]: s["status"] for f in data["features"] for s in f["subs"]}
        assert status["create-open"] == "auto", "실행 파일이 ID 를 가리키면 자동 검증"
        assert status["create-save"] == "method", "Driving 글머리에 ID 가 있으면 방법만"
        assert status["create-cancel"] == "none", "어디에도 없으면 없음"
        assert [s["mapped_in"] for s in data["surfaces"]] == [["create-note"], [], []], "진입점은 기능 파일 글에 낱말째 있어야 맞는다(Disc 는 Discard 에 걸리지 않는다)"
        assert data["gaps"] == ["내보내기 메뉴, 설정 화면", "휴지통"], "빈칸 글머리는 이어지는 줄까지 하나로 읽는다"
        page = render(data)
        assert "create-cancel" in page and "__DATA__" not in page, "HTML 에 데이터가 들어간다"
    print("featuremap self-test OK")
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="기능 지도를 커버리지가 붙은 인터랙티브 HTML 로 만든다")
    ap.add_argument("features", nargs="?", help="기능 지도 폴더 (보통 .claude/skills/verify-<앱>/features)")
    ap.add_argument("--repo", default=".", help="저장소 루트")
    ap.add_argument("--surfaces", help="코드에서 뽑은 사용자 진입점 JSON")
    ap.add_argument("--out", help="쓸 HTML 경로")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if not a.features:
        ap.error("기능 지도 폴더를 준다")
    data = build(a.features, a.repo, a.surfaces)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(render(data))
    s = data["summary"]
    print(json.dumps(s, ensure_ascii=False))
    for f in data["features"]:
        for sub in f["subs"]:
            if sub["status"] == "none":
                print(f"방법 없음 {f['key']} {sub['id']}")
    for sf in data["surfaces"]:
        if not sf["mapped_in"]:
            print(f"지도에 없는 진입점 {sf.get('group', '')} {sf.get('label', sf.get('id'))} {sf.get('where', '')}".rstrip())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
