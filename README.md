# devkit

Claude Code 에이전트가 한 일을 믿을 수 있게 만드는 플러그인이다. 에이전트에게 정해진 순서(플레이북)로 일하게 하고, 판단은 원칙 문서로 잡고, 끝났다는 말은 직접 돌려서 본 증거가 있을 때만 받는다. 에이전트가 틀려서 교정할 때마다 그 실수를 글이 아니라 구조, 검사, 훅으로 막는다.

Lauren Tan 의 강연 「All Code Is Slop (Except Mine)」(2026-11)과 그가 공개한 pstack(MIT)에서 출발해 Claude Code 에 맞게 다시 썼다. 강연의 요지는 「make it yours」다. 남의 설정을 그대로 쓰지 말고 포크해서 자기 교정 이력으로 키우라는 뜻이다. 스킬과 문서는 모두 한국어이고, 에이전트가 사용자에게 한국어로 말하게 하는 훅이 들어 있다.

## 설치

Claude Code 가 설치되어 있어야 한다. 훅은 `python3` 으로 돌고, PR 머지 검사는 `gh`(GitHub CLI)를 쓴다.

```bash
claude plugin marketplace add happy-nut/devkit
claude plugin install devkit@devkit
```

서드파티 마켓플레이스는 자동 업데이트가 꺼져 있다. 새 판은 직접 받는다.

```bash
claude plugin update devkit@devkit
```

## 처음 써 보기

할 일 앞에 `/devkit:mode` 를 붙인다.

```
/devkit:mode 버튼 색이 화면마다 달라
/devkit:mode 이 PR 머지까지 해
```

그러면 에이전트가 다음을 한다.

1. 목표와 가장 작은 변경을 자기 말로 한 번 적는다.
2. 플레이북 23개 중 하나를 고르고 그 단계를 작업 목록에 옮긴다.
3. 단계마다 필요한 원칙 절을 읽고, 필요하면 서브에이전트에 일을 나눈다.
4. 스크린샷, 실행 출력 같은 확인한 증거와 함께 보고한다.

무엇을 원하는지와 「됐다」를 어떻게 알 수 있는지만 적으면 된다. 방법은 적지 않는다.

에이전트가 틀리면 대화로 지적한다. 「이거 틀렸어, 원래 X 여야 해」처럼 말한다. `/devkit:mode` 중이면 고치는 데서 끝나지 않고, 같은 실수가 다시 나오지 못하게 막는 장치를 넣은 뒤 어느 층에 넣었는지 보고한다. 모드 밖이면 `/devkit:correct <지적>` 을 쓴다.

devkit 자체가 마음에 안 들면 `/devkit:reflect <무엇이 별로였나>` 를 쓴다. devkit 저장소(포크)를 고쳐 PR 로 올린다.

방향만 바꾸려면 원칙 이름을 댄다. 「Prove It Works 로 다시 봐」(실제로 돌려 증명), 「Fix Root Causes」(땜질 말고 원인), 「Laziness Protocol」(더 작게).

무엇을 쓸지 모르겠으면 `/devkit:help` 에 물어본다.

## 구성

```
skills/mode/SKILL.md             /devkit:mode. 플레이북을 고르는 라우터
skills/mode/principles.md        원칙 24개(한 파일, 절마다 ## 영어 이름)
skills/mode/playbooks/           플레이북 23개
skills/mode/references/          플레이북이 읽는 참고 문서
skills/mode/scripts/             플레이북이 돌리는 스크립트
skills/<이름>/SKILL.md           /devkit:<이름> 으로 부르는 스킬(mode 포함 25개)
agents/                          서브에이전트 devkit:worker, devkit:comment-reviewer
hooks/                           설치하면 자동으로 켜지는 훅
scripts/check.py                 저장소 검사
docs/authoring.md                devkit 을 고치는 규칙
```

플레이북은 조사, 버그 수정, 기능, 리팩터링, 성능, PR 열기와 돌보기, 자율 실행, 오토파일럿, 일시 중지, 워크트리 정리처럼 일의 종류마다 단계를 정해 둔 것이다. 전체 목록은 `skills/mode/playbooks/` 에 있다.

원칙은 판단이 갈리는 지점의 기준이다. `Prove It Works` 는 돌려 보기 전에 됐다고 말하지 못하게 하고, `Never Block on the Human` 은 사람 답을 기다리느라 멈추지 않게 한다.

### 신뢰 피라미드

에이전트에게 투자하는 순서다. 위가 가장 강하다.

