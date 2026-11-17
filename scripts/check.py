"""devkit 저장소 검사. 실행: python3 scripts/check.py

- 모든 스킬·에이전트의 frontmatter
- 본문이 가리키는 플레이북·참고·스크립트 파일, /dev:<스킬>, dev:<에이전트>, principles.md 의 <원칙> 이 실제로 있는지
- 옮기기 전 이름(Cursor·pstack 흔적)과 긴 대시가 남지 않았는지
"""
import glob, json, os, re, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(root)
errors = []

for f in ('.claude-plugin/plugin.json', '.claude-plugin/marketplace.json'):
    json.load(open(f))

def frontmatter(path):
    text = open(path).read()
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    if not m:
        errors.append(f'{path}: frontmatter 없음')
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ':' in line and not line.startswith(' '):
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip()
    return fm, text

skills = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob('skills/*/SKILL.md'))
agents = sorted(os.path.basename(p)[:-3] for p in glob.glob('agents/*.md'))
for name in skills:
    fm, _ = frontmatter(f'skills/{name}/SKILL.md')
    if fm.get('name') != name:
        errors.append(f'skills/{name}: name 이 폴더 이름과 다름')
    if fm.get('disable-model-invocation') != 'true':
        errors.append(f'skills/{name}: disable-model-invocation: true 아님')
    d = fm.get('description', '')
    if not d or len(d) >= 1024:
        errors.append(f'skills/{name}: description 없음 또는 너무 김')
for name in agents:
    fm, _ = frontmatter(f'agents/{name}.md')
    if fm.get('name') != name or not fm.get('description'):
        errors.append(f'agents/{name}: name·description 확인')

principles = set(re.findall(r'^## (.+?)\s*$', open('skills/mode/principles.md').read(), re.M)) if os.path.exists('skills/mode/principles.md') else set()
if not principles:
    errors.append('skills/mode/principles.md: 원칙 절(## 이름)이 없음')

FORBIDDEN = re.compile(r'pstack|poteto|[Cc]ursor|AskQuestion|[Gg]emini|—')
for path in glob.glob('skills/**/*', recursive=True) + glob.glob('agents/*.md'):
    if not os.path.isfile(path) or not path.endswith(('.md', '.sh', '.mjs', '.ts', '.py')):
        continue
    text = open(path).read()
    for i, line in enumerate(text.splitlines(), 1):
        if FORBIDDEN.search(line) and not ('.test.' in path and '\u2014' in line and not re.search(r'pstack|poteto|[Cc]ursor|AskQuestion|[Gg]emini', line)):
            errors.append(f'{path}:{i}: 옮기기 전 흔적 또는 긴 대시: {line.strip()[:80]}')
    if not path.endswith('.md'):
        continue
    skill_dir = path.split('/')[1] if path.startswith('skills/') else None
    for s in re.findall(r'/dev:([a-z][\w-]*)', text):
        if s not in skills:
            errors.append(f'{path}: 없는 스킬 /dev:{s}')
    for a in re.findall(r'(?<![/\w])dev:([a-z][\w-]*)', text):
        if a not in agents and a not in skills:
            errors.append(f'{path}: 없는 에이전트 dev:{a}')
    for m in re.finditer(r'principles\.md 의 ', text):
        after = text[m.end():m.end() + 80]
        if not any(after.startswith(n) for n in principles):
            errors.append(f'{path}: principles.md 에 없는 원칙 「{after[:30]}」')
    if skill_dir:
        base = os.path.join('skills', skill_dir)
        for ref in re.findall(r'`?((?:\.\./[\w-]+/)?(?:playbooks|references|scripts)/[\w./-]+\.\w+)`?', text):
            target = os.path.normpath(os.path.join(base, ref))
            near = os.path.normpath(os.path.join(os.path.dirname(path), ref))
            if not any(os.path.exists(x) for x in (target, ref, near)):
                errors.append(f'{path}: 없는 파일 {ref}')

