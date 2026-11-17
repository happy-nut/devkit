#!/usr/bin/env python3
"""범위 안 주석을 덩어리 단위로 센다. 리뷰어가 하나도 빠뜨리지 않았는지 맞춰 보는 기준이다.

    python3 count.py <파일·폴더 ...>          # 파일마다 덩어리 수와 합계
    python3 count.py --list <파일·폴더 ...>   # 덩어리마다 「파일:줄  첫머리」
    python3 count.py --self-test

덩어리: 이어진 주석 줄 묶음 하나, 코드 뒤에 붙은 주석 하나, docstring 하나, /* */ 하나.
"""
import ast
import io
import os
import re
import subprocess
import sys
import tokenize

HASH = ('.py', '.sh', '.bash', '.zsh', '.rb', '.yaml', '.yml', '.toml')
SLASH = ('.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.go', '.java', '.kt', '.swift', '.rs', '.c', '.h', '.cpp', '.cs', '.css', '.scss')
SKIP = re.compile(r'(^|/)(node_modules|dist|build|vendor|\.git)/|\.d\.ts$|\.min\.')


def py_blocks(text):
    out, prev = [], None
    try:
        for t in tokenize.generate_tokens(io.StringIO(text).readline):
            if t.type != tokenize.COMMENT or (t.start[0] == 1 and t.string.startswith('#!')):
                continue
            alone = t.line[:t.start[1]].strip() == ''
            if alone and prev == t.start[0] - 1:
                prev = t.start[0]
                continue
            out.append((t.start[0], t.string))
            prev = t.start[0] if alone else None
        for node in ast.walk(ast.parse(text)):
            body = getattr(node, 'body', None)
            if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                    and isinstance(getattr(body[0], 'value', None), ast.Constant) and isinstance(body[0].value.value, str):
                out.append((body[0].lineno, body[0].value.value.strip().split('\n')[0]))
    except (SyntaxError, tokenize.TokenError, IndentationError):
        return hash_blocks(text) + [(i, l.strip()) for i, l in enumerate(text.splitlines(), 1) if l.strip()[:3] in ('"""', "'''") and len(l.strip()) > 3]
    return sorted(out)


def hash_blocks(text):
    out, prev = [], None
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if s.startswith('#') and not (i == 1 and s.startswith('#!')):
            if prev != i - 1:
                out.append((i, s))
            prev = i
    return out


def slash_blocks(text):
    out, i, n, line, quote, prev_end = [], 0, len(text), 1, None, None
    while i < n:
        c = text[i]
        if c == '\n':
            line += 1
        if quote:
            if c == '\\':
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in '\'"`':
            quote = c
        elif text.startswith('//', i):
            end = text.find('\n', i)
            end = n if end < 0 else end
            alone = text[text.rfind('\n', 0, i) + 1:i].strip() == ''
            if not (alone and prev_end == line - 1):
                out.append((line, text[i:end].strip()))
            prev_end = line if alone else None
            i = end
            continue
        elif text.startswith('/*', i):
            end = text.find('*/', i + 2)
            end = n if end < 0 else end + 2
            out.append((line, text[i:end].split('\n')[0].strip()))
            line += text.count('\n', i, end)
            prev_end = None
            i = end
            continue
        i += 1
    return out


def blocks(path):
    return blocks_of(path, open(path, encoding='utf-8', errors='replace').read())


def blocks_of(path, text):
    if path.endswith('.py'):
        return py_blocks(text)
    if path.endswith(HASH):
        return hash_blocks(text)
    return slash_blocks(text)


def files(args):
    for a in args:
        if os.path.isdir(a):
            listed = subprocess.run(['git', '-C', a, 'ls-files', '-co', '--exclude-standard'], capture_output=True, text=True)
            names = [os.path.join(a, p) for p in listed.stdout.splitlines()] if listed.returncode == 0 else \
                [os.path.join(r, f) for r, _, fs in os.walk(a) for f in fs]
        else:
            names = [a]
        for p in names:
            if p.endswith(HASH + SLASH) and not SKIP.search(p) and os.path.isfile(p):
                yield p


def main(argv):
    if '--self-test' in argv:
        return self_test()
    listing = '--list' in argv
    total = 0
    for p in files([a for a in argv if not a.startswith('--')]):
        bs = blocks(p)
        total += len(bs)
        if listing:
            for ln, head in bs:
                print(f'{p}:{ln}  {head[:80]}')
        elif bs:
            print(f'{len(bs):5}  {p}')
    print(f'주석 덩어리 {total}')
    return 0


def self_test():
    py = '#!/usr/bin/env python3\n"""모듈."""\n# 하나\n# 이어짐\nx = "# 문자열"  # 뒤\n\ndef f():\n    """함수."""\n    return 1\n'
    assert [l for l, _ in py_blocks(py)] == [2, 3, 5, 8], py_blocks(py)
    ts = 'const a = "//아님"; // 뒤\n// 하나\n// 이어짐\n/* 여러\n줄 */\nconst b = `/*아님*/`;\n'
    assert [l for l, _ in slash_blocks(ts)] == [1, 2, 4], slash_blocks(ts)
    sh = '#!/bin/sh\n# 하나\n# 이어짐\necho hi\n# 둘\n'
    assert [l for l, _ in hash_blocks(sh)] == [2, 5], hash_blocks(sh)
    print('count.py self-test OK')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
