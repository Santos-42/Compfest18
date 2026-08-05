"""Inisialisasi SQLite + auto-import wilayah.sql (91.000+ kode wilayah BMKG)."""
import sqlite3

from core.config import REPO_ROOT, settings

DB_PATH = settings.DATABASE_PATH


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(DB_PATH))


def init_database():
    """Panggil saat startup. Buat tabel + import wilayah.sql jika belum ada."""
    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS simulation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            input_addresses TEXT,
            result_data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='wilayah'")
    if not cur.fetchone():
        sql_file = REPO_ROOT / "data" / "wilayah.sql"
        if sql_file.exists():
            # wilayah.sql hanya berisi INSERT (kode, nama) — buat tabel dulu
            cur.execute(
                """
                CREATE TABLE wilayah (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kode TEXT,
                    nama TEXT
                )
                """
            )
            conn.executescript(sql_file.read_text(encoding="utf-8"))
            conn.commit()
            # Tambah kolom turunan untuk kompatibilitas SDD (kode_wilayah, provinsi, dll)
            cur.execute("ALTER TABLE wilayah ADD COLUMN kode_wilayah TEXT")
            cur.execute("ALTER TABLE wilayah ADD COLUMN kecamatan TEXT")
            cur.execute("ALTER TABLE wilayah ADD COLUMN kabupaten TEXT")
            cur.execute("ALTER TABLE wilayah ADD COLUMN provinsi TEXT")
            conn.commit()
            _fill_wilayah_parents(conn)
            conn.commit()
            print("OK:  Database wilayah berhasil di-import dari wilayah.sql")
        else:
            print(f"ERROR:  File wilayah.sql tidak ditemukan di {sql_file}")
    else:
        print("INFO: Database wilayah sudah ada, skip import.")

    conn.close()


def _fill_wilayah_parents(conn):
    """Derivasi kolom provinsi/kabupaten/kecamatan dari hierarki kode adm1-adm4.

    wilayah.sql berisi (kode, nama); kode '11.01.01.2001' berarti
    provinsi '11', kabupaten '11.01', kecamatan '11.01.01'.
    """
    cur = conn.cursor()
    cur.execute("SELECT id, kode FROM wilayah")
    rows = cur.fetchall()
    cur.execute("SELECT kode, nama FROM wilayah")
    name_by_code = dict(cur.fetchall())

    updates = []
    for rid, kode in rows:
        parts = kode.split(".")
        prov = name_by_code.get(parts[0])
        kab = name_by_code.get(".".join(parts[:2])) if len(parts) >= 2 else None
        kec = name_by_code.get(".".join(parts[:3])) if len(parts) >= 3 else None
        updates.append((kode, kec, kab, prov, rid))
    cur.executemany(
        "UPDATE wilayah SET kode_wilayah=?, kecamatan=?, kabupaten=?, provinsi=? WHERE id=?",
        updates,
    )


def get_adm4_code(fragment):
    """Cari kode adm4 (kelurahan/desa) berdasarkan nama/fragmen nama."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT kode_wilayah FROM wilayah WHERE nama LIKE ? LIMIT 1",
        (f"%{fragment}%",),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def get_adm2_code(fragment):
    """Cari kode kabupaten/kota (adm2, format 11.01) untuk query cuaca BMKG."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT kode_wilayah FROM wilayah WHERE (nama LIKE ? OR kabupaten LIKE ?) AND length(kode_wilayah)=5 LIMIT 1",
        (f"%{fragment}%", f"%{fragment}%"),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def get_adm4_code_for_token(fragment):
    """Cari kode adm4 (kelurahan/desa, format 11.01.01.2001) dari nama wilayah."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT kode_wilayah FROM wilayah WHERE nama LIKE ? AND length(kode_wilayah) >= 9 LIMIT 1",
        (f"%{fragment}%",),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def find_adm4_from_address(address):
    """Coba pecah alamat jadi token, cocokkan dengan kode adm4 (kelurahan/desa)."""
    tokens = [
        t.strip().rstrip(".,")
        for t in address.replace(",", " ").split()
        if len(t.strip()) >= 3
    ]
    for token in tokens:
        code = get_adm4_code_for_token(token)
        if code:
            return code
    return None


def find_adm2_from_address(address):
    """Coba pecah alamat jadi token, lalu cocokkan dengan tabel wilayah."""
    tokens = [
        t.strip().rstrip(".,")
        for t in address.replace(",", " ").split()
        if len(t.strip()) >= 3
    ]
    for token in tokens:
        code = get_adm2_code(token)
        if code:
            return code
    return None


def save_simulation(input_addresses, result_data):
    """Simpan riwayat simulasi (untuk video demo)."""
    import json

    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO simulation_history (input_addresses, result_data) VALUES (?, ?)",
        (json.dumps(input_addresses, ensure_ascii=False), json.dumps(result_data, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()
