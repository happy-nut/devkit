# Create a note

사용자는 브라우저나 CLI 로 제목 있는 노트를 저장하고, 덜 쓴 초안을 취소하고, 저장된 노트를 다른 사용자 화면에서 다시 확인할 수 있다.

## Sub-features

- `create-open` **open editor**: 브라우저 진입점마다 빈 편집기를 연다.
- `create-save` **save**: 제목과 본문을 저장한다.
- `create-cancel` **discard draft**: 덜 쓴 브라우저 초안을 버린다.
- `create-cli` **create from CLI**: 터미널에서 같은 모양의 노트를 만든다.

## How to get to it (user POV)

- 브라우저 도구 막대에서 `New note` 단추를 누른다.
- 입력 칸 밖에 초점이 있을 때 브라우저에서 `n` 을 누른다.
- 터미널에서 `notes create --title <title> --body <body>` 를 실행한다.

## Driving it with control-notes

Preconditions:

- Notes 가 `http://127.0.0.1:4173` 에서 정상이다.
- 제목이 `Release checklist` 인 노트가 없다.
- `control-notes doctor` 가 기대한 URL 과 버려도 되는 데이터 폴더를 보고한다.

- **편집기 열기.** `New note` 를 누른다. `control-notes browser click --role button --name "New note"` 를 실행한다. 이름이 `Note editor` 인 폼이 나타나고 `Title` 입력 칸에 초점이 있다.
- **내용 넣기.** 제목과 본문을 친다. `control-notes browser fill --role textbox --name "Title" --value "Release checklist"` 와 `control-notes browser fill --role textbox --name "Body" --value "Tag and publish"` 를 실행한다. `Save note` 단추가 켜진다.
- **저장.** `Save note` 를 누른다. `control-notes browser click --role button --name "Save note"` 를 실행한다. 이름이 `Note saved` 인 상태가 나타나고 제목이 `Release checklist` 로 보인다.
- **유지 확인.** 노트 목록으로 돌아가 노트를 다시 연다. `control-notes browser click --role link --name "All notes"` 와 `control-notes browser click --role link --name "Release checklist"` 를 실행한다. 편집기에 저장한 두 값이 보인다.
- **초안 취소.** 새 노트를 열고 `Discard me` 를 넣고 `Cancel` 을 누른다. `control-notes browser click --role button --name "New note"`, `control-notes browser fill --role textbox --name "Title" --value "Discard me"`, `control-notes browser click --role button --name "Cancel"` 을 실행한다. 노트 목록으로 돌아오고 `Discard me` 링크가 없다.
- **CLI 진입.** 두 번째 노트를 만든다. `control-notes cli -- notes create --title "CLI note" --body "Created from terminal" --format json` 을 실행한다. 종료 코드 `0` 이고 stdout 에 새 노트 ID 와 제목이 있다.
- **증명.** `All notes` 에서 저장한 두 노트를 다시 연다. `control-notes browser snapshot --aria --path artifacts/create-note/list.aria.txt` 와 `control-notes browser screenshot --path artifacts/create-note/list.png` 를 실행한다. 산출물에 `Release checklist` 와 `CLI note` 가 보인다.

## Gotchas

- 입력 칸에 초점이 있을 때 `n` 을 누르면 새 편집기가 열리지 않고 글자가 들어간다.
- 저장할 때 제목 앞뒤 공백이 잘린다. 초안 입력값이 아니라 그려진 제목을 확인한다.
- 저장 상태 표시만으로는 증명이 안 된다. 목록에서 노트를 다시 연다.
- 정리할 때 `Release checklist` 와 `CLI note` 를 지우되 증명 산출물은 남긴다.
