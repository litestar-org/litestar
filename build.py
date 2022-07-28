"""
Build script is adapted from: https://github.com/aotuai/example-cython-poetry-pypi/blob/main/build.py

See: https://aotu.ai/en/blog/2021/01/19/publishing-a-proprietary-python-package-on-pypi-using-poetry/
For further details
"""

import multiprocessing
from pathlib import Path
from typing import List

# enable clang compiler optimizations
CLANG_COMPILE_ARGS = ["-O2"]
BUILD_TARGETS = [
    "starlite/routes.py",
    "starlite/response.py",
    "starlite/parsers.py",
    "starlite/signature.py",
]


def build() -> None:
    """
    Entry build for poetry build
    """
    # pylint: disable=import-outside-toplevel
    try:
        from Cython.Build import cythonize
        from Cython.Distutils.build_ext import new_build_ext as cython_build_ext
        from setuptools import Distribution, Extension

        extension_modules: List[Extension] = []

        for filename in BUILD_TARGETS:
            module_path = filename.removesuffix(".py").replace("/", ".")
            extension_module = Extension(
                name=module_path, sources=[str(filename)], extra_compile_args=CLANG_COMPILE_ARGS
            )
            extension_modules.append(extension_module)

        # Use Setuptools to collect files
        distribution = Distribution(
            {
                "ext_modules": cythonize(
                    module_list=extension_modules,
                    build_dir=Path("dist"),
                    annotate=False,
                    nthreads=multiprocessing.cpu_count() * 2,
                    compiler_directives={"language_level": "3"},
                    force=True,
                ),
                "cmdclass": {
                    "build_ext": cython_build_ext,
                },
            }
        )

        # Grab the build_ext command and copy all files back to source dir. This is
        # done so that Poetry grabs the files during the next step in its build.
        distribution.run_command("build_ext")
        build_ext_cmd = distribution.get_command_obj("build_ext")
        build_ext_cmd.copy_extensions_to_source()
    except ImportError:
        pass


if __name__ == "__main__":
    build()
