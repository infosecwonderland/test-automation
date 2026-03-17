import os
import sys

# Make the repo root importable so both test suites share utils/contract_loader
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import allure
import pytest

@pytest.fixture(autouse=True)
def _allure_suite_labels():
    allure.dynamic.parent_suite("Security Tests")
    allure.dynamic.suite("pytest")
