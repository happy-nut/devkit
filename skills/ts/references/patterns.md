# TypeScript 패턴

`SKILL.md` 의 규칙마다 코드 예시. 바탕 원칙은 언어와 무관하다. 「principles.md 의 Type System Discipline」과 「principles.md 의 Boundary Discipline」(경로 `../../mode/principles.md`)을 본다.

## 브랜드 타입

원시값을 브랜드해 섞이지 않게 한다. 경계에서 한 번 검증한다. 아래쪽 코드는 타입을 믿는다.

```ts
type AgentId = string & { readonly __brand: "AgentId" };

function isAgentId(input: string): input is AgentId {
  return isUUID(input);
}

function parseAgentId(input: string): AgentId {
  if (!isAgentId(input)) throw new Error(`Invalid agent id: ${input}`);
  return input;
}

function focusAgent(id: AgentId): void {
  /* input is trusted */
}
```

`readonly __brand: 'X'` 모양을 맞춘다. 새 관례를 지어내지 않는다.

## 판별 유니온

변형을 리터럴 판별자로 모델링한다. 모든 변형이 같은 필드 이름을 쓰고 변형마다 값이 다르므로 불가능한 조합을 표현할 수 없다.

```ts
// Don't. Boolean + optionals lets contradictory states exist.
type DiffState = { loading: boolean; diff?: GitDiff; error?: string };

// Do. Only valid states exist.
type DiffState =
  | { kind: "loading" }
  | { kind: "ready"; diff: GitDiff }
  | { kind: "error"; error: string };
```

판별자 이름 하나(`kind`, `type`, `tag`)를 골라 지킨다.

## 구성으로 모델링

느슨한 타입을 런타임 검사로 묶지 말고, 모두 올바른 부품으로 타입을 짓는다.

비어 있지 않음, 가변 튜플로:

```ts
type NonEmpty<T> = [T, ...T[]];

// Don't: T[] plus a length check every caller must repeat
function pickWinner(entries: string[]): string {
  if (entries.length === 0) throw new Error("no entries");
  return entries[Math.floor(Math.random() * entries.length)];
}

// Do: an empty value of the type can't exist
function pickWinner(entries: NonEmpty<string>): string {
  return entries[Math.floor(Math.random() * entries.length)];
}
```

평범한 `T[]` 가 들어오는 곳에서는 가드로 한 번 좁힌다. 그 뒤로는 사실이 타입에 실려 다닌다.

```ts
const isNonEmpty = <T>(arr: T[]): arr is NonEmpty<T> => arr.length > 0;
```

짝수 길이, 쌍으로:

```ts
type Pairs<T> = [T, T][];
```

시간 범위, 시작과 길이로:

```ts
// Don't: a comment holds the invariant
type TimeRange = { start: Date; end: Date }; // start <= end

// Do: a negative range can't be written; derive end when needed
type TimeRange = { start: Date; durationMs: number };
```

`durationMs` 는 평범한 number 로 둔다. 길이가 와야 할 자리에 날 number 가 들어갈 수 있을 때만 (브랜드 타입대로) 브랜드한다. 반사적으로 하지 않는다. 나쁜 상태를 만들 수 없는 표현을 고르고, 필요한 읽기는 그 위에 얹는다(`pairs.flat()`, `rangeEnd()` 도우미).

## 가장 단순한 total 타입

모든 것을 강화하지 않는다. 모든 연산이 total 이면 `T[]` 를 둔다.

```ts
const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0); // [] is 0, fine
```

느슨한 타입이 쓰는 자리에서 거짓말을 강요할 때 강화한다. 티는 `!`, `arr[0] as T`, 「절대 안 일어남」 throw 다.

```ts
// Don't: partiality smuggled past the compiler
function newestSession(sessions: Session[]): Session {
  return sessions.at(0)!;
}

// Do: strengthen the input; the assertion disappears
function newestSession(sessions: NonEmpty<Session>): Session {
  return sessions[0];
}
```

결과를 `Session | undefined` 로 약하게 하는 것이 다른 total 시그니처다.

## `any` 대신 `unknown`

바깥 데이터는 언제나 `unknown` 이다. 쓰기 전에 좁힌다.

```ts
// Don't
function handle(input: any) {
  return input.foo.bar;
}

// Do
function handle(input: unknown) {
  if (typeof input === "object" && input !== null && "foo" in input) {
    // narrowed; compiler verifies access
  }
}
```

바깥 출처: RPC 페이로드, `JSON.parse`, `postMessage`, IPC, 파일 내용, 환경 변수, 데이터베이스 결과.

## 손 가드보다 스키마 먼저

바깥 데이터에 속성 하나하나 보는 타입 가드를 쓰기 전에 저장소의 런타임 스키마 라이브러리와 기존 스키마를 찾는다. 스키마 하나가 검증을 맡고 TypeScript 타입은 거기서 끌어낸다. 따로 놀 수 있는 스키마, 중복 인터페이스, 가드 셋을 함께 관리하지 않는다.

```ts
import { z } from "zod";

const UserSchema = z.object({
  id: z.string().uuid(),
  role: z.enum(["admin", "member"]),
});

type User = z.infer<typeof UserSchema>;

function parseUser(input: unknown): User {
  return UserSchema.parse(input);
}
```

실패가 예상되는 갈래면 `safeParse` 를 쓴다. 저장소가 다른 스키마 라이브러리를 쓰면 그쪽 추론 도우미를 쓴다. 가드 하나 때문에 새 스키마 의존성을 들이지 않는다. 이 규칙은 코드베이스가 이미 믿는 스키마 체계를 쓰라는 것이다.

