from sqlpyd import Connection, IndividualBio


def test_sample_columns_from_model(col_structure):
    assert (
        IndividualBio.extract_cols(IndividualBio.__fields__) == col_structure
    )


def test_config_tbl_pk(in_memory_db: Connection, col_structure):
    kls1 = IndividualBio
    tbl1 = in_memory_db.tbl(kls1.__tablename__)
    tbl1_made = kls1.config_tbl(tbl=tbl1)

    assert tbl1_made.columns_dict == col_structure | {"id": int}
    assert tbl1_made.pks == ["id"]
    assert tbl1_made.detect_fts() == "pax_tbl_individual_bio_fts"
    assert [i.name for i in tbl1_made.indexes] == [
        "idx_pax_tbl_individual_bio_first_name_last_name",
        "idx_pax_tbl_individual_bio_last_name",
        "idx_pax_tbl_individual_bio_full_name",
    ]


def test_create_table_func(in_memory_db: Connection):
    tbl = in_memory_db.create_table(IndividualBio)
    assert [i.name for i in tbl.indexes] == [
        "idx_pax_tbl_individual_bio_first_name_last_name",
        "idx_pax_tbl_individual_bio_last_name",
        "idx_pax_tbl_individual_bio_full_name",
    ]
