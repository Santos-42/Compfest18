import sqlite3

from core import database


def test_legacy_wilayah_schema_gets_required_columns():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE wilayah (id INTEGER PRIMARY KEY, kode TEXT, nama TEXT)")
    database._ensure_wilayah_schema(connection)
    columns = database._table_columns(connection, "wilayah")
    assert database.REQUIRED_WILAYAH_COLUMNS.issubset(columns)
    connection.close()


def test_wilayah_parent_fields_are_derived():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE wilayah (id INTEGER PRIMARY KEY, kode TEXT, nama TEXT, kode_wilayah TEXT, kecamatan TEXT, kabupaten TEXT, provinsi TEXT)"
    )
    connection.executemany(
        "INSERT INTO wilayah (kode, nama) VALUES (?, ?)",
        [("31", "DKI JAKARTA"), ("31.71", "KOTA JAKARTA SELATAN"), ("31.71.01", "KEBAYORAN BARU"), ("31.71.01.1001", "SENAYAN")],
    )
    database._fill_wilayah_parents(connection)
    row = connection.execute(
        "SELECT kode_wilayah, kecamatan, kabupaten, provinsi FROM wilayah WHERE kode='31.71.01.1001'"
    ).fetchone()
    assert row == ("31.71.01.1001", "KEBAYORAN BARU", "KOTA JAKARTA SELATAN", "DKI JAKARTA")
    connection.close()
