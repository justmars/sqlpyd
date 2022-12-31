from pathlib import Path

from sqlite_utils.db import Table

from sqlpyd import Connection


def test_no_path_to_memory_db(in_memory_db: Connection):
    assert in_memory_db.path_to_db is None


def test_db_path():
    path_string = "test.db"
    conn = Connection(DatabasePath="test.db", WAL=False)
    assert Path().cwd() / path_string == conn.path_to_db


def test_insert_table(in_memory_db: Connection):
    tbl = in_memory_db.tbl("test_table")
    tbl.insert({"text": "hello-world"}, pk="id")  # type: ignore
    assert isinstance(tbl, Table)
    assert list(tbl.rows) == [{"id": 1, "text": "hello-world"}]


def test_session(in_memory_db: Connection):
    def extract_row():
        with in_memory_db.session as cur:
            create_sql = "create table t (id integer, text text);"
            cur.execute(create_sql)
            insert_sql = "insert into t values(1, 'hello-world')"
            cur.execute(insert_sql)
            get_sql = "select text from t where id = 1"
            return cur.execute(get_sql).fetchone()

    assert extract_row() == ("hello-world",)
