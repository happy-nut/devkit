---
name: formal-guard-bash
description: "hooks/guard-bash.py 의 merge_gate 가 \"바뀐 파일 있는지, 체크가 다 붙고 다 초록인지 본다. 'no checks reported'는 초록이 아니다\"라는 자기 docstring의 fail-closed 약속을 지키는지 전수 검사한다. merge_gate 를 고치거나, 그 호출부(gh pr merge 를 막는 조건)를 바꿀 때 돌린다."
---

# formal-guard-bash

`hooks/guard-bash.py` 의 `merge_gate(pr, cwd)` 가 검사하는 약속: 파일이 0개면 막고, 체크가 아직 붙지 않았거나 돌고 있거나 실패했으면 막는다. "no checks reported"는 체크가 아직 안 붙었을 수 있다는 뜻이라 초록으로 치지 않는다(docstring 원문). 이건 fail-closed 약속이다. gh 호출이 실패했거나 PR 나이를 몰라서 "아직 안 붙었을 수 있다"를 배제 못 하면, 허용(`None`)이 아니라 막아야(deny) 한다.

## 돌리는 법

```
python3 .claude/skills/formal-guard-bash/check_merge_gate.py
```

진짜 `merge_gate` 함수를 가져와서(코드를 베껴 모델링하지 않는다. `check_merge_gate.py` 가 `hooks/guard-bash.py` 를 직접 읽어 그 함수를 꺼내 쓴다), `files`(0개/1개 이상/응답에 키 없음) × `createdAt`(최근/오래됨/응답에 없음) × checks 신호(no_checks, pending-rc8, pending 문구, fail-rc1, fail 문구, pass) 55가지 조합과, gh 자체가 PATH 에 없는 경우를 더해 `fake gh` 를 PATH 에 꽂아 돌린다. 모든 조합에서 fail-closed 약속이 지켜지는지 본다.

끝에 0이 아닌 종료 코드와 "새 어긋남" 목록이 나오면 멈춘다. 그게 2단계(진짜 버그와 모델링 오류를 가른다)다.

## 알려진 어긋남 (지금 코드에 있고, 사용자가 시키지 않아 고치지 않은 것)

`check_merge_gate.py` 가 매번 그대로 보여 준다. 셋이다.

1. `gh` 명령 자체를 못 찾거나 실패하면(subprocess 예외) `merge_gate` 가 아무것도 확인하지 못했는데도 머지를 허용한다.
2. "no checks reported" 인데 `gh pr view` 응답에 `createdAt` 이 없으면(응답이 깨졌거나 그 필드가 빠지면), PR 이 얼마나 됐는지 몰라도 머지를 허용한다. `files` 가 빈 배열이든 응답에 키가 없든 똑같이 일어난다.

이 셋 다 "확인 못 함 → 허용"이라 docstring의 fail-closed 의도와 반대다. 제품 코드(`hooks/guard-bash.py`)는 사용자가 고치라고 하지 않으면 고치지 않는다.

## 범위와 한계

- `merge_gate` 함수 하나만 본다. `guard-bash.py` 의 다른 RULES(pytest 파이프 뒤 커밋) 는 덮지 않는다.
- gh 가 실제로 내는 JSON·텍스트 모양이 바뀌면(필드 이름, "no checks reported" 문구 등) 이 모델도 같이 낡는다. `/devkit:formal-setup` 을 다시 부르면 "유지"로 들어가 코드와 다시 맞춘다.
- 이 검사는 `merge_gate` 가 돌려주는 거부 사유 문자열의 "내용"은 보지 않는다. deny 인지 allow 인지만 본다.

## 동기화 커밋

`6ce0281e7e1020bab8802b5008840c2c5019f87a`. 이 커밋에서 `hooks/guard-bash.py` 를 읽고 위 모델을 맞췄다. 그 뒤 `hooks/guard-bash.py` 가 바뀌면(RULES 추가가 아니라 `merge_gate` 자체가 바뀌면) 이 스킬이 낡은 것이다. `check_merge_gate.py` 를 다시 돌려 새 코드를 설명하는지 보고, 확인한 새 커밋으로 이 줄을 옮긴다. `blocked` 면 옮기지 않는다.
