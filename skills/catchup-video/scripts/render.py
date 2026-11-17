#!/usr/bin/env python3
import argparse, collections, html, html.parser, os, pathlib, shutil, subprocess, sys, tempfile

W, H, STRIP = 1280, 720, 100
FPS = 30
CMP_W, CMP_H = 160, 90

CHROME_CANDIDATES = [
    os.environ.get('CHROME', ''),
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    shutil.which('google-chrome') or '', shutil.which('chromium') or '',
]


class VisibleTextParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'title', 'head'):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'title', 'head') and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def eojeols(text):
    return text.split()


def slide_words(path):
    p = VisibleTextParser()
    p.feed(path.read_text())
    return eojeols(' '.join(p.parts))


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def shoot(chrome, page, png):
    run([chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1',
         f'--window-size={W},{H}', f'--screenshot={png}', page.as_uri()],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not png.exists():
        sys.exit(f'스크린샷 실패: {page}')


def gray_frames(src, extra=()):
    out = run(['ffmpeg', '-v', 'error', *extra, '-i', str(src), '-vf', f'scale={CMP_W}:{CMP_H},format=gray',
               '-f', 'rawvideo', '-'], stdout=subprocess.PIPE).stdout
    n = CMP_W * CMP_H
    return [out[i:i + n] for i in range(0, len(out), n)]


def dist(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def added_word_counts(pages, subs):
    added, prev = [], collections.Counter()
    for page, sub in zip(pages, subs):
        cur = collections.Counter(slide_words(page))
        added.append(sum((cur - prev).values()) + len(eojeols(sub)))
        prev = cur
    return added


def clip_lengths(holds, fade):
    n = len(holds)
    return [h + fade * (i > 0) + fade * (i < n - 1) for i, h in enumerate(holds)]


def hold_tolerance(refs, fade):
    steps = max(1.0, fade * FPS)
    n = len(refs)
    return [max(0.01, 0.2 * min((dist(refs[i], refs[j]) for j in range(n) if j != i), default=1) / steps)
            for i in range(n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('slides', type=pathlib.Path)
    ap.add_argument('out', type=pathlib.Path)
    ap.add_argument('--fade', type=float, default=0.6)
    ap.add_argument('--margin', type=float, default=0.5)
    a = ap.parse_args()

    pages = sorted(a.slides.glob('*.html'))
    subs = [l.strip() for l in (a.slides / 'subtitles.txt').read_text().splitlines() if l.strip()]
    if not pages or len(pages) != len(subs):
        sys.exit(f'슬라이드 {len(pages)}장, 자막 {len(subs)}줄: 수가 같아야 한다')
    if len(pages) > 10:
        sys.exit('슬라이드는 10장까지')
    chrome = next((c for c in CHROME_CANDIDATES if c and os.path.exists(c)), None)
    if not chrome:
        sys.exit('Chrome 을 못 찾았다. CHROME 환경 변수에 경로를 준다')

    added = added_word_counts(pages, subs)
    need = [n / 3 for n in added]
    holds = [max(1.0, x) + a.margin for x in need]

    tmp = pathlib.Path(tempfile.mkdtemp(prefix='catchup-video-'))
    pngs = []
    for i, (page, sub) in enumerate(zip(pages, subs)):
        frame = tmp / f'frame{i:02d}.html'
        frame.write_text(f'''<!doctype html><meta charset="utf-8"><style>
html,body{{margin:0;width:{W}px;height:{H}px;overflow:hidden;background:#fff}}
iframe{{display:block;border:0;width:{W}px;height:{H - STRIP}px}}
.sub{{height:{STRIP}px;display:flex;align-items:center;justify-content:center;background:#111;color:#fff;
font:600 34px/1.2 "Apple SD Gothic Neo","Noto Sans KR",sans-serif;padding:0 40px;box-sizing:border-box;text-align:center}}
</style><iframe src="{page.resolve().as_uri()}" scrolling="no"></iframe><div class="sub">{html.escape(sub)}</div>''')
        png = tmp / f'frame{i:02d}.png'
        shoot(chrome, frame, png)
        pngs.append(png)

    n, f = len(pngs), a.fade
    lens = clip_lengths(holds, f)
    cmd = ['ffmpeg', '-v', 'error', '-y']
    for png, L in zip(pngs, lens):
        cmd += ['-loop', '1', '-framerate', str(FPS), '-t', f'{L:.3f}', '-i', str(png)]
    chain, last, t = [], '[0:v]', 0.0
    for i in range(1, n):
        t += lens[i - 1] - f
        chain.append(f'{last}[{i}:v]xfade=transition=fade:duration={f}:offset={t:.3f}[v{i}]')
        last = f'[v{i}]'
    chain.append(f'{last}format=yuv420p[out]')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    run(cmd + ['-filter_complex', ';'.join(chain), '-map', '[out]', '-an', '-c:v', 'libx264', '-crf', '12', '-tune', 'stillimage',
               '-r', str(FPS), '-movflags', '+faststart', str(a.out)])

    refs = [gray_frames(p)[0] for p in pngs]
    frames = gray_frames(a.out)
    best = []
    for fr in frames:
        ds = [dist(fr, r) for r in refs]
        k = min(range(n), key=ds.__getitem__)
        best.append((k, ds[k]))
    floor = [min((d for k, d in best if k == i), default=99) for i in range(n)]
    tol = hold_tolerance(refs, f)
    held = [sum(1 for k, d in best if k == i and d <= floor[i] + tol[i]) / FPS for i in range(n)]

    check = a.out.with_name(a.out.stem + '-check')
    check.mkdir(exist_ok=True)
    ok = True
    print('슬라이드  더한낱말  필요(초)  잰머문(초)  판정  자막')
    for i in range(n):
        idx = [j for j, (k, d) in enumerate(best) if k == i and d <= floor[i] + tol[i]]
        mid = idx[len(idx) // 2] if idx else 0
        run(['ffmpeg', '-v', 'error', '-y', '-i', str(a.out), '-vf', f'select=eq(n\\,{mid}),scale=400:-2',
             '-frames:v', '1', str(check / f'{i + 1:02d}.png')])
        good = held[i] >= max(1.0, need[i])
        ok &= good
        print(f'{i + 1:>6}  {added[i]:>8}  {need[i]:>8.1f}  {held[i]:>10.2f}  {"통과" if good else "모자람"}  {subs[i]}')
    print(f'영상: {a.out}  확인 프레임: {check}/')
    shutil.rmtree(tmp)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
