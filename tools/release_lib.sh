# shellcheck shell=bash
# Shared helpers for the release scripts. Source from a bash script that has already
# run `set -euo pipefail`.

# towncrier <args...>
#   The pinned towncrier. Single definition so the scripts and the workflows cannot drift
#   onto different versions.
towncrier() {
	uvx --from 'towncrier>=24,<26' towncrier "$@"
}

# resolve_version <arg>
#   <arg> is EITHER an explicit version (leading digit, optional leading "v"), e.g.
#   "4.0.0b1" / "v4.0.0", OR one or more space-separated bump components
#   (patch|minor|major|stable|alpha|beta|rc|post|dev), e.g. "patch" or "major beta".
#   Sets globals: CUR_VERSION, NEW_VERSION, and the array UV_ARGS (to pass to uv version).
#   Exits 1 with a clear message on an invalid value or a non-increasing version.
resolve_version() {
	local arg="$1" component
	CUR_VERSION="$(uv version --short)"

	if printf '%s' "$arg" | grep -qE '^v?[0-9]'; then
		UV_ARGS=("${arg#v}") # explicit version (drop an optional leading "v")
	else
		UV_ARGS=()
		for component in $arg; do UV_ARGS+=(--bump "$component"); done
	fi

	# uv validates the value (bad component / malformed version) and writes nothing here.
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
}
