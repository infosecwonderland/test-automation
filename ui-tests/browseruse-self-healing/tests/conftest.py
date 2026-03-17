import allure
import pytest


@pytest.fixture(autouse=True)
def _allure_suite_labels():
    allure.dynamic.parent_suite("UI Tests")
    allure.dynamic.suite("Self-Healing (browser-use)")
