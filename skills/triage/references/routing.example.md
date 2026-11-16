# 라우팅 지도 예시

이 파일을 팩 밖(예: `.claude/triage/routing.md`)에 복사하고 자리표시를 모두 바꾼다. 설정의 `routing.map_path` 가 그 사본을 가리키게 한다. 팩을 새로 받아도 사본은 덮이지 않아야 한다.

분류 스킬은 이 지도를 데이터로 다룬다. 경로 하나를 고르려면 보고나 원인 추적에서 나온 증거가 있어야 한다. 낱말이 맞는 것만으로는 부족하다.

```yaml
routes:
  - name: "billing-example"
    match:
      product_areas:
        - "billing-area-placeholder"
      code_paths:
        - "billing-code-path-placeholder"
      error_signatures:
        - "billing-error-placeholder"
    destination:
      slack_channel: "billing-channel-placeholder"
      tracker_team: "billing-team-placeholder"
    owners:
      - "billing-owner-placeholder"
    allow_feature_owner_ping: false

  - name: "desktop-example"
    match:
      product_areas:
        - "desktop-area-placeholder"
      code_paths:
        - "desktop-code-path-placeholder"
      error_signatures:
        - "desktop-error-placeholder"
    destination:
      slack_channel: "desktop-channel-placeholder"
      tracker_team: "desktop-team-placeholder"
    owners:
      - "desktop-owner-placeholder"
    allow_feature_owner_ping: false

fallback:
  destination: ""
  owners: []
  allow_feature_owner_ping: false

ping_policy:
  default: "off"
  allow:
    - "configured-feature-owner"
    - "confirmed-regression-author"
  deny:
    - "broad-on-call-group"
    - "unverified-owner"
```

## 규칙

- 맞지 않은 보고를 모두 받겠다는 팀이 하나 있을 때만 `fallback.destination` 을 채운다. 아니면 비운다.
- 오래 가는 제품 영역, 코드 경로, 에러 시그니처를 쓴다.
- 공개될 사본에 개인 데이터를 넣지 않는다.
- 공개될 예시에 날것의 사용자 ID 나 채널 ID 를 붙이지 않는다.
- 대상 팀이 동의하기 전까지 기능 담당자 호출은 꺼 둔다.
- 다른 곳으로 안내는 보고자에게 어디로 가면 되는지 말하는 것이다. 자동화는 다른 채널에 같이 올리지 않는다.
