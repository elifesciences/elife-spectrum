import pytest
from spectrum import checks

@pytest.mark.two
def test_integration_of_gateway():
    checks.API.labs_health()

