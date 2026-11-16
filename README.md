# devkit

에이전트를 믿을 수 있게 만드는 Claude Code 작업 방식 플러그인이다. 일은 플레이북 단계대로 하고, 판단은 원칙으로 하고, 끝은 눈으로 본 증거로 낸다. 에이전트를 교정할 때마다 그 실수를 글 대신 구조·검사·훅으로 막는다.

Lauren Tan 의 강연 「All Code Is Slop (Except Mine)」(2026-11)과 그가 공개한 pstack(MIT)에서 출발해 Claude Code 에 맞게 다시 썼다. 강연의 요지는 「make it yours」다. 남의 설정을 그대로 쓰지 말고 포크해서 자기 교정 이력으로 키운다.

> 한국어로 쓰였고, 에이전트가 사용자에게 한국어로 말하게 하는 훅이 들어 있다.

## 신뢰 피라미드

에이전트에게 투자하는 순서다. 위가 가장 강하다.

1. **코드 구조**: 잘못 쓸 수 없는 API·디렉터리 구조
2. **결정적 검사**: 린트·타입·테스트·훅·CI
3. **검증**: 직접 실행·스크린샷·형식 검증 같은 산출물
4. **산문**: AGENTS.md·스킬·메모리. 판단이 필요한 것만, 마지막에

## 설치

```bash
claude plugin marketplace add happy-nut/devkit
claude plugin install devkit@devkit
```

새 판은 `claude plugin update devkit@devkit` (서드파티 마켓플레이스는 자동 업데이트가 꺼져 있다).

### 개인 설정 (선택)

저장소 밖 `~/.claude/devkit.json` 에 둔다. 플러그인에는 넣지 않는다.

```json
{
  "personal": { "owners": ["<내 GitHub 계정>"], "paths": ["~/code/"] },
  "private_words": ["<devkit 에 들어오면 안 되는 내 앱·회사 이름(정규식)>"]
}
```

- `personal`: 개인 저장소를 가린다. 여기 걸리는 저장소에서는 머지까지 맡고, 나머지는 회사 저장소로 보고 더 좁게 움직인다. 파일이 없으면 모두 회사 저장소로 본다.
- `private_words`: devkit 을 고칠 때 `scripts/check.py` 가 이 낱말이 저장소 어느 파일에든 들어오는 것을 막는다(커밋 전 훅 `.githooks/pre-commit`, `git config core.hooksPath .githooks`). 커밋 작성자 메일도 GitHub noreply 여야 통과한다. 포크를 공개해도 개인 이름이 새지 않는다.

## 쓰는 법

할 일 앞에 붙인다.

```
/devkit:mode 버튼 색이 화면마다 달라
/devkit:mode 이 PR 머지까지 해
```

`/devkit:mode` 가 플레이북(조사·버그 수정·기능·리팩터링·성능·PR 돌보기 등 23개)을 고르고, 필요한 스킬을 부른다. 스킬만 따로 불러도 된다.

### 세 가지만 기억한다

1. **일을 시킬 때** `/devkit:mode <할 일>`. 무엇을 원하는지와 「됐다」를 어떻게 알지를 적으면 충분하다. 방법은 적지 않는다.
2. **틀렸을 때** 그냥 대화로 지적한다. 「이거 틀렸어, 원래 X 여야 해」. `/devkit:mode` 가 켜져 있으면 고치는 데서 끝나지 않고 같은 실수가 다시 못 나오게 검사·구조로 막은 뒤 「어느 층에 넣었는지」 보고한다. 모드 밖이면 `/devkit:correct <지적>`.
3. **devkit 자체가 마음에 안 들 때** `/devkit:reflect <무엇이 별로였나>`. devkit 저장소(포크)를 고쳐 PR 로 올린다.

방향만 바꾸고 싶으면 원칙 이름을 댄다. 「Prove It Works 로 다시 봐」(실제로 돌려 증명), 「Fix Root Causes」(땜질 말고 원인), 「Laziness Protocol」(더 작게).

### 교정이 장치가 되는 층

교정은 가능한 가장 위층에 들어간다. 위층일수록 강하다.

| 층 | 예 |
|---|---|
| 1. 구조 | 잘못 쓰는 API 를 감싼 한 곳만 남기고 지운다 |
| 2. 검사 | 린트·테스트·훅이 그 실수를 오류로 낸다 |
| 3. 저장소 규칙 | 판단이라 기계로 못 막으면 그 저장소 `AGENTS.md` 의 결정 지점에 한 줄 |
| 4. 메모리 | 저장소를 가로지르는 개인 습관만 |