## `as` 캐스트 금지

모든 `as` 는 런타임 오류가 될 수 있다. 타입 체계가 주장을 검증한 뒤에만 캐스트한다.

```ts
import { z } from "zod";

// Don't
const user = data as User;

// Don't
function isUser(data: unknown): data is User {
  return typeof data === "object" && data !== null && "id" in data;
}

// Do
const userSchema = z.object({ id: z.string(), name: z.string() });
type User = z.infer<typeof userSchema>;

function parseUser(data: unknown): User {
  return userSchema.parse(data);
}
```

타입이 먼저 있으면 검증기에 그것이 증명하는 타입을 붙인다. 그러면 검증기가 타입보다 덜 증명할 때 컴파일러가 거부한다. 아래 객체에서 `name` 을 빼면 대입이 컴파일되지 않는다.

```ts
type User = { id: string; name: string };

const userSchema: z.ZodType<User> = z.object({ id: z.string(), name: z.string() });
```

기존 코드에서 `as` 를 걷어낼 때는 TypeScript 가 왜 추론하지 못하는지 찾는다.

- 판별자가 없다: 넣고 판별 유니온으로 바꾼다.
- 출처 타입이 너무 넓다(`Record<string, unknown>` 등): 좁힌다.
- 타입 없는 경계: 그 모양을 맡은 스키마로 파싱한다. 스키마가 없는 곳에만 새로 만든다.
- 정말 표현할 수 없다: 브랜드 타입이나 `satisfies` 를 쓴다.

## 좁히기 순서

좋은 것부터 마지막 수단까지:

1. **판별 유니온 switch·if.** 컴파일러가 알아서 좁힌다.
2. **`in` 연산자.** `"key" in obj` 가 그 키가 있는 변형으로 좁힌다.
3. **`typeof`·`instanceof`.** 원시값과 클래스 인스턴스.
4. **사용자 정의 타입 가드.** 위로 안 될 때.
5. **`as` 캐스트.** 검증 뒤에만.

```ts
function area(s: Shape): number {
  if ("radius" in s) return Math.PI * s.radius ** 2; // narrowed to circle
  return s.width * s.height; // narrowed to rect
}
```

## 타입 가드

가드는 주장을 실제로 검증해야 한다. 거짓말하는 가드는 `as` 보다 나쁘다.

```ts
function isCircle(s: Shape): s is Shape & { kind: "circle" } {
  return s.kind === "circle";
}
```

할 수 있으면 판별자로 좁힌다.

## 완전성

default 갈래에서 판별 대상을 `never` 타입 지역 변수에 넣는다.

```ts
// Value-returning switch
function area(s: Shape): number {
  switch (s.kind) {
    case "circle":
      return Math.PI * s.radius ** 2;
    case "rect":
      return s.width * s.height;
    default: {
      const _exhaustive: never = s;
      return _exhaustive;
    }
  }
}

// Void switch
function handle(s: Shape): void {
  switch (s.kind) {
    case "circle":
      drawCircle(s);
      break;
    case "rect":
      drawRect(s);
      break;
    default: {
      const _exhaustive: never = s;
      void _exhaustive;
    }
  }
}
```

값을 돌려주는 switch 는 return 꼴, 문장 switch 는 void 꼴.

## `as` 대신 `satisfies`

`satisfies` 는 리터럴 타입을 넓히지 않고 검증한다.

```ts
// Don't. Widens, loses literal types.
const config = { theme: "dark", cols: 3 } as Config;

// Do. Validates AND preserves literal types.
const config = { theme: "dark", cols: 3 } satisfies Config;
// config.theme is "dark" (literal), not string
```

## 경계 검증

데이터가 들어오는 곳에서 한 번 검증한다. 안쪽에서는 타입을 믿는다. 「principles.md 의 Boundary Discipline」을 본다.

- **와이어 포맷**(proto, JSON-RPC): `ignoreUnknownFields` 로 파싱해 앞으로 호환되는 변경이 옛 클라이언트를 깨지 않게 한다.
- **저장된 JSON:** 버전이 붙은 덩어리, 파싱을 try/catch 로 감싼다.
- **호출 사슬 깊은 곳에서 다시 검증하지 않는다.**

## 스키마에서 나온 타입

`.proto`, OpenAPI 명세, GraphQL 스키마, 데이터베이스 마이그레이션이 이미 모양을 정했으면 중복하지 말고 생성된 타입에서 끌어낸다.

```ts
// Don't. Duplicate shape, drifts when the schema changes.
type CheckSummary = {
  totalCount: number;
  checks: { name: string; status: string }[];
};
function renderChecks(s: CheckSummary) {
  /* ... */
}

// Do. Derive from the generated schema type.
import type { ChecksMessage } from "<generated module>";
function renderChecks(s: Pick<ChecksMessage, "totalCount" | "checks">) {
  /* ... */
}
```

새 인터페이스를 쓰기 전에 `Pick`, `Omit`, `Parameters`, `ReturnType`, `Awaited`, `typeof` 를 먼저 쓴다.

## 객체 인자

```ts
// Don't. Swap two args, still compiles.
openFile(uri, {
  startLineNumber: 10,
  startColumn: 1,
  endLineNumber: 10,
  endColumn: 1,
});

// Do. Order-independent, self-documenting.
openFile({
  uri,
  selection: {
    startLineNumber: 10,
    startColumn: 1,
    endLineNumber: 10,
    endColumn: 1,
  },
});
```

핫 패스는 예외다. 프레임마다 그리기, 토크나이저, 파서, 할당 비용이 중요한 빡빡한 반복.
