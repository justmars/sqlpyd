from sqlpyd import Connection, IndividualBio


def test_full_name(person1):
    assert not person1.get("full_name")
    obj = IndividualBio(**person1)
    full = obj.first_name + " " + obj.last_name + f", {obj.suffix}"
    assert obj.full_name == full if obj.suffix else ""


def test_created_cleaned_gender(in_memory_db: Connection, person2: dict):
    tbl = in_memory_db.add_record(IndividualBio, person2)
    row = next(tbl.rows)
    assert row["id"] == 1
    assert row["gender"] != person2.get("gender")
    assert row["gender"] == "female"


def test_insert_records(session: Connection):
    assert list(session.tbl(IndividualBio.__tablename__).rows) == [
        {
            "id": 1,
            "full_name": "Juan Doe, Jr.",
            "first_name": "Juan",
            "last_name": "Doe",
            "suffix": "Jr.",
            "nick_name": None,
            "gender": "male",
        },
        {
            "id": 2,
            "full_name": "Jane Doe",
            "first_name": "Jane",
            "last_name": "Doe",
            "suffix": None,
            "nick_name": "Jany",
            "gender": "female",
        },
    ]
