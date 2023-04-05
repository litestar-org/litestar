from functools import partial
from typing import Literal

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective

_GH_BASE_URL = "https://github.com/starlite-api/starlite"


def _parse_gh_reference(raw: str, type_: Literal["issues", "pull"]) -> list[str]:
    return [f"{_GH_BASE_URL}/{type_}/{r.strip()}" for r in raw.split(" ") if r]


class Change(nodes.General, nodes.Element):
    pass


class ChangeDirective(SphinxDirective):
    required_arguments = 1
    has_content = True
    final_argument_whitespace = True
    option_spec = {
        "type": partial(directives.choice, values=("feature", "bugfix", "misc")),
        "breaking": directives.flag,
        "issue": directives.unchanged,
        "pr": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        self.assert_has_content()

        change_type = self.options["type"].lower()
        title = self.arguments[0]

        change_node = nodes.container("\n".join(self.content))
        change_node.attributes["classes"].append("changelog-change")

        self.state.nested_parse(self.content, self.content_offset, change_node)

        reference_links = [
            *_parse_gh_reference(self.options.get("issue", ""), "issues"),
            *_parse_gh_reference(self.options.get("pr", ""), "pull"),
        ]

        references_paragraph = nodes.paragraph()
        references_paragraph.append(nodes.Text("References: "))
        for i, link in enumerate(reference_links, 1):
            link_node = nodes.inline()
            link_node += nodes.reference("", link, refuri=link, external=True)
            references_paragraph.append(link_node)
            if i != len(reference_links):
                references_paragraph.append(nodes.Text(", "))

        change_node.append(references_paragraph)

        return [
            Change(
                "",
                change_node,
                title=self.state.inliner.parse(title, 0, self.state.memo, change_node)[0],
                change_type=change_type,
                breaking="breaking" in self.options,
            )
        ]


class ChangelogDirective(SphinxDirective):
    required_arguments = 1
    has_content = True

    def run(self) -> list[nodes.Node]:
        self.assert_has_content()

        version = self.arguments[0]

        changelog_node = nodes.section()
        changelog_node += nodes.title(version, version)
        section_target = nodes.target("", "", ids=[version])

        self.state.nested_parse(self.content, self.content_offset, changelog_node)

        change_group_lists = {
            "feature": nodes.definition_list(),
            "bugfix": nodes.definition_list(),
            "misc": nodes.definition_list(),
        }

        change_group_titles = {"bugfix": "Bugfixes", "feature": "Features", "misc": "Other changes"}

        nodes_to_remove = []

        for change_node in changelog_node.findall(Change):
            change_type = change_node.attributes["change_type"]
            title = change_node.attributes["title"]

            list_item = nodes.definition_list_item("")

            term = nodes.term()
            term += title
            if change_node.attributes["breaking"]:
                breaking_notice = nodes.inline("breaking", "breaking")
                breaking_notice.attributes["classes"].append("breaking-change")
                term += breaking_notice

            list_item += [term]

            list_item += nodes.definition("", change_node.children[0])

            nodes_to_remove.append(change_node)

            change_group_lists[change_type] += list_item

        for node in nodes_to_remove:
            changelog_node.remove(node)

        for change_group_type, change_group_list in change_group_lists.items():
            if not change_group_list.children:
                continue

            section = nodes.section()

            target_id = f"{version}-{change_group_type}"
            target_node = nodes.target("", "", ids=[target_id])
            title = change_group_titles[change_group_type]

            section += nodes.title(title, title)
            section += change_group_list

            changelog_node += [target_node, section]

        return [section_target, changelog_node]


def setup(app: Sphinx) -> dict[str, str]:
    app.add_directive("changelog", ChangelogDirective)
    app.add_directive("change", ChangeDirective)

    return {}
