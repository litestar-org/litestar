import re
from pathlib import Path

PYPI_BANNER = '<img src="https://raw.githubusercontent.com/litestar-org/branding/473f54621e55cde9acbb6fcab7fc03036173eb3d/assets/Branding%20-%20PNG%20-%20Transparent/Logo%20-%20Banner%20-%20Inline%20-%20Light.png" alt="Litestar Logo - Light" width="100%" height="auto" />'


def generate_pypi_readme() -> None:
    source = Path("README.md").read_text(encoding="utf-8")
    output = re.sub(r"<!-- github-banner-start -->[\w\W]*<!-- github-banner-end -->", PYPI_BANNER, source)
    output = re.sub(r"<!-- contributors-start -->[\w\W]*<!-- contributors-end -->", "", output)
    output = re.sub(r"<!-- ALL-CONTRIBUTORS-BADGE:START[\w\W]*<!-- ALL-CONTRIBUTORS-BADGE:END -->", "", output)

    # ensure a newline here so the other pre-commit hooks don't complain
    output = output.strip() + "\n"
    Path("docs/PYPI_README.md").write_text(output, encoding="utf-8")


if __name__ == "__main__":
    generate_pypi_readme()