1. 코드 구조. 잘못 쓸 수 없는 API 와 디렉터리 구조
2. 결정적 검사. 린트, 타입, 테스트, 훅, CI
3. 검증. 직접 실행, 스크린샷, 형식 검증 같은 산출물
4. 산문. `AGENTS.md`, 스킬, 메모리. 판단이 필요한 것만, 마지막에

교정은 가능한 가장 위층에 넣는다. 잘못 쓰는 API 는 감싼 한 곳만 남기고 지우고, 안 되면 린트나 테스트가 오류를 내게 한다. 판단이라 기계로 못 막으면 그 저장소 `AGENTS.md` 에 한 줄 적는다. 메모리에는 저장소를 가로지르는 개인 습관만 둔다.

## 스킬

스킬은 모두 `/devkit:<이름>` 으로 직접 부를 때만 돈다. `/devkit:mode` 가 플레이북 단계에서 필요한 스킬을 대신 부르기도 한다.

일을 시키고 나누는 스킬이다.

| 스킬 | 하는 일 |
|---|---|
| `/devkit:mode` | 플레이북을 고르고 단계대로 일한다 |
| `/devkit:design` | 여러 설계를 병렬로 그려 보고, 하나를 기반으로 골라 다른 안의 좋은 점을 붙인다 |
| `/devkit:swarm` | 일을 독립 조각으로 나눠 병렬로 풀고 PASS, ISSUES, BLOCKED 로 모은다 |
| `/devkit:review` | 여러 모델이 변경을 적대적으로 깨 보고, 실행으로 증명된 것만 보고한다. 파급 범위도 본다 |

실수를 막고 품질을 지키는 스킬이다.

| 스킬 | 하는 일 |
|---|---|
| `/devkit:correct` | 에이전트의 반복 실수를 구조, 린트, 테스트로 막는다. 새 검사가 과거 실수에서 실패하는지 증명한다 |
| `/devkit:tdd` | 버그를 실패하는 회귀 테스트로 먼저 만든다. 싸고 분명할 때만 쓴다 |
| `/devkit:bench` | 성능 숫자를 믿거나 보고하기 전에 점검한다 |
| `/devkit:no-comments` | 주석을 심사해 지우고, 주석이 가리던 우회 코드를 고친다 |
| `/devkit:ts` | `.ts`, `.tsx` 를 고칠 때 쓰는 TypeScript 규칙 |
| `/devkit:write` | 한국어 글(문서, README, PR 설명, 커밋 메시지) 규칙 |

코드와 작업 맥락을 이해하는 스킬이다.

| 스킬 | 하는 일 |
|---|---|
| `/devkit:how` | 코드가 어떻게 도는지, 무엇을 어디에 둘지 설명한다 |
| `/devkit:why` | 커밋, PR, 이슈에서 근거를 찾아 왜 이렇게 됐는지 답한다 |
| `/devkit:recall` | 며칠 전 작업의 맥락을 대화 기록에서 되살린다 |
| `/devkit:catchup` | 자리를 비운 사이 바뀐 것과 사용자가 정할 것만 짧게 보고한다 |
| `/devkit:catchup-video` | catchup 을 자막 달린 짧은 영상으로 만든다 |
| `/devkit:log` | 긴 자율 작업의 결정 기록을 TSV 한 파일로 남긴다 |

프로젝트별 검증을 만드는 스킬이다.

| 스킬 | 하는 일 |
|---|---|
| `/devkit:verify-setup` | 앱을 사용자처럼 몰아 증명하는 프로젝트 전용 검증 스킬을 만들고 유지한다 |
| `/devkit:formal-setup` | 버그가 가장 비싼 코드를 형식 검증(TLA+ 등)하는 프로젝트 전용 스킬을 만들고 유지한다 |
| `/devkit:statechart` | TLA+ 모델을 TLC 로 검사하고, 규칙이 깨지는 최단 경로를 Mermaid 상태 차트로 그린다 |

운영과 설정을 돕는 스킬이다.

| 스킬 | 하는 일 |
|---|---|
| `/devkit:reflect` | 반복되는 교정과 선호를 찾아 devkit 을 고치는 PR 을 올린다 |
| `/devkit:triage` | 채널에 올라온 이슈 보고를 분류해 스레드에 판정 답글 하나를 남긴다 |
| `/devkit:repro-fix` | 분류된 버그를 실제 UI 에서 재현하고, 재현된 뒤에만 초안 수정 PR 을 낸다 |
| `/devkit:bot-ui` | 누르면 Claude Code 루틴을 깨우는 로컬 페이지를 만든다 |
| `/devkit:setup` | `~/.claude/devkit.json` 을 만들거나 고친다 |
| `/devkit:help` | 상황에 맞는 스킬을 고르고 보낼 프롬프트를 준다 |