# 강연 철학이 빠지지 않게 붙잡는 자리
REQUIRED = {
    'skills/mode/SKILL.md': ['## 신뢰 피라미드', '사용자에게 교정을 받음'],
    'skills/mode/playbooks/autonomous-run.md': ['0. 돌리기 전에 이 저장소가 믿을 만한지 본다.'],
    'skills/correct/SKILL.md': ['교정할 때마다'],
}
for f, needles in REQUIRED.items():
    body = open(f).read() if os.path.exists(f) else ''
    for n in needles:
        if n not in body:
            errors.append(f'{f}: 빠지면 안 되는 문장 「{n}」 이 없음')
for path in glob.glob('skills/**/*.md', recursive=True):
    for i, line in enumerate(open(path).read().splitlines(), 1):
        if re.search(r'두 번[^.]{0,12}(지적|고치|교정)|(지적|교정)[^.]{0,12}두 번(?!째를 기다리지)', line):
            errors.append(f'{path}:{i}: 교정은 매번 굳힌다. 「두 번」 조건이 남음')

# devkit 은 어디서나 쓰는 도구다. 특정 사람·앱·개인 도구 이름이 들어오지 않게 막는다.
# 막을 낱말(정규식)은 저장소 밖 ~/.claude/devkit.json 의 personal.owners 와 private_words 에서 읽는다
cfg_path = os.path.expanduser('~/.claude/devkit.json')
cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else {}
words = cfg.get('personal', {}).get('owners', []) + cfg.get('private_words', [])
SPECIFIC = re.compile('|'.join(words) if words else r'(?!)')
# 저장소 전체(새 파일 포함)를 본다. 설치 주소에 꼭 필요한 GitHub 저장소 주소(origin)만 지우고 본다
import subprocess
origin = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True).stdout.strip()
slug = re.sub(r'^.*github\.com[:/]|\.git$', '', origin)
tracked = subprocess.run(['git', 'ls-files', '-co', '--exclude-standard'], capture_output=True, text=True).stdout.splitlines()
for path in tracked:
    if os.path.isfile(path):
        for i, line in enumerate(open(path, errors='ignore').read().splitlines(), 1):
            if SPECIFIC.search(line.replace(slug, '') if slug else line):
                errors.append(f'{path}:{i}: 특정 사람·앱·개인 도구 이름: {line.strip()[:80]}')
# 공개 저장소라 커밋 작성자 메일도 드러난다. 로컬 설정이 있으면 GitHub noreply 메일이어야 한다
email = subprocess.run(['git', 'config', 'user.email'], capture_output=True, text=True).stdout.strip()
if email and not email.endswith('@users.noreply.github.com'):
    errors.append(f'git user.email 이 개인 메일이다. 이 저장소에선 GitHub noreply 메일을 쓴다: git config user.email <id>+<계정>@users.noreply.github.com')

# 판은 끝자리만 1 씩 올린다(0.6.0 → 0.6.1). 고치는 중이면 HEAD 와, 커밋된 상태(CI)면 바로 앞 커밋과 견준다
PJ = '.claude-plugin/plugin.json'
def git_version(rev):
    r = subprocess.run(['git', 'show', f'{rev}:{PJ}'], capture_output=True, text=True)
    return json.loads(r.stdout)['version'] if r.returncode == 0 else None
dirty = subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', PJ]).returncode != 0
old, new = git_version('HEAD' if dirty else 'HEAD~1'), json.load(open(PJ))['version']
if old and old != new:
    o, n = [list(map(int, v.split('.'))) for v in (old, new)]
    if n[:2] != o[:2] or n[2] != o[2] + 1:
        errors.append(f'{PJ}: 판 {old} → {new}. 끝자리만 1 올린다({old} → {".".join(map(str, o[:2] + [o[2] + 1]))})')

if errors:
    sys.exit('\n'.join(errors))
r = subprocess.run([sys.executable, '-I', 'scripts/test_hooks.py'], capture_output=True, text=True)
if r.returncode:
    sys.exit(r.stdout + r.stderr)
r = subprocess.run([sys.executable, '-I', 'skills/no-comments/scripts/count.py', '--self-test'], capture_output=True, text=True)
if r.returncode:
    sys.exit(r.stdout + r.stderr)
print(f'OK 스킬 {len(skills)} · 에이전트 {len(agents)} · 원칙 {len(principles)}')
