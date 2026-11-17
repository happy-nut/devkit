#!/usr/bin/env bash
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

append_header_if_empty() {
	if [ ! -s "$1" ]; then
		printf 'ts\tphase\tdecision\twhy\tevidence\tresult\n' >> "$1"
	fi
}
append_header_if_empty "$logfile"

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# 스프레드시트는 =, +, -, @ 로 시작하는 셀을 수식으로 실행한다(CSV injection).
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
