app = Litestar(route_handlers=[create_static_files_router(path="/static", directories=["some_dir"])])
