from enum import Enum

from pydantic import BaseModel, Field, root_validator, validator

from .tableconfig import TableConfig


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


class RegularName(BaseModel):
    full_name: str | None = Field(None, col=str, fts=True, index=True)
    first_name: str = Field(..., max_length=50, col=str, fts=True)
    last_name: str = Field(..., max_length=50, col=str, fts=True, index=True)
    suffix: Suffix | None = Field(None, max_length=4, col=str)

    class Config:
        use_enum_values = True

    @root_validator(pre=True)
    def set_full_name(cls, values):
        """Supply full name, when absent, from first, last, and/or suffix"""
        if not values.get("full_name"):
            first = values.get("first_name")
            last = values.get("last_name")
            if first and last:
                values["full_name"] = f"{first} {last}"
                if sfx := values.get("suffix"):
                    values["full_name"] += f", {sfx}"
        return values


class IndividualBio(RegularName, TableConfig):
    __prefix__ = "pax"
    __tablename__ = "individual_bio"
    __indexes__ = [["first_name", "last_name"]]
    nick_name: str | None = Field(None, max_length=50, col=str, fts=True)
    gender: Gender | None = Field(Gender.other, max_length=15, col=str)

    @validator("gender", pre=True)
    def lower_cased_gender(cls, v):
        return Gender(v.lower()) if v else None
