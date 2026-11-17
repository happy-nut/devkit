#!/usr/bin/env python3
"""PreToolUse(Edit·Write·MultiEdit) 훅: 코드 파일에 새 주석을 넣는 편집을 한 번 막는다.
기준은 /dev:no-comments 의 예외 목록이다. 예외라고 판단해 같은 편집을 다시 보내면 통과한다."""
import collections, hashlib, json, os, re, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, 'skills', 'no-comments', 'scripts'))
from count import HASH, SLASH, SKIP, blocks_of

EXEMPT = re.compile(r'https?://|SPDX|[Cc]opyright|[Ll]icen[cs]e|prettier-ignore')
STATE = os.path.expanduser('~/.claude/devkit/state/comment-gate.json')

d = json.load(sys.stdin)
i = d.get('tool_input') or {}
path = i.get('file_path', '')
if not path.endswith(HASH + SLASH) or SKIP.search(path):
    sys.exit(0)

edits = i.get('edits') or [i]
if d.get('tool_name') == 'Write':
    old = open(path, encoding='utf-8', errors='replace').read() if os.path.isfile(path) else ''
    pairs = [(old, i.get('content', ''))]
else:
    pairs = [(e.get('old_string', ''), e.get('new_string', '')) for e in edits]

added = []
for old, new in pairs:
    before = collections.Counter(h for _, h in blocks_of(path, old))
    for _, head in blocks_of(path, new):
        if before[head]:
            before[head] -= 1
        elif not EXEMPT.search(head):
            added.append(head)
if not added:
    sys.exit(0)

key = hashlib.sha1(json.dumps([path, sorted(added)], ensure_ascii=False).encode()).hexdigest()
try:
    seen = set(json.load(open(STATE)))
except (OSError, ValueError):
    seen = set()
if key in seen:
    sys.exit(0)
os.makedirs(os.path.dirname(STATE), exist_ok=True)
json.dump(sorted(seen | {key})[-500:], open(STATE, 'w'))

lines = '\n'.join(f'  - {h[:90]}' for h in added[:8])
why = (f'새 주석 {len(added)}개를 넣으려 한다:\n{lines}\n'
       '주석은 기본으로 쓰지 않는다. 이름·타입·함수 추출·단언이나 오류 문자열로 옮기고 주석 없이 다시 써라. '
       '살아남는 예외는 법적 고지, 우리가 바꿀 수 없는 외부 제약(벤더·플랫폼·프로토콜), 공개 API 계약 문서, 이슈·문서 링크뿐이다. '
       '예외가 맞으면 같은 편집을 그대로 한 번 더 보내면 통과한다.')
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': why}}, ensure_ascii=False))
