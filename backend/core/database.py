import sqlite3

from core.config import REPO_ROOT, settings

DB_PATH = settings.DATABASE_PATH
SCHEMA_VERSION = 1
REQUIRED_WILAYAH_COLUMNS = {
    "id",
    "kode",
    "nama",
    "kode_wilayah",
    "kecamatan",
    "kabupaten",
    "provinsi",
}


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(DB_PATH))
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _table_columns(connection, table_name: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")}


def _ensure_wilayah_schema(connection):
    columns = _table_columns(connection, "wilayah")
    if not columns:
        connection.execute(
            """
            CREATE TABLE wilayah (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kode TEXT NOT NULL,
                nama TEXT NOT NULL,
                kode_wilayah TEXT,
                kecamatan TEXT,
                kabupaten TEXT,
                provinsi TEXT
            )
            """
        )
        return
    if not {"kode", "nama"}.issubset(columns):
        raise RuntimeError("Schema tabel wilayah tidak memiliki kolom kode dan nama.")
    for column in sorted(REQUIRED_WILAYAH_COLUMNS - columns - {"id", "kode", "nama"}):
        connection.execute(f"ALTER TABLE wilayah ADD COLUMN {column} TEXT")


def _fill_wilayah_parents(connection):
    name_by_code = dict(connection.execute("SELECT kode, nama FROM wilayah"))
    rows = connection.execute("SELECT id, kode FROM wilayah").fetchall()
    updates = []
    for row_id, code in rows:
        parts = code.split(".")
        province = name_by_code.get(parts[0])
        regency = name_by_code.get(".".join(parts[:2])) if len(parts) >= 2 else None
        district = name_by_code.get(".".join(parts[:3])) if len(parts) >= 3 else None
        updates.append((code, district, regency, province, row_id))
    connection.executemany(
        "UPDATE wilayah SET kode_wilayah=?, kecamatan=?, kabupaten=?, provinsi=? WHERE id=?",
        updates,
    )


def _import_wilayah_if_empty(connection):
    row_count = connection.execute("SELECT COUNT(*) FROM wilayah").fetchone()[0]
    if row_count:
        return
    sql_file = REPO_ROOT / "data" / "wilayah.sql"
    if not sql_file.exists():
        raise RuntimeError(f"File wilayah.sql tidak ditemukan di {sql_file}")
    connection.executescript(sql_file.read_text(encoding="utf-8"))


def init_database():
    connection = _connect()
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS simulation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_addresses TEXT NOT NULL,
                result_data TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _ensure_wilayah_schema(connection)
        _import_wilayah_if_empty(connection)
        _fill_wilayah_parents(connection)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_wilayah_kode ON wilayah(kode_wilayah)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_wilayah_nama ON wilayah(nama)")
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _like(value: str) -> str:
    return f"%{value}%"


def get_adm4_code(fragment):
    with _connect() as connection:
        row = connection.execute(
            "SELECT kode_wilayah FROM wilayah WHERE nama LIKE ? AND length(kode_wilayah) >= 9 LIMIT 1",
            (_like(fragment),),
        ).fetchone()
    return row[0] if row else None


def get_adm2_code(fragment):
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT kode_wilayah FROM wilayah
            WHERE (nama LIKE ? OR kabupaten LIKE ?) AND length(kode_wilayah)=5
            LIMIT 1
            """,
            (_like(fragment), _like(fragment)),
        ).fetchone()
    return row[0] if row else None


def get_adm3_code(fragment, adm2_prefix=None):
    with _connect() as connection:
        if adm2_prefix:
            row = connection.execute(
                """
                SELECT kode_wilayah FROM wilayah
                WHERE nama LIKE ? AND length(kode_wilayah)=8 AND kode_wilayah LIKE ?
                LIMIT 1
                """,
                (_like(fragment), f"{adm2_prefix}.%"),
            ).fetchone()
        else:
            row = connection.execute(
                "SELECT kode_wilayah FROM wilayah WHERE nama LIKE ? AND length(kode_wilayah)=8 LIMIT 1",
                (_like(fragment),),
            ).fetchone()
    return row[0] if row else None


def get_adm4_code_for_token(fragment, adm2_prefix=None):
    with _connect() as connection:
        if adm2_prefix:
            row = connection.execute(
                """
                SELECT kode_wilayah FROM wilayah
                WHERE nama LIKE ? AND length(kode_wilayah) >= 9 AND kode_wilayah LIKE ?
                LIMIT 1
                """,
                (_like(fragment), f"{adm2_prefix}.%"),
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT kode_wilayah FROM wilayah
                WHERE nama LIKE ? AND length(kode_wilayah) >= 9
                LIMIT 1
                """,
                (_like(fragment),),
            ).fetchone()
    return row[0] if row else None


