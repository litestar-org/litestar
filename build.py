"""
Build script is adapted from: https://github.com/aotuai/example-cython-poetry-pypi/blob/main/build.py

See: https://aotu.ai/en/blog/2021/01/19/publishing-a-proprietary-python-package-on-pypi-using-poetry/
For further details
"""

import multiprocessing
from pathlib import Path
from typing import List

from Cython.Build import cythonize
from Cython.Distutils.build_ext import new_build_ext as cython_build_ext
from setuptools import Distribution, Extension

# enable clang compiler optimizations
CLANG_COMPILE_ARGS = ["-O2"]


def get_extension_modules() -> List[Extension]:
    """
    Collect all .py files in the starlite folder and turn them into setuptools.Extensions
    """

    extension_modules: List[Extension] = []

    for filename in Path("starlite").rglob("*.py"):
        module_path = str(filename.with_suffix("")).replace("/", ".")
        extension_module = Extension(name=module_path, sources=[str(filename)], extra_compile_args=CLANG_COMPILE_ARGS)
        extension_modules.append(extension_module)

    return extension_modules


def build() -> None:
    """
    Entry build for poetry build
    """
    extension_modules = cythonize(
        module_list=get_extension_modules(),
        build_dir=Path("dist"),
        # Don't generate an .html output file. This will contain source.
        annotate=False,
        # Parallelize our build
        nthreads=multiprocessing.cpu_count() * 2,
        # Tell Cython we're using Python 3
        compiler_directives={"language_level": "3"},
        force=True,
    )

    # Use Setuptools to collect files
    distribution = Distribution(
        {
            "ext_modules": extension_modules,
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


if __name__ == "__main__":
    build()