## 훅

설치하면 `hooks/hooks.json` 의 훅이 자동으로 켜진다.

| 훅 | 막는 것 |
|---|---|
| `hooks/korean-stop.py` (Stop) | 사용자에게 한 마지막 말이 한국어가 아니면 한 번 되돌려 다시 쓰게 한다. 코드, 경로, 짧은 줄은 세지 않는다 |
| `hooks/guard-bash.py` (PreToolUse) | 바뀐 파일이 0개이거나, 체크가 아직 안 붙었거나 돌고 있거나 실패한 PR 의 `gh pr merge`. 테스트 출력을 `tail` 로 넘긴 뒤 `&&` 로 커밋이나 머지를 잇는 명령(테스트 실패가 삼켜진다) |
| `hooks/tool-text.py` (PreToolUse) | 사용자가 읽는 도구 글이 한국어가 아닌 경우. 작업 요약과 작업 목록(`wrap_up`, `update_plan`), 파일 캡션(`SendUserFile`), `AskUserQuestion` 의 질문과 선택지, Bash 설명이 대상이다. `AskUserQuestion` 에 질문이 둘 이상 들어 있어도 막는다 |

세 훅의 한국어 판정은 `hooks/korean.py` 하나가 한다. 훅을 고치면 `scripts/test_hooks.py` 에 막아야 할 예와 통과해야 할 예를 같이 넣는다.

## 개인 설정

선택 사항이다. 저장소 밖 `~/.claude/devkit.json` 에 둔다. `/devkit:setup` 이 만들어 준다.

```json
{
  "personal": { "owners": ["<내 GitHub 계정>"], "paths": ["~/code/"] },
  "private_words": ["<devkit 에 들어오면 안 되는 내 앱·회사 이름(정규식)>"]
}
```

- `personal`: 개인 저장소를 가린다. `origin` 의 소유자가 `owners` 에 있거나 저장소가 `paths` 아래면 개인 저장소로 보고 머지까지 맡는다. 나머지는 회사 저장소로 보고, 머지·배포·공유 브랜치 push 는 사용자가 말했을 때만 한다. 파일이 없으면 모두 회사 저장소로 본다.
- `private_words`: devkit 을 고칠 때 `scripts/check.py` 가 이 낱말이 저장소 어느 파일에든 들어오는 것을 막는다.
- `models`: 역할별 서브에이전트 모델. 기본값과 다르게 쓸 역할만 적는다.

## devkit 을 고칠 때

규칙은 `docs/authoring.md` 에 있다. 고친 뒤 검사를 돌린다.

```bash
python3 scripts/check.py
```

`check.py` 는 스킬과 에이전트의 frontmatter, 본문이 가리키는 파일과 스킬 이름, 긴 대시 같은 금지 낱말, `private_words`, 판 번호를 검사하고 `test_hooks.py` 도 이어서 돌린다. CI(`.github/workflows/check.yml`)도 푸시와 PR 마다 `check.py` 를 돌린다.

커밋 전에 검사하려면 훅 경로를 한 번 지정한다. 이때 로컬 커밋 작성자 메일이 GitHub noreply 주소가 아니면 `check.py` 가 막는다. 공개 저장소라 개인 메일이 새지 않게 하려는 것이다.

```bash
git config core.hooksPath .githooks
```

`.claude-plugin/plugin.json` 의 `version` 은 끝자리만 1 씩 올린다(0.6.2 에서 0.6.3). 다른 자리를 올리거나 2 이상 건너뛰면 `check.py` 와 CI 가 막는다. 그 판으로 태그·GitHub Release 를 만드는 것도 `main` 에 push 될 때 `.github/workflows/release.yml` 이 자동으로 한다. 사람이나 에이전트가 따로 `gh release create` 를 부를 필요가 없다(판만 올리고 릴리즈를 깜빡하는 실수를 CI 가 대신한다).

스킬에 문장을 더 쓰기 전에, 검사나 구조로 막을 수 있는지 먼저 본다.

## 출처

원칙, 플레이북, 스킬 상당수는 [pstack](https://github.com/cursor/plugins/tree/main/pstack)(커밋 bf0c7cd)을 고쳐 쓴 것이다. 원본의 스킬과 플레이북을 모두 옮겼고, 이름 대응은 `docs/authoring.md` 에 있다.

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
