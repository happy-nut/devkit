"""devkit 훅 시험: 막아야 할 것은 막고, 막지 말아야 할 것은 통과하는지. check.py 가 부른다."""
import json, os, subprocess, sys, tempfile

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
hooks = os.path.join(root, 'hooks')
fails = []

def run(script, payload):
    return subprocess.run([sys.executable, '-I', os.path.join(hooks, script)], input=json.dumps(payload), capture_output=True, text=True).stdout

with tempfile.TemporaryDirectory() as t:
    for name, text, expect in [
        ('영어 보고', "Two workers are building the payment and repo gates. I'll build the agent-behavior hooks myself while they run.", True),
        ('한국어 보고', "결제 관문을 만들고 있어요. `app/deploy/deploy.sh` 에 npm test 와 build 를 넣었고 PR #2730 을 열었어요.", False),
        ('코드 블록', "고쳤어요.\n```python\nprint('a long english code block that should not count')\n```\n검사도 통과했어요.", False),
        ('짧은 영어', "Done.", False),
        ('일본어 보고', "これはテストです。全部完了しました。次の作業に進みます。", True),
        ('중국어 보고', "我已经完成了所有的修改 测试都通过了 接下来继续处理剩下的任务", True),
        ('영어 섞인 짧은 상태 줄', "Waiting on the last two writers.", True),
        ('영어 식별자 섞임', "devkit 0.3.0 에 신뢰 피라미드를 넣었고 check.py 가 mode SKILL autonomous-run correct 를 검사해요.", False),
    ]:
        p = os.path.join(t, 'tx.jsonl')
        open(p, 'w').write(json.dumps({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': text}]}}) + '\n')
        if ('block' in run('korean-stop.py', {'transcript_path': p})) != expect:
            fails.append(f'korean-stop: {name}')
    p = os.path.join(t, 'tx.jsonl')
    if run('korean-stop.py', {'transcript_path': p, 'stop_hook_active': True}):
        fails.append('korean-stop: 이미 한 번 막았으면 놓아줘야 함')

for cmd, expect in [
    ('cd x && pytest -q | tail -3 && gh pr merge 12 --squash', True),
    ('pytest -q tests/ && git commit -m x', False),
    ('ls -la', False),
]:
    if ('deny' in run('guard-bash.py', {'tool_input': {'command': cmd}})) != expect:
        fails.append(f'guard-bash: {cmd[:40]}')

# 머지 관문: 가짜 gh 로 세 상황을 만든다
import datetime, stat
with tempfile.TemporaryDirectory() as t:
    def fake_gh(checks_out, code, age_sec):
        created = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=age_sec)).strftime('%Y-%m-%dT%H:%M:%SZ')
        path = os.path.join(t, 'gh')
        open(path, 'w').write(f"""#!/bin/sh
if [ "$2" = "view" ]; then echo '{{"createdAt":"{created}","headRefOid":"abc"}}'; exit 0; fi
echo '{checks_out}'; exit {code}
""")
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    env = dict(os.environ, PATH=t + os.pathsep + os.environ['PATH'])
    for name, out, code, age, expect in [
        ('체크가 아직 안 붙은 새 PR', 'no checks reported on the branch', 1, 20, True),
        ('도는 체크', 'test\tpending\t0', 8, 600, True),
        ('실패한 체크', 'test\tfail\t1m', 1, 600, True),
        ('모두 통과', 'test\tpass\t1m', 0, 600, False),
        ('체크 없는 경로의 오래된 PR', 'no checks reported on the branch', 1, 600, False),
    ]:
        fake_gh(out, code, age)
        r = subprocess.run([sys.executable, '-I', os.path.join(hooks, 'guard-bash.py')], input=json.dumps({'tool_input': {'command': 'gh pr merge 42 --squash'}, 'cwd': t}), capture_output=True, text=True, env=env).stdout
        if ('deny' in r) != expect:
            fails.append(f'머지 관문: {name}')

if fails:
    sys.exit('훅 시험 실패:\n' + '\n'.join(fails))
print('훅 시험 OK')
