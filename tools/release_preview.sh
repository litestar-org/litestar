#!/usr/bin/env bash
# Release readiness check. Writes NOTHING.
set -euo pipefail

ARG="${1:-patch}"
BASE="${2:-}"
# shellcheck source=tools/release_lib.sh
source "$(dirname "$0")/release_lib.sh"
fail=0

check() { # check "<label>" <exit-status>
	if [ "$2" -eq 0 ]; then printf '  \033[32m✅\033[0m %s\n' "$1"; else printf '  \033[31m❌\033[0m %s\n' "$1"; fail=1; fi
}

resolve_version "${ARG}" # sets CUR_VERSION, NEW_VERSION, UV_ARGS
TAG="v${NEW_VERSION}"

printf '\nRelease preview: %s --(%s)--> %s\n\n' "$CUR_VERSION" "$ARG" "$NEW_VERSION"
echo "Readiness checks"

if ! git diff --quiet || ! git diff --cached --quiet; then
	check "working tree clean" 1
else
	check "working tree clean" 0
fi

uv lock --check >/dev/null 2>&1
check "uv.lock up to date" $?

if git rev-parse -q --verify "refs/tags/${TAG}" >/dev/null 2>&1 \
	|| git ls-remote --exit-code --tags origin "${TAG}" >/dev/null 2>&1; then
	check "tag ${TAG} does not exist yet" 1
else
	check "tag ${TAG} does not exist yet" 0
fi

if CHANGELOG_PREVIEW="$(towncrier build --draft --version "${NEW_VERSION}" 2>/dev/null)"; then
	check "news fragments parse" 0
else
	check "news fragments parse" 1
	CHANGELOG_PREVIEW="(towncrier build --draft failed)"
fi

FRAGMENTS="$(printf '%s' "${CHANGELOG_PREVIEW}" | grep -c '\.\. change::' || true)"
if [ "${FRAGMENTS}" -gt 0 ]; then
	check "news fragments present (${FRAGMENTS})" 0
else
	printf '  \033[33m⚠\033[0m  no news fragments — %s will get no changelog entry\n' "${NEW_VERSION}"
fi

HAVE_TOKEN=0
if [ -n "${GH_TOKEN:-}" ] || gh auth token >/dev/null 2>&1; then
	check "GitHub token available" 0
	HAVE_TOKEN=1
else
	check "GitHub token available (needed for the draft release)" 1
fi

printf '\nChangelog preview (towncrier --draft, not written):\n'
if is_final_version "${NEW_VERSION}"; then
	ESC="${NEW_VERSION//./\\.}"
	PRE_COUNT="$(grep -cE "^\.\. changelog:: ${ESC}((a|b|rc)[0-9]+|\.dev[0-9]+)\$" docs/release-notes/changelog.rst 2>/dev/null)" || PRE_COUNT=0
	if [ "${PRE_COUNT}" -gt 0 ]; then
		printf '(final release: %s existing pre-release section(s) will be folded into %s at release time)\n' "${PRE_COUNT}" "${NEW_VERSION}"
	fi
else
	printf '(pre-release: this section is kept and later folded into the final release)\n'
fi
printf -- '------------------------------------------------------------\n%s\n' "${CHANGELOG_PREVIEW}"
printf -- '------------------------------------------------------------\n'

if [ "${HAVE_TOKEN}" -eq 1 ]; then
	printf '\nGitHub release notes preview%s:\n' "${BASE:+ (base ${BASE})}"
	printf -- '------------------------------------------------------------\n'
	# shellcheck disable=SC2086  # BASE is a single tag (no spaces); the split into "--base <tag>" is intentional
	uv run python tools/prepare_release.py "${NEW_VERSION}" ${BASE:+--base "${BASE}"} 2>/dev/null || echo "(could not generate GH notes preview)"
	printf -- '------------------------------------------------------------\n'
fi

warn_review_notes

printf '\n'
if [ "${fail}" -eq 0 ]; then
	echo "✅ READY to release ${NEW_VERSION} (re-run release.yml with dry_run=false to cut it)."
else
	echo "❌ NOT READY — resolve the ❌ items above."
fi

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
	{
		printf '## Release preview: `%s` → `%s` (`%s`)\n\n' "${CUR_VERSION}" "${NEW_VERSION}" "${ARG}"
		if [ "${fail}" -eq 0 ]; then
			printf '**✅ READY** — re-run with `dry_run: false` to cut the release.\n\n'
		else
			printf '**❌ NOT READY** — resolve the failing checks.\n\n'
		fi
		printf '### Changelog entry (preview)\n\n```rst\n%s\n```\n' "${CHANGELOG_PREVIEW}"
	} >>"${GITHUB_STEP_SUMMARY}"
fi

exit "${fail}"