| 스킬 | 하는 일 |
|---|---|
| `/devkit:design` | 여러 설계를 병렬로 그려 보고 기반을 골라 좋은 점을 접붙인다 |
| `/devkit:swarm` | 독립 조각으로 나눠 병렬 처리, PASS/ISSUES/BLOCKED 로 모은다 |
| `/devkit:review` | 여러 모델 적대 리뷰와 파급 범위 증명 |
| `/devkit:correct` | 교정을 받을 때마다 구조·린트·테스트로 굳힌다 |
| `/devkit:tdd` | 싸고 분명할 때만 테스트 먼저 |
| `/devkit:bench` | 성능 숫자를 믿기 전 점검표 |
| `/devkit:how`, `/devkit:why` | 지금 어떻게 도는지, 왜 이렇게 됐는지 |
| `/devkit:recall` | 며칠 전 작업 맥락 되살리기 |
| `/devkit:reflect` | 반복되는 교정을 찾아 devkit 자체를 고친다 |
| `/devkit:catchup` | 자리 비운 사이 일을 결정할 것만 추려 보고 |
| `/devkit:log` | 긴 자율 작업의 결정 기록 |
| `/devkit:verify-setup` | 앱을 직접 몰아 증명하는 프로젝트 전용 검증 스킬 만들기·유지 |
| `/devkit:write` | 한국어 글 규칙 |
| `/devkit:ts` | TypeScript 규칙 |
| `/devkit:no-comments` | 주석 걷어내기 리뷰 |
| `/devkit:formal-setup` | 버그가 가장 비싼 곳을 형식 검증(TLA+ 등)하는 프로젝트 전용 스킬 만들기·유지 |
| `/devkit:statechart` | TLA+ 모델을 검사해 규칙이 깨지는 최단 경로와 상태도로 보여 준다 |
| `/devkit:catchup-video` | catchup 을 자막 달린 짧은 영상으로 |
| `/devkit:triage`, `/devkit:repro-fix` | 채널의 이슈 보고를 분류하고, 확인된 버그를 재현해 초안 수정까지 |
| `/devkit:bot-ui` | 누르면 Claude Code 루틴을 깨우는 로컬 페이지 |
| `/devkit:setup` | 개인 설정(`~/.claude/devkit.json`) 만들기 |
| `/devkit:help` | 무엇을 쓸지 고르는 안내 |

## 훅 (설치하면 자동으로 켜진다)

| 훅 | 막는 것 |
|---|---|
| `hooks/korean-stop.py` (Stop) | 사용자에게 한 마지막 말이 한국어가 아니면 한 번 되돌려 한국어로 다시 쓰게 한다(코드·경로·짧은 줄은 제외) |
| `hooks/guard-bash.py` (PreToolUse) | 바뀐 파일이 0개이거나 체크가 아직 안 붙었거나 돌고 있거나 실패한 PR 의 `gh pr merge`, `pytest … \| tail && 커밋·머지`(실패를 삼킴) |
| `hooks/tool-text.py` (PreToolUse, 사용자가 읽는 도구 글) | 작업 요약·작업 목록·버튼(`wrap_up`·`update_plan`), 파일 캡션, `AskUserQuestion` 질문·선택지, Bash 설명이 한국어가 아니면 막는다(판정은 `korean-stop.py` 와 같다. 짧은 글은 한글 낱말 없이 두 낱말 이상일 때만). `AskUserQuestion` 질문이 둘 이상이어도 막는다 |

훅을 고치면 `scripts/test_hooks.py` 에 막아야 할 예와 통과해야 할 예를 같이 넣는다.

## 고칠 때

규칙은 `docs/authoring.md`. 고친 뒤 반드시:

```bash
python3 scripts/check.py
```

판(`plugin.json` 의 version)은 끝자리만 1 씩 올린다(0.6.2 → 0.6.3). `check.py` 와 CI 가 막는다.

devkit 을 고칠 때도 같다. 스킬에 문장을 더 쓰기 전에 검사나 구조로 막을 수 있는지 먼저 본다.

## 출처

원칙·플레이북·스킬 상당수는 [pstack](https://github.com/cursor/plugins/tree/main/pstack)(커밋 bf0c7cd)을 고쳐 쓴 것이다. 원본의 스킬·플레이북을 모두 옮겼다(이름 대응은 `docs/authoring.md`).

Copyright (c) 2026 Lauren Tan, MIT License

```
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
