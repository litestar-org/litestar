#!/usr/bin/env bash
# Prepares a release branch and commit locally. Does NOT push and does NOT touch GitHub.
set -euo pipefail

ARG="${1:-patch}"
# shellcheck source=tools/release_lib.sh
source "$(dirname "$0")/release_lib.sh"

if ! git diff --quiet || ! git diff --cached --quiet; then
	echo "✖ working tree is not clean — commit or stash first." >&2
	exit 1
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "${CURRENT_BRANCH}" != "main" ]; then
	if [ ! -t 0 ]; then
		echo "✖ not on main (on \"${CURRENT_BRANCH}\") — refusing to prepare a release unattended." >&2
		exit 1
	fi
	printf '⚠ not on main (on "%s"). Continue anyway? [y/N] ' "${CURRENT_BRANCH}"
	read -r reply
	case "${reply}" in [yY]*) ;; *) echo "aborted." >&2; exit 1 ;; esac
fi

resolve_version "${ARG}" # sets CUR_VERSION, NEW_VERSION, UV_ARGS
TAG="v${NEW_VERSION}"

if git rev-parse -q --verify "refs/tags/${TAG}" >/dev/null 2>&1; then
	echo "✖ tag ${TAG} already exists." >&2
	exit 1
fi
if git show-ref -q --verify "refs/heads/${TAG}"; then
	echo "✖ branch ${TAG} already exists." >&2
	exit 1
fi

echo "→ preparing ${TAG} (${ARG}) on a new branch — nothing will be pushed"
git switch -c "${TAG}"
uv version "${UV_ARGS[@]}" --no-sync
if has_news_fragments; then
	towncrier build --yes --version "${NEW_VERSION}"
else
	echo "⚠ no news fragments — skipping the changelog build (no entry for ${NEW_VERSION})"
fi

if is_final_version "${NEW_VERSION}"; then
	python3 tools/consolidate_prereleases.py "${NEW_VERSION}"
fi

git commit -am "chore(release): prepare release ${TAG}"

cat <<EOF

✅ Prepared ${TAG} on branch ${TAG} — nothing pushed.

Next:
  git push origin ${TAG}
  gh pr create --base main --head ${TAG} --title "chore(release): ${TAG}" --body ""
  # merging the PR triggers finalize-release.yml, which creates the draft GitHub release.
  # then review and click "Publish" on the draft release  ->  publish.yml  ->  PyPI

(Or skip all of the above and just run the "Release" workflow with dry_run off.)
EOF

warn_review_notes
