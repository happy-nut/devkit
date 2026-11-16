# 노트 찾기

사용자는 제목이나 본문 글로 노트를 찾고, 맞는 노트를 열어 보고, 결과 없음과 검색 불가를 구분할 수 있다.

## Sub-features

- `search-open` 은 지원하는 브라우저 진입점마다 검색을 연다.
- `search-match` 는 노트 데이터를 바꾸지 않고 제목·본문이 맞는 것을 돌려준다.
- `search-open-result` 는 결과를 노트 편집기로 연다.
- `search-empty` 는 맞는 것이 없는 검색어에 완결된 빈 상태를 보인다.
- `search-clear` 는 검색어를 지우고 최근 노트 화면으로 돌아간다.
- `search-cli` 는 터미널에서 같은 결과를 돌려준다.

## How to get to it (user POV)

- 브라우저 도구 막대에서 `Search` 단추를 누른다.
- 입력 칸 밖에 초점이 있을 때 브라우저에서 `/` 를 누른다.
- 터미널에서 `notes search <query>` 를 실행한다.

## Driving it with control-notes

Preconditions:

- Notes 가 `http://127.0.0.1:4173` 에서 정상이다.
- 버려도 되는 데이터 폴더에 본문이 `Draft budget` 인 `Quarterly plan` 이 있다.
- `control-notes doctor` 가 기대한 URL 과 데이터 폴더를 보고한다.

- **도구 막대 진입.** `Search` 단추를 누른다. `control-notes browser click --role button --name "Search"` 를 실행한다. 이름이 `Search notes` 인 대화상자가 나타나고 검색 칸에 초점이 있다.
- **키보드 진입.** 대화상자를 닫고, 페이지에 초점을 두고, `/` 를 누른다. `control-notes browser press --key "/"` 를 실행한다. 같은 대화상자가 나타나고 페이지에 빗금이 들어가지 않는다.
- **제목 일치.** `quarterly` 를 친다. `control-notes browser fill --role searchbox --name "Search notes" --value "quarterly"` 를 실행한다. `Search results` 목록에 `Quarterly plan` 이 있고 `Grocery list` 는 없다.
- **본문 일치.** 검색어를 `budget` 으로 바꾼다. `control-notes browser fill --role searchbox --name "Search notes" --value "budget"` 를 실행한다. `Quarterly plan` 결과가 본문 일치 발췌와 함께 남는다.
- **결과 열기.** `Quarterly plan` 을 누른다. `control-notes browser click --role link --name "Quarterly plan"` 을 실행한다. 대화상자가 닫히고 편집기 제목이 `Quarterly plan` 이다.
- **빈 상태.** 검색을 다시 열고 `volcano` 를 넣는다. `control-notes browser fill --role searchbox --name "Search notes" --value "volcano"` 를 실행한다. 검색이 끝난 뒤 이름이 `No matching notes` 인 상태가 나타난다.
- **검색어 지우기.** `Clear search` 를 누른다. `control-notes browser click --role button --name "Clear search"` 를 실행한다. 검색 칸이 비고 `Recent notes` 영역이 결과 목록을 대신한다.
- **CLI 일치.** 터미널에서 찾는다. `control-notes cli -- notes search "quarterly" --format json` 을 실행한다. 종료 코드 `0` 이고 stdout 에 제목이 `Quarterly plan` 인 객체 하나가 있다.
- **CLI 불일치.** 없는 값을 찾는다. `control-notes cli -- notes search "volcano" --format json` 을 실행한다. 종료 코드 `0` 이고 stdout 이 `[]` 다.
- **증명.** 결과가 찬 상태를 잡는다. `control-notes browser snapshot --aria --path artifacts/search/results.aria.txt` 와 `control-notes browser screenshot --path artifacts/search/results.png` 를 실행한다. 두 산출물 모두 Notes, 검색어, `Quarterly plan` 을 보여 준다.

## Gotchas

- 편집기나 검색 칸에 초점이 있을 때 `/` 를 누르면 검색이 열리지 않고 글자가 들어간다.
- 결과는 잠깐의 디바운스 뒤에 바뀐다. 정해진 시간만큼 자지 말고 결과 목록이나 빈 상태를 기다린다.
- 사용자가 `Include archived` 를 켜지 않으면 보관한 노트는 빠진다.
- CLI 기본 출력은 사람용이다. 안정된 확인에는 `--format json` 을 쓴다.
- 결과를 열면 브라우저 상태가 바뀐다. 다른 검색어를 증명하기 전에 검색을 다시 연다.
