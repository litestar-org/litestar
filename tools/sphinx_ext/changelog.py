from pydata_sphinx_theme import BootstrapHTML5Translator
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from docutils import nodes
from docutils.parsers.rst import directives
from functools import partial
from typing import Literal


_GH_BASE_URL = "https://github.com/starlite-api/starlite"


def _parse_gh_reference(raw: str, type_: Literal["issues", "pull"]) -> list[str]:
    return [f"{_GH_BASE_URL}/{type_}/{r.strip()}" for r in raw.split(" ")]


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

        title = self.arguments[0]
        change_type = self.options["type"].lower()

        change_node = nodes.container("\n".join(self.content))
        change_node.attributes["classes"].append("changelog-change")

        change_node.append(nodes.strong(title, title))

        if "breaking" in self.options:
            breaking_node = nodes.paragraph("", "breaking change")
            breaking_node.attributes["classes"].append("breaking-change")
            change_node.append(breaking_node)

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

        return [change_node]


def setup(app: Sphinx) -> dict[str, str]:
    # app.add_directive("changelog", ChangelogDirective)
    app.add_directive("change", ChangeDirective)

    return {}
