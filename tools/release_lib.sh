# shellcheck shell=bash
# Shared helpers for the release scripts. Source from a bash script that has already
# run `set -euo pipefail`.

towncrier() {
	uvx --from 'towncrier>=24,<26' towncrier "$@"
}

resolve_version() {
	local arg="$1" component explicit=0
	CUR_VERSION="$(uv version --short)"

	if printf '%s' "$arg" | grep -qE '^v?[0-9]'; then
		UV_ARGS=("${arg#v}") # explicit version (drop an optional leading "v")
		explicit=1
	else
		UV_ARGS=()
		for component in $arg; do UV_ARGS+=(--bump "$component"); done
	fi

	if ! NEW_VERSION="$(uv version --dry-run "${UV_ARGS[@]}" --output-format json 2>/dev/null \
		| python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])' 2>/dev/null)" \
		|| [ -z "${NEW_VERSION}" ]; then
		{
			echo "✖ invalid version/bump: '${arg}'"
			echo "  bump:    patch | minor | major | stable | alpha | beta | rc  (combinable, e.g. 'major beta')"
			echo "  version: an explicit PEP 440 version, e.g. 4.0.0b1"
		} >&2
		exit 1
	fi

	# Monotonic guard: the target must be greater than the current version. Uses uv to get
	# `packaging` for a correct PEP 440 comparison; if that can't run, the guard is skipped
	# (the malformed check above still applies).
	if [ "$(uv run --no-project --with packaging python - "${CUR_VERSION}" "${NEW_VERSION}" 2>/dev/null <<'PY' || true
import sys
from packaging.version import Version
print("down" if Version(sys.argv[2]) <= Version(sys.argv[1]) else "ok")
PY
)" = "down" ]; then
		echo "✖ target version ${NEW_VERSION} is not greater than the current ${CUR_VERSION}" >&2
		exit 1
	fi

	# While a pre-release is pending, a bump may only continue that line (another pre-release)
	# or finish it (stable). Anything else leaves the pending final unreleased and its changelog
	# sections orphaned. An explicit version is an intentional override and is not checked.
	if [ "${explicit}" -eq 0 ] && printf '%s' "${CUR_VERSION}" | grep -qE '(a|b|rc)[0-9]+|\.dev[0-9]+'; then
		local cur_final new_final
		cur_final="$(release_final_of "${CUR_VERSION}")"
		new_final="$(release_final_of "${NEW_VERSION}")"
		if [ "${cur_final}" != "${new_final}" ]; then
			{
				echo "✖ ${CUR_VERSION} is a pre-release of ${cur_final}; '${arg}' targets ${NEW_VERSION} and would skip it."
				echo "  finish the line:  stable  (-> ${cur_final})"
				echo "  continue it:      alpha | beta | rc"
				echo "  or pass an explicit version to override this check."
			} >&2
			exit 1
		fi
	fi
}

release_final_of() {
	printf '%s' "${1#v}" | sed -E 's/((a|b|rc)[0-9]+|\.dev[0-9]+|\.post[0-9]+).*$//'
}

# has_news_fragments
#   0 = fragments to build, 1 = none, 2 = towncrier could not be asked. A build with no
#   fragments writes a content-less `.. changelog::` section, which the Sphinx directive
#   rejects under -W, so the caller must skip the build — but it must NOT mistake a broken
#   towncrier for an empty one. Matched in-shell rather than through `grep -q`, which exits on
#   the first match and SIGPIPEs its writer; under `pipefail` that made a large draft look empty.
has_news_fragments() {
	local draft
	draft="$(towncrier build --draft --version 0.0.0 2>/dev/null)" || return 2
	case "${draft}" in
	*".. change::"*) return 0 ;;
	*) return 1 ;;
	esac
}

is_final_version() {
	printf '%s' "$1" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(\.post[0-9]+)?$'
}

warn_review_notes() {
	printf '\n\033[1;33m⚠ Review the GitHub release notes before publishing — especially the "Other changes" section: not all of those entries belong in the final notes.\033[0m\n'
}
