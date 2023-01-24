import toml

import sqlpyd


def test_version():
    assert (
        toml.load("pyproject.toml")["tool"]["poetry"]["version"]
        == sqlpyd.__version__
    )
