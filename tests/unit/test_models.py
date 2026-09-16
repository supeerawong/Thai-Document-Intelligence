import pytest
from pydantic import ValidationError
from thaidoc.models import FieldProvenance


def test_page_numbers_are_one_based() -> None:
    with pytest.raises(ValidationError):
        FieldProvenance(page=0, method="rule")
