---
name: reflect
description: "지금 대화나 최근 대화 기록에서 오래갈 교훈과 되풀이되는 교정·선호를 캐서, 사용자 승인 뒤 devkit 저장소(또는 그 프로젝트의 AGENTS.md)에 PR 로 반영한다. Use when the user says reflect, \"automate me\", \"turn my preferences or working style into the skill\", \"update my mode\", or wants agents to follow how they work. /devkit:reflect"
disable-model-invocation: true
---

# Reflect

대화 기록에서 오래갈 교훈을 캐서 devkit 의 스킬 수정으로 보낸다. 두 가지로 돈다.

- **이번 대화.** 사용자가 「reflect」, `/devkit:reflect` 라고 하면 지금 대화 하나를 본다.
- **내 방식.** 「automate me」, 「내 방식을 스킬로」, 「모드 갱신」이면 최근 여러 대화에서 되풀이되는 교정과 선호를 캔다. 아래 「내 방식 캐기」를 1~2단계 대신 쓴다.

대화가 사소하거나, 주제에서 벗어났거나, 이미 있는 스킬을 제대로 따른 대화면 하지 않고 그렇다고 한 줄 말한다. 한 번 있었던 일은 교훈이 아니다.

## 어디에 반영하나

교훈은 기억 파일이 아니라 규칙이 읽히는 자리에 넣는다. 강도 순서는 「principles.md 의 Encode Lessons in Structure」(경로 `../mode/principles.md`)를 따른다.

1. 검사·구조로 막을 수 있으면 그쪽이다. 사용자의 교정이면 한 번이라도 글보다 장치다. 그 프로젝트의 실수면 /devkit:correct 로 보내고, devkit 자체의 실수면 devkit 의 `scripts/check.py` 에 검사를 더한다.
2. 특정 저장소에만 맞는 교훈은 그 저장소의 `AGENTS.md`(없으면 `CLAUDE.md`)의 결정 지점 문장이다. devkit 보다 저장소 규칙이 앞선다.
3. 저장소를 가리지 않는 작업 방식은 devkit 의 스킬이다. 작업 방식 전반은 `skills/mode/SKILL.md`, 원칙은 `skills/mode/principles.md`, 특정 워크플로는 그 `skills/<이름>/SKILL.md`, 서브에이전트는 `agents/<이름>.md`.

플러그인 캐시(`~/.claude/plugins/cache/`) 안 파일은 절대 고치지 않는다. 다음 업데이트에 덮인다. devkit 은 원본 저장소에서 고친다. 원본은 플러그인 `.claude-plugin/plugin.json` 의 `repository` 다. 이 머신에 클론이 있으면 그것(`<devkit 원본>`), 없으면 `gh repo clone <repository>` 로 받는다. 고치기 전에 그 저장소의 `docs/authoring.md` 를 끝까지 읽는다.

## 1. 지금 대화 기록 찾기

나눠 보내기 전에 이 대화의 기록 파일을 찾는다. 현재 작업 폴더의 기록 폴더만 본다. `~/.claude/projects/*/` 를 통째로 glob 하지 않는다. 다른 프로젝트의 사적인 대화를 읽게 된다.

```bash
d=~/.claude/projects/$(pwd | sed 's#[/.]#-#g')
ls -t "$d"/*.jsonl "$d"/*/subagents/*.jsonl 2>/dev/null | head -10
```

후보마다 `type == "user"` 인 첫 줄의 `.message.content` 를 읽는다. 이 대화를 연 사용자 메시지와 같은 파일을 고른다. 맞는 것이 없으면 세션 요약을 짧게 써서 대신 넘긴다.

## 2. 검토자 셋을 병렬로

한 메시지에 `Agent` 셋을 띄운다. `subagent_type: "general-purpose"`. 대화가 가리키는 이슈·채팅·관측 기록을 MCP 로 찾아봐야 해서 `Explore` 를 쓰지 않는다. 템플릿에 「파일을 고치지 마라」가 들어 있다.

| 렌즈 | 모델 | 템플릿 |
|---|---|---|
| 판단 | `opus` | `references/judgment-reviewer.md` |
| 도구 | `opus` | `references/tooling-reviewer.md` |
| 다른 각도 | `fable` | `references/divergent-reviewer.md` |

