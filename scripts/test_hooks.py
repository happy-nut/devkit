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

for name, tool, inp, expect in [
    ('한국어 recap', 'mcp__ccd_turn__wrap_up', {'recap': '빈 PR 머지를 막는 훅을 넣었어요. `check.py` 가 통과했고 CI 는 아직 돌고 있어요.', 'actions': [{'label': 'PR 머지'}]}, False),
    ('영어 recap', 'mcp__ccd_turn__wrap_up', {'recap': 'Added the empty PR merge gate. check.py passes and CI is still running.'}, True),
    ('짧은 영어 버튼', 'mcp__ccd_turn__wrap_up', {'recap': '고쳤어요.', 'actions': [{'label': 'Yes, fix 1'}]}, True),
    ('한 낱말 영어 버튼', 'mcp__ccd_turn__wrap_up', {'recap': '고쳤어요.', 'actions': [{'label': 'OK'}]}, False),
    ('한글 섞인 짧은 버튼', 'mcp__ccd_turn__wrap_up', {'recap': '고쳤어요.', 'ask': 'PR 을 머지할까요?', 'actions': [{'label': '1번 fix'}, {'action': 'commit'}]}, False),
    ('빈 필드', 'mcp__ccd_turn__wrap_up', {}, False),
    ('영어 작업 목록', 'mcp__ccd_turn__update_plan', {'items': [{'content': 'check.py 돌리기', 'status': 'pending'}, {'content': 'Push and watch CI', 'status': 'pending'}]}, True),
    ('한국어 작업 목록', 'mcp__ccd_turn__update_plan', {'items': [{'content': 'hooks.json 에 등록', 'status': 'in_progress'}]}, False),
    ('진행 표시만', 'mcp__ccd_turn__update_plan', {'advance': True}, False),
    ('영어 캡션', 'SendUserFile', {'caption': 'Settings screen after the fix'}, True),
    ('영어 명령 설명', 'Bash', {'command': 'git status', 'description': 'Show working tree status'}, True),
    ('한국어 명령 설명', 'Bash', {'command': 'git status', 'description': '작업 트리 상태 보기'}, False),
    ('설명 없는 명령', 'Bash', {'command': 'ls'}, False),
    ('질문 하나', 'AskUserQuestion', {'questions': [{'question': '버튼 색은 어느 쪽이 좋아요?', 'header': '버튼 색', 'options': [{'label': '파랑', 'description': '지금 앱 색'}, {'label': '초록'}]}]}, False),
    ('질문 둘', 'AskUserQuestion', {'questions': [{'question': '버튼 색은?', 'header': '색'}, {'question': '글꼴은?', 'header': '글꼴'}]}, True),
    ('영어 선택지', 'AskUserQuestion', {'questions': [{'question': '어느 쪽으로 할까요?', 'header': '방식', 'options': [{'label': 'Keep both'}, {'label': '하나만'}]}]}, True),
    ('다른 도구', 'Read', {'file_path': '/a/b'}, False),
]:
    if ('deny' in run('tool-text.py', {'tool_name': tool, 'tool_input': inp})) != expect:
        fails.append(f'tool-text: {name}')

for cmd, expect in [
    ('cd x && pytest -q | tail -3 && gh pr merge 12 --squash', True),
    ('pytest -q tests/ && git commit -m x', False),
    ('ls -la', False),
]:
    if ('deny' in run('guard-bash.py', {'tool_input': {'command': cmd}})) != expect:
        fails.append(f'guard-bash: {cmd[:40]}')

