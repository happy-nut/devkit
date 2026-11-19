# 재현용 기능 지도

재현할 수 있는 사용자 기능을 모두 지도에 둔다. 앱을 몰기 전에 맞는 기능 파일을 읽는다. 지도는 사용자 시점으로 쓴다. 내부 구조와 지금 코드 경로는 지도에 얼리지 말고 실행할 때 찾는다.

지도는 따로 만들지 않는다. `/dev:verify-setup` 이 만든 `<저장소>/.claude/skills/verify-<앱>/features/` 가 지도다. 모양(README 색인과 기능마다 파일 하나, H2 넷 `Sub-features`, `How to get to it (user POV)`, `Driving it with <장치>`, `Gotchas`)은 [`../../verify-setup/references/feature-map-example/README.md`](../../verify-setup/references/feature-map-example/README.md) 를 따른다. 이 문서는 재현에 더 필요한 칸을 그 네 절 어디에 채우는지만 정한다. 설정의 `control.feature_map_path` 가 그 폴더를 가리키게 한다. 이 예시를 고치지 말고 그 스킬의 기능 파일에 채운다. 그 폴더는 검증 스킬이 소유하므로 팩을 새로 받아도 덮이지 않는다.

## 기능마다 채울 칸

| 칸 | 둘 곳 |
|---|---|
| 사용자에게 보이는 목적 한 줄 | H1 아래 문단 |
| 사용자가 가는 길: 누르는 경로(`<화면> -> <메뉴·탭·패널> -> <컨트롤>`), 단축키(없으면 「없음」) | `How to get to it (user POV)` |
| 어댑터 동작: `<어댑터 동작>` 에 `<입력>` 을 주면 `<보이는 결과>` | `Driving it with <장치>` 의 라벨 붙은 글머리 |
| 되돌리기: 새 상태로 돌아가는 법 | `Driving it with <장치>` 의 `Reset:` 글머리 |
| 안정된 선택자: 역할과 접근 가능한 이름, ARIA 관계, `data-component` 나 목적을 이름에 담은 data 속성 | `Driving it with <장치>` 의 `Selectors:` 글머리 |
| 다룰 상태: 기본, hover, focus-visible, active, disabled, loading, empty, error, selected, open, expanded, 기능 고유 변형. 해당 없는 상태는 표시 | `Sub-features` 의 ID 마다 한 줄, 또는 `Driving it with <장치>` 의 `States:` 글머리 |
| 전제와 준비: 인증(계정 상태), 데이터(픽스처), 권한(역할), 플래그(없으면 「없음」), 서비스(필요한 가용성) | `Driving it with <장치>` 의 `Preconditions:` |
| 증거와 교차 확인: 스크린샷(앱 정체, 기능, 가르는 상태), 영상(들어가는 경로, 조작, 최종 상태), 교차 확인(UI 를 확인하는 읽기 전용 상태나 값) | `Driving it with <장치>` 의 `Evidence:` 글머리 |
| 함정: 알려진 막다른 길이나 잘못된 표면, 안전한 환경 옮기기 | `Gotchas` |

생성된 CSS 나 StyleX 같은 CSS-in-JS 클래스, 동적 해시, 자식 순번, 깨지기 쉬운 DOM 위치는 선택자로 절대 쓰지 않는다.

## 가상 예시

아래 기능은 가상의 할 일 앱 것이다. 예시일 뿐 필요한 기능 목록이 아니다. 장치 이름은 `control-tasks` 로 둔다.

### 로그인

```markdown
# Sign in

사용자가 할 일 앱에 들어간다.

## Sub-features

- `SI1` **default**: 기본, focus-visible 상태.
- `SI2` **submitting**: 제출 중, disabled, loading 상태.
- `SI3` **sign-in error**: error 상태.

## How to get to it (user POV)

- 앱을 열고 `Sign in` 을 고른다. 단축키 없음.

## Driving it with control-tasks

Preconditions: 버려도 되는 계정, 인증 서비스가 떠 있음. 플래그 없음.

- Act: `open_app`, `click Sign in`, `fill credentials`, `click Continue`. Observe: 할 일 목록이 열린다.
- Reset: 로그아웃하고 버려도 되는 세션을 지운다.
- Selectors: 버튼 `Sign in`, 입력 칸 `Email` 과 `Password`, `data-component="sign-in-form"`.
- Evidence: 첫 화면부터 할 일 목록까지 녹화. 읽기 전용 세션 상태를 확인한다.

## Gotchas

- 홍보 페이지는 잘못된 표면이다.
- 인증 서비스가 없으면 막힘이다.
```

