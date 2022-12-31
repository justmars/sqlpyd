import re
from collections.abc import Iterable, Iterator
from typing import Any, ClassVar

from pydantic import BaseModel
from pydantic.fields import ModelField
from sqlite_utils.db import DescIndex, Table

SEQ_CAP = re.compile(r"([A-Z]+)")


class TableConfig(BaseModel):
    """Based on a `pydantic.BaseModel`, makes use of custom
    `pydantic.Field` attributes, specifically:

    1. `col`
    2. `fk`
    3. `fts`
    4. `index`
    5. ModelField(required=)

    This enables the construction of an `sqlite-utils`-designed table.

    __indexes__ refers to a list of Iterables that can be used as
    indexes to the table,based on the sqlite-utils convention.
    Defaults to None.
    """

    __prefix__: ClassVar[str] = "db"
    __tablename__: ClassVar[str]
    __indexes__: ClassVar[list[Iterable[str | DescIndex]] | None] = None

    @classmethod
    def __init_subclass__(cls):
        if not hasattr(cls, "__tablename__"):
            msg = "Must explicitly declare a __tablename__ for TableConfig"
            raise NotImplementedError(f"{msg} {cls=}.")
        cls.__tablename__ = "_".join(
            [cls.__prefix__, "tbl", cls.__tablename__]
        )

    @classmethod
    def config_tbl(cls, tbl: Table) -> Table:
        """Using pydantic fields, generate an sqlite db table via
        `sqlite-utils` conventions.

        Each `pydantic.BaseModel` will have a __fields__ attribute,
        which is a dictionary of `ModelField` values.

        Each of these fields assigned a `col` attribute
        will be extracted from the ModelField.

        The extract will enable further processing on the field such
        as introspecting the `fk`, `fts`, and `index` attributes.

        For more complex indexes, the `idxs` attribute can be supplied
        following the `sqlite-utils` convention.

        Returns:
            Table: An sqlite-utils Table object.
        """
        if tbl.exists():
            return tbl

        cols = cls.__fields__
        created_tbl = tbl.create(
            columns=cls.extract_cols(cols),
            pk="id",
            not_null=cls._not_nulls(cols),
            column_order=["id"],  # make id the first
            foreign_keys=cls._fks(cols),
            if_not_exists=True,
        )

        single_indexes = cls._indexes(cols)
        if single_indexes:
            for idx1 in single_indexes:
                tbl.create_index(columns=idx1, if_not_exists=True)

        if cls.__indexes__:
            for idx2 in cls.__indexes__:
                if not isinstance(idx2, Iterable):
                    msg = f"{idx2=} must follow sqlite-utils convention."
                    raise Exception(msg)
                if len(list(idx2)) == 1:
                    msg = "If single column index, use index= attribute."
                    raise Exception(msg)
                tbl.create_index(columns=idx2, if_not_exists=True)

        if fts_cols := cls._fts(cols):
            created_tbl.enable_fts(
                columns=fts_cols,
                create_triggers=True,
                tokenize="porter",
            )

        return created_tbl

    @classmethod
    def extract_model_fields(
        cls, fields_data: dict[str, ModelField]
    ) -> Iterator[tuple[str, ModelField]]:
        """Loop through the ModelField to extract included 2-tuples.
        The first part of the tuple is the name of the field,
        the second part is the ModelField.

        Args:
            fields_data (dict[str, ModelField]): _description_

        Yields:
            Iterator[tuple[str, ModelField]]: _description_
        """
        _pydantic_fields = [{k: v} for k, v in fields_data.items()]
        for field in _pydantic_fields:
            for k, v in field.items():
                if not v.field_info.exclude:  # implies inclusion
                    yield (k.lower(), v)  # all keys are lower-cased

    @classmethod
    def extract_cols(
        cls, fields_data: dict[str, ModelField]
    ) -> dict[str, Any]:
        """If a `col` attribute is declared in the ModelField,
        e.g. `name: str = Field(col=str)`, extract it.

        Note this makes the the `id` field an `int` type by default.
        But if an `id` field exists in the parent model and this is
        set to a different type, e.g. `str`, this overrides the default `id`
        previously set as an `int`.

        Args:
            fields_data (dict[str, ModelField]): Pydantic field

        Returns:
            dict[str, Any]: A mapping to be used later sqlite-utils
        """
        cols: dict[str, Any] = {}
        cols["id"]: int  # type: ignore
        for k, v in cls.extract_model_fields(fields_data):
            if sqlite_type := v.field_info.extra.get("col"):
                cols[k] = sqlite_type
        return cols

    @classmethod
    def _fts(cls, fields_data: dict[str, ModelField]) -> list[str]:
        """If `fts` attribute in ModelField is set, extract."""
        cols: list[str] = []
        for k, v in cls.extract_model_fields(fields_data):
            if v.field_info.extra.get("fts", False):
                cols.append(k)
        return cols

    @classmethod
    def _fks(
        cls, fields_data: dict[str, ModelField]
    ) -> list[tuple[str, str, str]] | None:
        """If `fk` attribute in ModelField is set, extract."""
        fk_tuples: list[tuple[str, str, str]] = []
        for k, v in cls.extract_model_fields(fields_data):
            if fk := v.field_info.extra.get("fk"):
                if isinstance(fk, tuple):
                    fk_setup = (k, fk[0], fk[1])
                    fk_tuples.append(fk_setup)
        return fk_tuples or None

    @classmethod
    def _indexes(
        cls, fields_data: dict[str, ModelField]
    ) -> list[list[str]] | None:
        """If `index` attribute in ModelField is set, extract."""
        cols: list[list[str]] = []
        for k, v in cls.extract_model_fields(fields_data):
            if idx := v.field_info.extra.get("index"):
                if isinstance(idx, bool) and idx is True:
                    cols.append([k])
        return cols or None

    @classmethod
    def _not_nulls(cls, fields_data: dict[str, ModelField]) -> set[str]:
        """If `required` in the ModelField is `True`
        and the field has not been `excluded`, extract.
        """
        cols: set[str] = set()
        for k, v in cls.extract_model_fields(fields_data):
            if v.required:  # both values (required, exclude) are boolean
                cols.add(k)
        return cols
