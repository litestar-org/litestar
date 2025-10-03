import os

from litestar.cli._utils import _load_app_from_path, populate_repl_globals

app = _load_app_from_path(os.environ["LITESTAR_APP"]).app
new_locals, banner = populate_repl_globals(app=app)
print(banner)
globals().update(new_locals)