import datetime, stat
with tempfile.TemporaryDirectory() as t:
    def fake_gh(checks_out, code, age_sec, files=1):
        created = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=age_sec)).strftime('%Y-%m-%dT%H:%M:%SZ')
        path = os.path.join(t, 'gh')
        open(path, 'w').write(f"""#!/bin/sh
if [ "$2" = "view" ]; then echo '{{"createdAt":"{created}","headRefOid":"abc","files":{json.dumps([{"path": "a"}] * files)}}}'; exit 0; fi
echo '{checks_out}'; exit {code}
""")
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    env = dict(os.environ, PATH=t + os.pathsep + os.environ['PATH'])
    for name, out, code, age, files, expect in [
        ('체크가 아직 안 붙은 새 PR', 'no checks reported on the branch', 1, 20, 1, True),
        ('도는 체크', 'test\tpending\t0', 8, 600, 1, True),
        ('실패한 체크', 'test\tfail\t1m', 1, 600, 1, True),
        ('모두 통과', 'test\tpass\t1m', 0, 600, 1, False),
        ('체크 없는 경로의 오래된 PR', 'no checks reported on the branch', 1, 600, 1, False),
        ('바뀐 파일 0개', 'test\tpass\t1m', 0, 600, 0, True),
    ]:
        fake_gh(out, code, age, files)
        r = subprocess.run([sys.executable, '-I', os.path.join(hooks, 'guard-bash.py')], input=json.dumps({'tool_input': {'command': 'gh pr merge 42 --squash'}, 'cwd': t}), capture_output=True, text=True, env=env).stdout
        if ('deny' in r) != expect:
            fails.append(f'머지 관문: {name}')

    sub = os.path.join(t, 'other'); os.makedirs(sub)
    open(os.path.join(t, 'gh'), 'w').write(f"""#!/bin/sh
case "$*" in *"-R o/r"*) ok=1;; esac
[ "$(pwd -P)" = "$(cd {sub} && pwd -P)" ] && ok=1
[ -z "$ok" ] && {{ echo 'GraphQL: Could not resolve to a PullRequest with the number of 42.' >&2; exit 1; }}
if [ "$2" = "view" ]; then echo '{{"createdAt":"2020-01-01T00:00:00Z","files":[{{"path":"a"}}]}}'; exit 0; fi
echo 'test	pass	1m'; exit 0
""")
    for name, cmd, expect, word in [
        ('--repo 로 다른 저장소', 'M 42 --repo o/r --squash', False, ''),
        ('-R 로 다른 저장소', 'M 42 -R o/r --squash', False, ''),
        ('맨 앞 cd 로 다른 저장소', f'cd {sub} && M 42 --squash', False, ''),
        ('이 폴더에 없는 PR', 'M 42 --squash', True, '못 찾았다'),
    ]:
        r = subprocess.run([sys.executable, '-I', os.path.join(hooks, 'guard-bash.py')], input=json.dumps({'tool_input': {'command': cmd.replace('M ', 'gh pr ' + 'merge ')}, 'cwd': t}), capture_output=True, text=True, env=env).stdout
        if ('deny' in r) != expect or word not in r:
            fails.append(f'머지 관문: {name}')

with tempfile.TemporaryDirectory() as t:
    env = dict(os.environ, HOME=t)
    py = os.path.join(t, 'a.py')
    open(py, 'w').write('# Copyright 2026\nx = 1  # 있던 주석\n')
    def gate(payload):
        return 'deny' in subprocess.run([sys.executable, '-I', os.path.join(hooks, 'no-new-comments.py')], input=json.dumps(payload), capture_output=True, text=True, env=env).stdout
    edit = {'tool_name': 'Edit', 'tool_input': {'file_path': py, 'old_string': 'x = 1  # 있던 주석', 'new_string': 'x = 2  # 있던 주석\n# 값을 2로 바꾼다\ny = x'}}
    for name, payload, expect in [
        ('새 서술 주석', edit, True),
        ('같은 편집을 다시 보내면 통과', edit, False),
        ('있던 주석을 옮기기만', {'tool_name': 'Edit', 'tool_input': {'file_path': py, 'old_string': 'x = 1  # 있던 주석', 'new_string': 'x = 3  # 있던 주석'}}, False),
        ('링크 주석', {'tool_name': 'Edit', 'tool_input': {'file_path': py, 'old_string': 'x', 'new_string': '# https://example.com/spec\nx'}}, False),
        ('새 파일의 docstring', {'tool_name': 'Write', 'tool_input': {'file_path': os.path.join(t, 'b.py'), 'content': 'def f():\n    """하는 일."""\n    return 1\n'}}, True),
        ('기존 파일 덮어쓰기에 남은 주석', {'tool_name': 'Write', 'tool_input': {'file_path': py, 'content': '# Copyright 2026\nx = 5  # 있던 주석\n'}}, False),
        ('ts 새 주석', {'tool_name': 'Edit', 'tool_input': {'file_path': os.path.join(t, 'c.ts'), 'old_string': 'a', 'new_string': 'a // 왜냐하면'}}, True),
        ('마크다운은 보지 않음', {'tool_name': 'Write', 'tool_input': {'file_path': os.path.join(t, 'd.md'), 'content': '# 제목\n'}}, False),
    ]:
        if gate(payload) != expect:
            fails.append(f'새 주석 관문: {name}')

if fails:
    sys.exit('훅 시험 실패:\n' + '\n'.join(fails))
print('훅 시험 OK')
