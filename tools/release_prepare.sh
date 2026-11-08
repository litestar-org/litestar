#!/usr/bin/env bash
# Prepare a release LOCALLY: create a vX.Y.Z branch, bump the version, assemble the
# changelog from news fragments, and commit. Does NOT push and does NOT touch GitHub.
# Review the result, then push + open a PR (or run the "Release" workflow with
# dry_run off). Pairs with tools/release_preview.sh (which writes nothing).
#
# Usage: tools/release_prepare.sh [bump|version]   (default: patch)
#   bump:    patch | minor | major | stable | alpha | beta | rc  (combinable, e.g. "major beta")
#   version: an explicit version, e.g. 4.0.0b1
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
towncrier build --yes --version "${NEW_VERSION}"

# Pre-releases keep their own section; at a FINAL release, fold the pre-release
# sections (aN/bN/rcN/.devN) of this version into a single consolidated section.
if printf '%s' "${NEW_VERSION}" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(\.post[0-9]+)?$'; then
	python3 tools/consolidate_prereleases.py "${NEW_VERSION}"
fi

git commit -am "chore(release): prepare release ${TAG}"

cat <<EOF

✅ Prepared ${TAG} on branch ${TAG} — nothing pushed.

Next:
  git push origin ${TAG}
  gh pr create --base main --title "chore(release): ${TAG}"
  # after the PR is merged:
  python tools/prepare_release.py ${NEW_VERSION} --create-draft-release
  # then click "Publish" on the draft release  ->  publish.yml  ->  PyPI

(Or skip all of the above and just run the "Release" workflow with dry_run off.)
EOF

printf '\n\033[1;33m⚠ When you create the release, review the generated notes before publishing — especially the "Other changes" section: not all of those entries belong in the final notes.\033[0m\n'
