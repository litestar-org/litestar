from dataclasses import dataclass

from litestar.dto import DataclassDTO, DTOConfig
from litestar.enums import RequestEncodingType
from litestar.params import JSONBody
from litestar.typing import FieldDefinition


@dataclass
class User:
    name: str
    email: str
    password: str = ""


class UserDTO(DataclassDTO[User]):
    config = DTOConfig(exclude={"password"})


data_backend = UserDTO.create_for_field_definition(FieldDefinition.from_annotation(JSONBody[User], name="data"))
return_backend = UserDTO.create_for_field_definition(FieldDefinition.from_annotation(User))

user = data_backend.populate_data_from_raw(b'{"name": "Mr Sunglass", "email": "mr.sunglass@example.com"}')
same_user = data_backend.populate_data_from_builtins({"name": "Mr Sunglass", "email": "mr.sunglass@example.com"})
from_msgpack = data_backend.populate_data_from_raw(
    b"\x82\xa4name\xabMr Sunglass\xa5email\xb7mr.sunglass@example.com", media_type=RequestEncodingType.MESSAGEPACK
)

user.password = "secret"
transfer = return_backend.encode_data(user)