### 할 일 목록과 상세

```markdown
# Task list and detail

사용자가 할 일을 훑고 하나를 연다.

## Sub-features

- `IL1` **list states**: loading, empty, error 상태.
- `IL2` **item selection**: selected, open, expanded 상태.

## How to get to it (user POV)

- `Items` 탭을 열고 줄 하나를 고른다.

## Driving it with control-tasks

Preconditions: 이름 붙은 픽스처 할 일, 읽기 권한, 할 일 서비스가 떠 있음.

- Act: `select_tab Items`, `click <픽스처 할 일>`. Observe: 그 할 일의 상세가 열린다.
- Reset: 상세를 닫고 선택을 지운다.
- Selectors: 이름이 `Items` 인 탭과 목록, 픽스처 이름의 줄, `data-component="item-detail"`.
- Evidence: 선택과 맞는 상세 제목을 보인다. 선택된 할 일 ID 를 확인한다.

## Gotchas

- 검색 결과는 비슷해 보이지만 다른 경로다.
```

### 할 일 편집기

```markdown
# Task editor

사용자가 할 일을 만들거나 고친다.

## Sub-features

- `IE1` **editing**: 기본, focus-visible, dirty 상태.
- `IE2` **saving**: validating, disabled, saving 상태.
- `IE3` **save result**: error, success 상태.

## How to get to it (user POV)

- 상세에서 `Edit` 을 고르거나 목록에서 `New item` 을 고른다.

## Driving it with control-tasks

Preconditions: 고칠 수 있는 픽스처, 쓰기 권한, 저장 서비스가 떠 있음.

- Act: `click Edit`, `fill <칸>`, `click Save`. Observe: 상세가 바뀐다.
- Reset: 픽스처를 되돌린다.
- Selectors: 버튼 `Edit`, `New item`, `Save`, 폼 `Item editor`, 라벨에 이어진 칸.
- Evidence: 칸이 바뀌는 것부터 바뀐 상세까지 보인다. 저장된 값을 읽기 전용으로 확인한다.

## Gotchas

- 폼 상태를 주입하지 않는다.
- 읽기 전용 상세 칸은 편집기가 아니다.
```

### 설정

```markdown
# Settings

사용자가 개인 선호를 바꾼다.

## Sub-features

- `ST1` **tab switching**: closed, open, selected 상태.
- `ST2` **tab focus**: focus-visible, disabled 상태.
- `ST3` **tab loading**: loading, error 상태.

## How to get to it (user POV)

- 프로필 메뉴를 열고 `Settings` 를 고른다.

## Driving it with control-tasks

Preconditions: 로그인한 시험 계정, 알려진 선호 값, 선호 서비스가 떠 있음.

- Act: `open_menu Profile`, `click Settings`, `toggle <선호>`. Observe: 컨트롤이 바뀐다.
- Reset: 처음 선호 값으로 되돌린다.
- Selectors: 버튼 `Profile`, 메뉴 항목 `Settings`, 영역 `Settings`, 목적을 이름에 담은 선호 속성.
- Evidence: 메뉴 경로와 최종 컨트롤 상태를 보인다. 선호 값을 읽기 전용으로 확인한다.

## Gotchas

- 운영체제 설정은 다른 표면이다.
```

## 완결 점검

- 재현할 수 있는 사용자 기능마다 파일이 있다.
- 파일마다 사용자 경로, 어댑터 동작, 되돌리기를 이름 댄다.
- 선택자는 역할, 이름, ARIA, 안정된 컴포넌트 표지, 목적을 이름에 담은 속성을 쓴다.
- 생성된 클래스나 DOM 위치를 쓰는 선택자가 없다.
- 관련된 조작, loading, empty, error, selected, expanded 상태를 덮는다.
- 인증, 픽스처, 권한, 플래그, 서비스가 명시돼 있다.
- 스크린샷, 영상, 바탕 교차 확인 요구가 명시돼 있다.
- 잘못된 표면, 막다른 길, 안전한 환경 옮기기가 적혀 있다.
- 구현 세부는 실행할 때 찾는 것으로 남아 있다.
