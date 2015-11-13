import pytest
def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true",
        help="run slow tests")
    parser.addoption("--log", action="store_true",
        help="print debug logs")

def pytest_runtest_setup(item):
    if 'slow' in item.keywords and not item.config.getoption("--runslow"):
        pytest.skip("need --runslow option to run")
