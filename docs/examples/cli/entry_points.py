from setuptools import setup

setup(
   name="my-litestar-plugin",
   ...,
   entry_points={
       "litestar.commands": ["my_command=my_litestar_plugin.cli:main"],
   },
)