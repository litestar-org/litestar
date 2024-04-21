app = Litestar(
    static_files_config=[StaticFilesConfig(path="/static", directories=["some_dir"])]
)