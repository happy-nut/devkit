#!/usr/bin/env python3
"""슬라이드 HTML 폴더와 자막으로 무음 가로 mp4 를 만들고, 만든 파일의 프레임으로 머문 시간을 잰다.

쓰는 법: render.py <슬라이드 폴더> <출력.mp4> [--fade 초] [--margin 초]

슬라이드 폴더: 01.html, 02.html ... (이름 순서가 슬라이드 순서) 와 subtitles.txt (한 줄에 슬라이드 하나).
슬라이드 HTML 은 1280x620 화면을 가득 채우게 그린다. 아래 100px 는 자막 띠다.
머문 시간 = 슬라이드가 더하는 어절 수 / 3 초 + margin. 렌더 뒤 프레임 대조로 다시 재서 모자라면 종료 코드 1.
확인용 프레임(슬라이드마다 한 장, 휴대폰 화면 폭)은 <출력>-check/ 에 남는다.
필요한 것: ffmpeg, ffprobe, Chrome(또는 CHROME 환경 변수에 Chromium 계열 실행 파일).
"""
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


class TextOnly(html.parser.HTMLParser):
    """화면에 보이는 글만 모은다. 그림(img) 속 글자는 세지 않는다."""
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


def words(text):
    # 한국어는 띄어쓰기 단위 어절 하나를 한 낱말로 센다.
    return text.split()


def slide_words(path):
    p = TextOnly()
    p.feed(path.read_text())
    return words(' '.join(p.parts))


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def shoot(chrome, page, png):
    run([chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1',
         f'--window-size={W},{H}', f'--screenshot={png}', page.as_uri()],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not png.exists():
        sys.exit(f'스크린샷 실패: {page}')


def gray(src, extra=()):
    """이미지나 영상을 CMP_W x CMP_H 회색 프레임 목록으로."""
    out = run(['ffmpeg', '-v', 'error', *extra, '-i', str(src), '-vf', f'scale={CMP_W}:{CMP_H},format=gray',
               '-f', 'rawvideo', '-'], stdout=subprocess.PIPE).stdout
    n = CMP_W * CMP_H
    return [out[i:i + n] for i in range(0, len(out), n)]


def dist(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


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

    # 슬라이드가 더하는 낱말: 자막 전부 + 앞 슬라이드에 없던 낱말(바뀐 라벨 포함). 첫 슬라이드는 전부.
    added, prev = [], collections.Counter()
    for page, sub in zip(pages, subs):
        cur = collections.Counter(slide_words(page))
        added.append(sum((cur - prev).values()) + len(words(sub)))
        prev = cur
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

    # 클립 i 길이 = 머문 시간 + 들어오는 페이드 + 나가는 페이드. xfade 로 이어 붙인다.
    n, f = len(pngs), a.fade
    lens = [h + f * (i > 0) + f * (i < n - 1) for i, h in enumerate(holds)]
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

    # 재기: 만든 파일의 프레임을 슬라이드 그림과 대조한다. 정지 프레임 감지기는 페이드의 흐린 끝을
    # 정지로 세므로 쓰지 않는다. 순수 프레임 오차(압축 잡음, 0.01 안팎) 위로 페이드 한 프레임 걸음의 1/5 까지만
    # 머문 것으로 센다. 바로 옆 슬라이드와 라벨 하나만 달라도 페이드 첫 프레임이 걸러진다.
    refs = [gray(p)[0] for p in pngs]
    frames = gray(a.out)
    best = []
    for fr in frames:
        ds = [dist(fr, r) for r in refs]
        k = min(range(n), key=ds.__getitem__)
        best.append((k, ds[k]))
    floor = [min((d for k, d in best if k == i), default=99) for i in range(n)]
    steps = max(1.0, f * FPS)
    tol = [max(0.01, 0.2 * min((dist(refs[i], refs[j]) for j in range(n) if j != i), default=1) / steps)
           for i in range(n)]
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
