import sqlite3
import os

_DB = os.path.join(os.path.dirname(__file__), "database_notebooks.db")


def setup():
    conn = sqlite3.connect(_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notebooks (
            placa_id         TEXT PRIMARY KEY,
            numero_serie     TEXT,
            usuario_anterior TEXT,
            usuario_atual    TEXT,
            senha            TEXT,
            setor            TEXT,
            cargo            TEXT,
            nota_fiscal      TEXT,
            perifericos      TEXT,
            observacao       TEXT,
            situacao         TEXT DEFAULT 'Não definido',
            fotos            TEXT DEFAULT 'Não',
            obra             TEXT,
            autocad          TEXT
        )
    """)
    for col in ["obra", "autocad", "fotos", "perifericos"]:
        try:
            cur.execute(f"ALTER TABLE notebooks ADD COLUMN {col} TEXT")
        except Exception:
            pass
    conn.commit()
    conn.close()


def get_all(situacao=None, obra=None, search=None):
    conn = sqlite3.connect(_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    q = "SELECT * FROM notebooks WHERE 1=1"
    params = []
    if situacao:
        q += " AND situacao = ?"
        params.append(situacao)
    if obra:
        q += " AND obra = ?"
        params.append(obra)
    if search:
        q += " AND (placa_id LIKE ? OR usuario_atual LIKE ? OR usuario_anterior LIKE ? OR setor LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s])
    q += " ORDER BY placa_id"
    cur.execute(q, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_one(placa_id):
    conn = sqlite3.connect(_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM notebooks WHERE placa_id = ?", (placa_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def save(data):
    conn = sqlite3.connect(_DB)
    cur = conn.cursor()
    cols = list(data.keys())
    vals = [data[c] for c in cols]
    placeholders = ", ".join("?" * len(cols))
    update_clause = ", ".join(
        f"{c} = excluded.{c}" for c in cols if c != "placa_id"
    )
    sql = (
        f"INSERT INTO notebooks ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT(placa_id) DO UPDATE SET {update_clause}"
    )
    cur.execute(sql, vals)
    conn.commit()
    conn.close()


def delete(placa_id):
    conn = sqlite3.connect(_DB)
    cur = conn.cursor()
    cur.execute("DELETE FROM notebooks WHERE placa_id = ?", (placa_id,))
    conn.commit()
    conn.close()
