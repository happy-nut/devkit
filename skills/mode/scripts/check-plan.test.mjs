import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { test } from "node:test";
import assert from "node:assert/strict";

const checker = join(dirname(fileURLToPath(import.meta.url)), "check-plan.mjs");
const rule = "테스트만으로는 검증이 아니다. PR 은 단위·실사용·성능 칸이 모두 체크돼야 검증된 것이다.";

const validPlan = `# 예시

## 읽는 법
칸 하나는 일 하나다. 칸마다 증거를 적는다. 증거가 있을 때만 칸을 체크한다. playbooks/ 를 본다.
${rule}

## 프로그램 체크리스트
### 프로그램 준비
### 담당 띄우기
### PR 절차
### 판정과 머지
### 부팅 절차
\`git show origin/main:\` /loop 1h 상태 메시지

## PR 1
**의존.** 없음.
**파일.**
- [ ] 한다.
**만들 것.**
- [ ] 한다.
**보이는 것.**
- [ ] 한다.
**검증, 단위.** ${rule}
- [ ] 확인한다.
**검증, 실사용.** ${rule} 레인 열 개를 \`sonnet\` 로 PR head 에서 돌린다.
${Array.from({ length: 10 }, (_, i) => `- [ ] 레인 ${i + 1}. \`lane-${i + 1}.png\` 를 저장한다. 통과 조건은 증거가 있는 것.`).join("\n")}
**검증, 성능.** ${rule}
- [ ] 지표. 적었다.
- [ ] 측정. 적었다.
- [ ] 기준선. 적었다.
- [ ] 규칙. 적었다.
**리뷰 관문.** 없음.
**머지.**
- [ ] 승인되면 머지한다.

## 프로그램 닫기
닫는다.

## 부록 A. 프로토타입 증거
적었다.
`;

const runPlan = (example, expectedExit) => {
	const directory = mkdtempSync(join(tmpdir(), "check-plan-test-"));
	const file = join(directory, "plan.md");
	writeFileSync(file, validPlan + example);
	try {
		const result = spawnSync("node", [checker, file], { encoding: "utf8" });
		assert.equal(result.status, expectedExit, result.stdout + result.stderr);
		return result;
	} finally {
		rmSync(directory, { recursive: true, force: true });
	}
};

test("valid plan passes and reports the PR section", () => {
	const result = runPlan("", 0);
	assert.match(result.stdout, /PR 1  칸=19/);
	assert.match(result.stdout, /PR 절 1개, 문제 0개/);
});

test("missing lane, perf item, and rule are reported", () => {
	const broken = validPlan
		.replace("- [ ] 레인 10. `lane-10.png` 를 저장한다. 통과 조건은 증거가 있는 것.\n", "")
		.replace("- [ ] 기준선. 적었다.\n", "")
		.replace(`**검증, 단위.** ${rule}`, "**검증, 단위.**");
	const directory = mkdtempSync(join(tmpdir(), "check-plan-test-"));
	const file = join(directory, "plan.md");
	writeFileSync(file, broken);
	try {
		const result = spawnSync("node", [checker, file], { encoding: "utf8" });
		assert.equal(result.status, 1);
		assert.match(result.stderr, /레인이 \[1,2,3,4,5,6,7,8,9\]/);
		assert.match(result.stderr, /성능 칸이 \[지표\., 측정\., 규칙\.\]/);
		assert.match(result.stderr, /검증, 단위\. 가 규칙 문장으로 시작하지 않음/);
	} finally {
		rmSync(directory, { recursive: true, force: true });
	}
});

test("accepts ordinary, indented, and longer closing fences", () => {
	for (const indent of ["", " ", "  ", "   "])
		runPlan(`${indent}\`\`\`markdown\n## 예시일 뿐\n${indent}\`\`\`\n`, 0);
	runPlan("```markdown\n## 예시일 뿐\n````\n", 0);
});

test("accepts nested backticks and tilde info strings", () => {
	runPlan("````markdown\n```markdown\n## 예시일 뿐\n```\n````\n", 0);
	runPlan("~~~markdown `info`\n## 예시일 뿐\n ~~~\n", 0);
});

test("keeps mismatched, shorter, and suffixed closers inside the fence", () => {
	runPlan("````markdown\n~~~\n## 예시일 뿐\n````\n", 0);
	runPlan("````markdown\n```\n## 예시일 뿐\n````\n", 0);
	runPlan("````markdown\n``` info\n## 예시일 뿐\n````\n", 0);
});

test("rejects headings and prose outside a proper close", () => {
	for (const suffix of ["  ", "\t"]) {
		const heading = runPlan(`\`\`\`markdown\n## 예시일 뿐\n\`\`\`${suffix}\n## 예시일 뿐\n`, 1);
		assert.ok(heading.stderr.includes('프로그램 닫기 뒤 "## 예시일 뿐" 가 부록이 아님'));
	}
	const prose = runPlan("```markdown\n코드 안의 쌍점: 괜찮다\n```\n본문의 쌍점: 안 된다.\n", 1);
	assert.ok(prose.stderr.includes("문장 중간 쌍점"));
});

test("rejects backtick info strings containing a backtick", () => {
	const result = runPlan("```markdown `invalid`\n## 예시일 뿐\n```\n", 1);
	assert.ok(result.stderr.includes('프로그램 닫기 뒤 "## 예시일 뿐" 가 부록이 아님'));
});

test("ignores prose punctuation inside matching multi-backtick code spans", () => {
	for (const count of [2, 3, 4]) {
		const delimiter = "`".repeat(count);
		runPlan(`${delimiter}echo \`x\`: \u201cquoted\u201d \u2014 example${delimiter} 를 쓴다.\n`, 0);
	}
});

test("checks prose following a multi-backtick span and unmatched delimiters", () => {
	const outside = runPlan("``echo `x`: y`` 를 쓴다. 나쁨: 본문.\n", 1);
	assert.ok(outside.stderr.includes("문장 중간 쌍점"));
	const unmatched = runPlan("``unclosed: bad` 여기.\n", 1);
	assert.ok(unmatched.stderr.includes("문장 중간 쌍점"));
});

test("long dash and curly quotes in prose are reported", () => {
	const result = runPlan("본문 \u2014 대시와 \u201c따옴표\u201d.\n", 1);
	assert.ok(result.stderr.includes("긴 대시"));
	assert.ok(result.stderr.includes("곡선 따옴표"));
});
