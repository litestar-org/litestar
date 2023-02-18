from pydantic import BaseConfig


class BaseConfigModel(BaseConfig):
    """Base configuration model"""

    arbitrary_types_allowed = True
    copy_on_model_validation = "none"
