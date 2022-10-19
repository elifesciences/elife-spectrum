"Tests that go through EPP and propagate content to the rest of the system"

import pytest
from spectrum import checks

@pytest.mark.epp
def test_epp_ping():
    "EPP host is reachable"
    checks.EPP.ping()

def test_app_status():
    "EPP host is happy"
    checks.EPP.status()