템플릿을 그대로 넘기고 표시된 자리에 기록 경로나 요약을 넣는다. 검토자는 결과를 응답 본문으로 돌려준다. 셋 다 같은 회사 모델이라 다양성이 약하다는 것을 6단계 요약에 한 줄 적는다.

## 3. 종합

`Agent` 하나, `subagent_type: "general-purpose"`, `model: "opus"`. 인용을 MCP 로 확인해 보기도 하므로 `general-purpose` 다. `references/synthesizer.md` 를 그대로 넘기고 표시된 자리에 검토자 셋의 결과 전체를 넣는다. Accepted / Rejected / Backlog 목록이 돌아온다.

## 4. 구조로 막을 것 가르기

Accepted 가운데 린트·스크립트·메타데이터·런타임 검사가 더 확실히 막을 것은 Backlog 로 옮긴다. 「principles.md 의 Encode Lessons in Structure」대로다.

## 5. 승인받고 반영

종합 결과 Accepted / Rejected / Backlog 전체를 보여 주고, Accepted 의 수정은 사용자가 명시적으로 승인하기 전에 하나도 반영하지 않는다. 스킬 수정은 앞으로의 모든 에이전트에 영향을 준다. 자동으로 반영하지 않는다. 승인은 `AskUserQuestion` 한 번으로 받는다. 질문 하나, `multiSelect: true`, 선택지는 Accepted 행(넷이 넘으면 묶음별로). 사용자는 일부를 고르고 라우팅을 바꿀 수 있다. 승인 전에 행마다 반영될 파일 경로(devkit 의 `skills/<이름>/SKILL.md`, 또는 `<저장소>/AGENTS.md`)를 보인다.

Backlog 는 승인을 기다리지 않는다. devkit 자체의 것은 `gh issue create -R <repository>`, 다른 저장소의 것은 그 저장소에 `[improve]` 이슈로 바로 등록한다. 기다리는 것은 Accepted 뿐이다.

승인된 행은 라우팅대로 반영한다.

- 사소한 기존 스킬 수정(한 줄 추가, 문장 다듬기, 낡은 사실 고치기): 내가 직접 고친다.
- 큰 기존 스킬 수정(새 절, 새 표, 10줄쯤 넘는 것): `anthropic-skills:skill-creator` 스킬의 초안·시험·반복 흐름으로 한다.
- `tune description: <스킬 경로>`(스킬이 있는데 불려야 할 때 안 불렸다): `skill-creator` 의 description 다듬기 흐름으로 한다. devkit 스킬은 사람이 부르는 스킬이라 `/devkit:<이름>` 과 영어 트리거 문구가 description 에 들어가야 한다.
- `new skill: <이름>`: `skill-creator` 로 만든다. 모양을 즉석에서 지어내지 않는다.

devkit 반영은 이렇게 한다.

1. `<devkit 원본>` 에서 main 을 받아 새 워크트리와 브랜치를 만든다(`git -C <devkit 원본> worktree add ../devkit-reflect-<주제> -b reflect/<주제> origin/main`). main 에 직접 push 하지 않는다.
2. 고친 뒤 `python3 scripts/check.py` 를 돌려 통과시킨다. 고친 문장이 `docs/authoring.md` 의 글 규칙을 지키는지 /devkit:write 기준으로 다시 읽는다.
3. 커밋하고 PR 을 연다. PR 본문에는 행마다 문제, 고친 곳, 근거(세션 UUID 또는 날짜)를 한 줄씩 쓴다.
4. devkit 은 개인 저장소다. 승인한 행의 반영은 「고쳐」와 같아서 CI 통과와 머지까지 간다. 머지 뒤 `claude plugin update devkit@devkit` 를 돌린다. 서드파티 마켓플레이스는 자동 업데이트가 꺼져 있다.

저장소 `AGENTS.md` 반영은 그 저장소의 규칙(개인이면 PR·머지, 회사면 PR 까지)을 따른다.

## 6. 사용자에게 요약

서두 없이 짧은 목록으로 쓴다.

