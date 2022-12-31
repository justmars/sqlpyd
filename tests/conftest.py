from pathlib import Path

import pytest

from sqlpyd import Connection, IndividualBio

temppath = "tests/test.db"


@pytest.fixture
def in_memory_db():
    conn = Connection(DatabasePath=None, WAL=False)
    return conn


@pytest.fixture
def col_structure():
    return {
        "full_name": str,
        "first_name": str,
        "last_name": str,
        "suffix": str,
        "nick_name": str,
        "gender": str,
    }


@pytest.fixture
def person1():
    return {
        "first_name": "Juan",
        "last_name": "Doe",
        "suffix": "Jr.",
        "gender": "male",
    }


@pytest.fixture
def person2():
    return {
        "first_name": "Jane",
        "last_name": "Doe",
        "suffix": None,
        "gender": "FEMALE",
        "nick_name": "Jany",
    }


@pytest.fixture
def persons_list(person1, person2):
    return [person1, person2]


def setup_db(conn: Connection, items: list[dict]):
    conn.create_table(IndividualBio)
    conn.add_records(IndividualBio, items)
    return conn


def teardown_db(conn: Connection):
    conn.db.close()  # close the connection
    Path().cwd().joinpath(temppath).unlink()  # delete the file


@pytest.fixture
def session(persons_list):
    c = Connection(DatabasePath=temppath)  # type: ignore
    db = setup_db(c, persons_list)
    yield db
    teardown_db(db)
