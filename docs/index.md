---
hide:
  - navigation
  - toc
---
# Overview

Combining [sqlite-utils](https://github.com/simonw/sqlite-utils) data management + [Pydantic](https://github.com/pydantic/pydantic) data validation for data that will (later) be deployed in a specific [Datasette](https://datasette.io/) project: [LawData](https://lawdata.xyz).

## Premise

Each data model exists in two dimensions:

1. the app layer via a pythonic interface; and
2. the persistence layer via a database.

Here we'll use sqlite. Though sqlite features are frequently evolving, see *json1*, *fts5*, etc., it lacks a more robust validation mechanism.

Pydantic would be useful to:

1. clean and validate a model's fields prior to database insertion;
2. reuse data on the pythonic interface for dynamic queries on database extraction.

Since the database query syntax (SQL) is different from the app syntax (python), a useful bridge is sqlite-utils which allows us, via this package, to use pre-defined *Pydantic* field attributes as a means of creating dynamic SQL statements.

Put another way, this is an attempt to integrate the two tools so that the models declared in *Pydantic* can be consumed directly by *sqlite-utils*.

The opinionated use of default configurations is intended for a more specific project. Later on, may consider making this more general in scope.

## Connection

Connect to a database declared by an `.env` file through a `DB_FILE` variable, e.g.

```sh
DB_FILE="code/sqlpyd/test.db"
```

With the .env file created, the following sqlite `sqlpyd.Connection` object gets a typed `Table`:

```python
from sqlpyd import Connection
from sqlite_utils.db import Table

conn = Connection()  # will use .env file's DB_FILE value
conn.db["test_table"].insert(
    {"text": "hello-world"}, pk="id"
)  # will contain a db object
isinstance(conn.tbl("test_table"), Table)
True
```

There appears to be movement to make *sqlite-utils* more type-friendly, [see issue](https://github.com/simonw/sqlite-utils/issues/496).

## Fields

### Generic Pydantic Model

Let's assume a generic pydantic BaseModel with a non-primitive field like `suffix` and `gender`:

```py
# see sqlpyd/name.py
class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "unspecified"


class Suffix(str, Enum):
    jr = "Jr."
    sr = "Sr."
    third = "III"
    fourth = "IV"
    fifth = "V"
    sixth = "VI"


class IndividualBio(BaseModel):
    first_name: str = Field(None, max_length=50)
    last_name: str = Field(None, max_length=50)
    suffix: Suffix | None = Field(None, max_length=4)
    nick_name: str = Field(None, max_length=50)
    gender: Gender | None = Field(Gender.other)

    class Config:
        use_enum_values = True
```

With the BaseModel, we can get the types directly using:

```py
>>> IndividualBio.__annotations__
{
    "first_name": str,
    "last_name": str,
    "suffix": sqlpyd.__main__.Suffix | None,  # is non-primitive / optional
    "nick_name": str,
    "gender": sqlpyd.__main__.Gender | None,  # is non-primitive  / optional
}
```

Using the *sqlite-utils* convention of creating tables, this will throw an error:

```py
>>> from sqlpyd import Connection  # thin wrapper over sqlite-utils Database()

>>> conn = Connection(DatabasePath="created.db")
>>> conn.db["test_tbl"].create(columns=IndividualBio.__annotations__)
...
KeyError: sqlpyd.__main__.Suffix | None
```

### Data Modelling & Input Validation

We could rewrite the needed columns and use *sqlite-utils*:

```py
conn.db["test_tbl"].create(
    columns={
        "first_name": str,
        "last_name": str,
        "suffix": str,
        "nick_name": str,
        "gender": str,
    }
)
# <Table test_tbl (first_name, last_name, suffix, nick_name, gender)>
```

But we can also modify the initial Pydantic model and co-inherit from  `sqlpyd.TableConfig`, to wit:

```py
class RegularName(
    BaseModel
):  # separated the name to add a clear pre-root validator, note addition to field attributes
    full_name: str | None = Field(None, col=str, fts=True, index=True)
    first_name: str = Field(..., max_length=50, col=str, fts=True)
    last_name: str = Field(..., max_length=50, col=str, fts=True, index=True)
    suffix: Suffix | None = Field(None, max_length=4, col=str)

    class Config:
        use_enum_values = True

    @root_validator(pre=True)
    def set_full_name(cls, values):
        if not values.get("full_name"):
            first = values.get("first_name")
            last = values.get("last_name")
            if first and last:
                values["full_name"] = f"{first} {last}"
                if sfx := values.get("suffix"):
                    values["full_name"] += f", {sfx}"
        return values


class IndividualBio(
    TableConfig
):  # mandatory step:  inherit from TableConfig (which inherits from BaseModel)
    __tablename__ = "person_tbl"  # optional: may declare a tablename
    __indexes__ = [["first_name", "last_name"]]  # optional: may declare joined indexes
    nick_name: str | None = Field(None, max_length=50, col=str, fts=True)
    gender: Gender | None = Field(Gender.other, max_length=15, col=str)

    @validator("gender", pre=True)
    def lower_cased_gender(cls, v):
        return Gender(v.lower()) if v else None
```

With this setup, we can use the connection to create the table. Note that the primary key `id` is auto-generated in this scenario:

```py
conn = Connection(DatabasePath="test.db", WAL=False)

conn.create_table(IndividualBio)
# <Table person_tbl (id, full_name, first_name, last_name, suffix, nick_name, gender)>

person2 = {  # dict
    "first_name": "Jane",
    "last_name": "Doe",
    "suffix": None,
    "gender": "FEMALE",  # all caps
    "nick_name": "Jany",
}

IndividualBio.__validators__  # note that we created a validator for 'gender'
# {'gender': [<pydantic.class_validators.Validator object at 0x10c497510>]}

IndividualBio.__pre_root_validators__()  # we also have one to create a 'full_name'
# [<function RegularName.set_full_name at 0x10c4b43a0>]

tbl = conn.add_record(
    IndividualBio, person2
)  # under the hood, the dict is instantiated to a Pydantic model and the resulting `tbl` value is an sqlite-utils Table

assert list(tbl.rows) == [
    {
        "id": 1,  # auto-generated
        "full_name": "Jane Doe",  # since the model contains a pre root-validator, it adds a full name
        "first_name": "Jane",
        "last_name": "Doe",
        "suffix": None,
        "nick_name": "Jany",
        "gender": "female",  # since the model contains a validator, it cleans the same prior to database entry
    }
]
True
```

### Attributes

`sqlite-utils` is a far more powerful solution than the limited subset of features provided here. Again, this abstraction is for the purpose of easily reusing the functionality for a specific project rather than for something more generalized.

#### Columns In General

Using `col` in the Pydantic Field signals the need to add the field to an sqlite database table:

```python
conn = Connection(DatabasePath="test.db", WAL=False)
kls = IndividualBio
tbl = conn.db[kls.__tablename__]
cols = kls.extract_cols(kls.__fields__)  # possible fields to use
"""
{'first_name': str,
 'last_name': str,
 'suffix': str,
 'nick_name': str,
 'gender': str}
"""
tbl.create(cols)  # customize tablename and column types
# <Table individual_bio_tbl (first_name, last_name, suffix, nick_name, gender)>
```

#### Primary Key

To auto-generate, use the `TableConfig.config_tbl()` helper. It auto-creates the `id` field as an `int`-based primary key.

> Note: if an `id` is declared as a `str` in the pydantic model, the `str` declaration takes precedence over the implicit `int` default.

```py
conn = Connection(DatabasePath="test_db.db")
kls = IndividualBio
tbl = conn.db[kls.__tablename__]
tbl_created = kls.config_tbl(tbl=tbl, cols=kls.__fields__)
# <Table individual_bio_tbl (id, first_name, last_name, suffix, nick_name, gender)> # id now added
```

This results in the following sql schema:

```sql
CREATE TABLE [individual_bio_tbl] (
   [id] INTEGER PRIMARY KEY, -- added as integer since no field specified
   [first_name] TEXT NOT NULL, -- required via Pydantic's ...
   [last_name] TEXT NOT NULL, -- required via Pydantic's ...
   [suffix] TEXT,
   [nick_name] TEXT,
   [gender] TEXT
)
```

#### Full-Text Search (fts) Fields

Since we indicated, in the above declaration of `Fields`, that some columns are to be used for `fts`, we enable *sqlite-utils* to auto-generate the tables required. This makes possible the [prescribed approach of querying fts tables](https://sqlite-utils.datasette.io/en/stable/python-api.html#building-sql-queries-with-table-search-sql):

```py
# Using the same variable for `tbl` described above, can yield a query string, viz.
print(tbl.search_sql(columns=["first_name", "last_name"]))
```

produces:

```sql
with original as (
    select
        rowid,
        [first_name],
        [last_name]
    from [individual_bio_tbl]
)
select
    [original].[first_name],
    [original].[last_name]
from
    [original]
    join [individual_bio_tbl_fts] on [original].rowid = [individual_bio_tbl_fts].rowid
where
    [individual_bio_tbl_fts] match :query
order by
    [individual_bio_tbl_fts].rank
```

#### Foreign Keys

To add foreign keys, can use the `fk` attribute on a ModelField, assigning the same to a 2-tuple, e.g.:

```python
class GroupedIndividuals(TableConfig):
    __tablename__ = "grouping_tbl"
    __indexes__ = [["member_id", "name"]]

    name: str = Field(..., max_length=50, col=str)
    member_id: int = Field(
        ..., col=int, fk=(IndividualBio.__tablename__, "id"), index=True
    )
```

Parts of `fk` tuple:

- The first part of the `fk` tuple is the referenced table name *X*.
- The second part of the `fk` tuple is the id of *X*.

So in the above example, `member_id`, the Pydantic field, is constrained to the "id" column of the table "individual_bio_tbl"

#### Indexes

Note that we can add an index to each field as well with a boolean `True` to a ModelField attribute `index`. In case we want to use a combination of columns for the index, can include this when subclassing `TableConfig`:

```py
class GroupedIndividuals(TableConfig):
    __tablename__ = "grouping_tbl"
    __indexes__ = [["member_id", "name"]]  # follow sqlite-utils convention
```

When combined, the sql generated amounts to the following:

```sql
CREATE TABLE [grouping_tbl] (
   [id] INTEGER PRIMARY KEY,
   [name] TEXT NOT NULL,
   [member_id] INTEGER NOT NULL REFERENCES [individual_bio_tbl]([id])
);
CREATE UNIQUE INDEX [idx_grouping_tbl_member_id]
    ON [grouping_tbl] ([member_id]);
CREATE UNIQUE INDEX [idx_grouping_tbl_name_member_id]
    ON [grouping_tbl] ([name], [member_id]);
```