- 반영한 수정: `<파일 경로>`. 무엇이 바뀌었는지 한 줄씩. PR 번호와 머지 여부.
- 새로 만든 스킬: `<파일 경로>`. 한 줄씩(드물다).
- 등록한 Backlog: `<이슈 제목>` (#번호). 한 줄씩.
- 버린 것: 버린 교훈마다 한 줄, 종합자가 댄 이유.
- 검토 패널이 한 회사 모델뿐이었다는 한 줄.

## 내 방식 캐기

「automate me」류 요청일 때 1~2단계 대신 한다. 결과는 새 `-mode` 스킬이 아니라 devkit 의 `skills/mode/SKILL.md`(와 해당 스킬)의 수정이다. 3단계부터는 위와 같다.

1. **마지막 반영 이후만 본다.** `git -C <devkit 원본> log -1 --format=%cI -- skills/mode/SKILL.md` 로 마지막 수정 시각을 얻고 그 뒤 기록만 캔다. 처음이면 최근 2~4주다.
2. **기록을 나눠 캔다.** 현재 작업 폴더의 기록 폴더만 쓴다(위 1단계의 경로). 사용자가 여러 저장소를 넘나들며 일하면 어느 폴더를 볼지 범위를 한 줄로 밝히고 그 폴더들만 본다. 기간을 셋쯤으로 나눠 조각마다 `Agent`(`general-purpose`, `model: "sonnet"`, 브리프에 「파일을 고치지 마라」)를 병렬로 띄운다. 조각마다 아래 신호를 찾아 근거(세션 UUID, 사용자 말 인용)와 함께 짧은 목록으로 돌려받는다.
   - 응답 선호: 길이, 어조, 형식, 「쉽게 말해」 같은 교정.
   - 위임 습관: 서브에이전트, 모델, 따로 쓰는 흐름, 병렬.
   - 검증 자세: 「됐다」의 뜻, 단위 테스트인지 실제 재현인지, 리뷰어.
   - 코드와 글의 규율: 스타일, 인용하는 원칙, 린트·포맷 도구.
   - 진행 관례: 워크트리, 커밋, PR, 리뷰·머지 도구.
   - 메타 선호: 작업 중에 스킬 고치기, 새 스킬 제안.
   - 사용자가 에이전트를 고친 자리. 한 번이라도 따로 표시한다. 이것은 글이 아니라 장치 후보다(위 「어디에 반영하나」 1번).
3. **조각을 맞대 본다.** 두 조각 이상에서 보인 신호만 높은 확신으로 올린다. 하나에서만 보인 신호는 대개 버린다. 한 번 말하고 다른 때 반대로 말한 선호는 잡음이다.
4. **한 번만 묻는다.** 기록에 아직 안 나온 의도는 캐기로 못 찾는다. `AskUserQuestion` 을 한 번 부른다. 질문은 한두 개, 선택지는 4~6개, 영역을 묻는 질문은 `multiSelect: true` 다. 넓게 묻고(「어느 영역이 중요한가」) 끝낸다. 질문을 퍼붓지 않는다. 사람이 없는 실행이면 묻지 않고 캔 것만으로 간다.
5. **묶는다.** 신호를 devkit 의 기존 절에 맞춰 묶는다. `skills/mode/SKILL.md` 의 절, 원칙, 해당 스킬 중 맞는 곳이다. 그 사람에게 기본과 다른 구체 규칙이 있을 때만 절을 더한다. 「분명하게 말한다」는 절이 못 된다. 「짧은 문단. 비교는 표. 항목이 정말 나란할 때만 글머리.」는 된다.
6. 이 결과가 3단계 종합자의 입력이 된다. 종합자에게 검토자 셋 대신 조각 결과를 넘기고, 「반박되지 않은 기존 절은 지키고, 새 근거가 있는 절은 고치고, 정말 새 규칙에만 절을 더한다」를 덧붙인다.

지킬 것:

- 대화 하나에 맞추지 않는다. 여러 번 나온 것만 규칙으로 만든다.
- 꾸미지 않는다. 다른 스킬 내용을 다시 쓰거나, 비유를 지어내거나, 에이전트가 읽을 글을 멋 부려 쓰는 것은 비용만 든다. 할 일과 판단 기준만 쓴다.
- 다른 스킬은 붙여 넣지 말고 이름(`/devkit:<이름>`)이나 경로로 가리킨다. 사용자가 다른 곳에 둔 원칙 문서도 그렇다.
- 사람 이름 대신 「사용자」라고 쓴다.
- 억지 대칭을 만들지 않는다. 적을 진행 규칙이 없으면 그 절을 만들지 않는다.
- 평가는 점수 대신 사용자에게 「나 같나, 빠진 게 있나」를 보이는 것으로 한다. 그 확인이 5단계 승인과 같은 자리다.
