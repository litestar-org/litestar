from piccolo.utils.pydantic import create_pydantic_model

from test_apps.piccolo_admin_test_app.home.tables import Task

# task models
TaskModelIn = create_pydantic_model(table=Task, model_name="TaskModelIn")
TaskModelOut = create_pydantic_model(
    table=Task,
    include_default_columns=True,
    model_name="TaskModelOut",
)
