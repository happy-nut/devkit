#!/usr/bin/env bash
# 결정 기록(TSV)에 한 줄을 더한다.
# 쓰는 법: log.sh <기록 파일> <phase> <decision> <why> <evidence> <result>
set -euo pipefail

if [ "$#" -ne 6 ]; then
	printf 'usage: log.sh <logfile> <phase> <decision> <why> <evidence> <result>\n' >&2
	exit 1
fi

logfile="$1"
shift

logdir="$(dirname "$logfile")"
if [ -n "$logdir" ] && [ "$logdir" != "." ] && [ ! -d "$logdir" ]; then
	mkdir -p "$logdir"
fi

# `>` 가 아니라 `>>` 로 쓴다. 네트워크 마운트에서는 있는 파일도 비었다고 나올 수 있다.
# 그때 잃는 것은 헤더 한 줄 중복이지 기록 행이 아니다.
if [ ! -s "$logfile" ]; then
	printf 'ts\tphase\tdecision\twhy\tevidence\tresult\n' >> "$logfile"
fi

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# 셀이 한 줄로 남게 탭·줄바꿈·CR 을 공백으로 바꾼다. 스프레드시트가 수식으로 읽는
# 첫 글자(=, +, -, @)로 시작하는 셀 앞에는 작은따옴표를 붙인다. PR 제목, 파일 이름,
# 생성된 글 같은 바깥 입력이 리뷰어가 파일을 열 때 수식으로 실행되지 않게 한다.
clean() {
	local v
	v=$(printf '%s' "$1" | tr '\t\n\r' '   ')
	case "$v" in
		=*|+*|-*|@*) printf "'%s" "$v" ;;
		*) printf '%s' "$v" ;;
	esac
}
printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
	"$ts" "$(clean "$1")" "$(clean "$2")" "$(clean "$3")" "$(clean "$4")" "$(clean "$5")" \
	>> "$logfile"
