from examples.data_transfer_objects.dto_from_model_instance import (
    CompanyDTO as FromModelCompanyDTO,
)
from examples.data_transfer_objects.dto_from_model_instance import (
    company_instance,
    dto_instance,
)
from examples.data_transfer_objects.dto_to_model_instance import Company
from examples.data_transfer_objects.dto_to_model_instance import (
    CompanyDTO as ToModelCompanyDTO,
)


def test_dto_from_model_instance() -> None:
    assert isinstance(dto_instance, FromModelCompanyDTO)

    for field in FromModelCompanyDTO.__fields__:
        assert getattr(dto_instance, field) == getattr(company_instance, field)


def test_dto_to_model_instance() -> None:
    company_dto_instance = ToModelCompanyDTO(id=1, name="My Firm", worth=1000000.0)  # type: ignore
    model_instance = company_dto_instance.to_model_instance()

    assert isinstance(model_instance, Company)
    for field in ToModelCompanyDTO.__fields__:
        assert getattr(model_instance, field) == getattr(company_dto_instance, field)
