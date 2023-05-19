import argparse
import logging
import sys

from github import Github

logger = logging.getLogger("litestar-docs-preview")
logging.basicConfig(level=logging.INFO, stream=sys.stdout)


def make_comment(gh_token: str, repo_name: str, pr_number: int) -> None:
    logger.setLevel("DEBUG")

    logger.info(f"Creating comment for PR #{pr_number}")

    client = Github(login_or_token=gh_token)
    repository = client.get_repo(repo_name)

    comment_body = (
        "Documentation preview will be available shortly at "
        f"https://litestar-org.github.io/litestar-docs-preview/{pr_number}"
    )

    issue = repository.get_issue(pr_number)
    comments = issue.get_comments()

    logger.info("Checking for previous comments")
    for comment in comments:
        if comment.user.id != 41898282:  # id of the github-actions bot user
            logger.debug(f"Ignoring comment by user {comment.user.id!r}")
            continue
        if comment.body != comment_body:
            logger.debug(
                "Ignoring comment from github-actions user because of mismatching body: \n "
                f"{comment.body} != {comment_body}"
            )
            continue

        comment.delete()
        logger.info(f"Deleting previous comment: {comment.id}")

    issue.create_comment(comment_body)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("gh_token")
    parser.add_argument("--pr")
    parser.add_argument("--repo")

    args = parser.parse_args()

    make_comment(gh_token=args.gh_token, repo_name=args.repo, pr_number=int(args.pr))


if __name__ == "__main__":
    main()
