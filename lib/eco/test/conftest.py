import pytest
def pytest_addoption(parser):
    parser.addoption("--justslow", action="store_true",
        help="ONLY run slow tests")
    parser.addoption("--runslow", action="store_true",
        help="run slow tests")
    parser.addoption("--logs", action="store_true",
        help="print debug logs")

def pytest_runtest_setup(item):
    if item.config.getoption("--justslow"):
        if 'slow' not in item.keywords:
            pytest.skip("need --runslow option to run")
    elif 'slow' in item.keywords and not item.config.getoption("--runslow"):
        pytest.skip("need --runslow option to run")

def pytest_configure(config):
    if config.getoption('--logs'):
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
