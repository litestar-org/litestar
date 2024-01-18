module.exports = async ({github, context, core}) => {

    const issues = JSON.parse(process.env.CLOSED_ISSUES)
    const releaseURL = context.payload.release.html_url
    const releaseName = context.payload.release.name
    const baseBody = "A fix for this issue has been released in"
    const body = baseBody + ` [${releaseName}](${releaseURL})`

    for (const issueNumber of issues) {
        const opts = github.rest.issues.listComments.endpoint.merge({
            owner: context.repo.owner,
            repo: context.repo.repo,
            issue_number: issueNumber,
        });

        const comments = await github.paginate(opts)
        for (const comment of comments) {
            if (comment.user.id === 41898282 && comment.body.startsWith(baseBody)) {
                await github.rest.issues.deleteComment({
                    owner: context.repo.owner,
                    repo: context.repo.repo,
                    comment_id: comment.id
                })
            }
        }

        await github.rest.issues.createComment({
            owner: context.repo.owner,
            repo: context.repo.repo,
            issue_number: issueNumber,
            body: body,
        })
    }
}