def get_adm4_in_adm3(adm3_code):
    with _connect() as connection:
        row = connection.execute(
            "SELECT kode_wilayah FROM wilayah WHERE kode_wilayah LIKE ? AND length(kode_wilayah) >= 9 LIMIT 1",
            (f"{adm3_code}.%",),
        ).fetchone()
    return row[0] if row else None


_ADDR_STOPWORDS = {
    "jalan", "jl", "jln", "no", "nomor", "rt", "rw", "kav", "kavling",
    "gang", "gg", "blok", "blk", "perum", "komplek", "kompleks", "gedung",
    "lantai", "lt", "rt/rw", "gg.", "jl.", "no.", "dsn", "dusun", "kp",
    "kampung", "pondok", "kota", "kab", "kabupaten", "prov", "provinsi",
    "indonesia", "barat", "timur", "selatan", "utara", "raya",
}
_ADDR_STOPWORDS_ADM4 = _ADDR_STOPWORDS | {
    "sudirman", "gatot", "subroto", "thamrin", "otista", "kebon", "sayur",
    "kemang", "senayan", "fatmawati", "rasuna", "mh", "hr", "mt", "jenderal",
    "jend", "doktor", "dr", "kh", "haji", "h", "letjen", "mayjen", "jendral",
}


def _tokens(address: str, stopwords: set[str]) -> list[str]:
    return [
        token.strip().rstrip(".,").lower()
        for token in address.replace(",", " ").split()
        if len(token.strip()) >= 3 and token.strip().rstrip(".,").lower() not in stopwords
    ]


def find_adm2_from_address(address):
    tokens = _tokens(address, _ADDR_STOPWORDS)
    for token in tokens:
        code3 = get_adm3_code(token)
        if code3:
            return code3[:5]
    for token in tokens:
        code = get_adm2_code(token)
        if code:
            return code
    return None


def find_adm4_from_address(address):
    tokens = _tokens(address, _ADDR_STOPWORDS_ADM4)
    adm2 = find_adm2_from_address(address)
    for token in tokens:
        code = get_adm4_code_for_token(token, adm2_prefix=adm2)
        if code:
            return code
    for token in tokens:
        code3 = get_adm3_code(token, adm2_prefix=adm2)
        if code3:
            code = get_adm4_in_adm3(code3)
            if code:
                return code
    for token in tokens:
        code = get_adm4_code_for_token(token)
        if code:
            return code
    return None


def find_adm4_from_location(location: dict | None, address: str = ""):
    location = location or {}
    if location.get("adm4_code"):
        return location["adm4_code"]
    adm2 = location.get("adm2_code")
    if not adm2:
        for value in (location.get("city"), location.get("county"), location.get("state")):
            if value:
                adm2 = get_adm2_code(value)
                if adm2:
                    break
    for value in (location.get("district"), location.get("suburb"), location.get("locality")):
        if value:
            code3 = get_adm3_code(value, adm2_prefix=adm2)
            if code3:
                return get_adm4_in_adm3(code3)
            code4 = get_adm4_code_for_token(value, adm2_prefix=adm2)
            if code4:
                return code4
    return find_adm4_from_address(address) if address else None


def save_simulation(input_addresses, result_data):
    import json

    with _connect() as connection:
        connection.execute(
            "INSERT INTO simulation_history (input_addresses, result_data) VALUES (?, ?)",
            (
                json.dumps(input_addresses, ensure_ascii=False),
                json.dumps(result_data, ensure_ascii=False),
            ),
        )
        connection.commit()
