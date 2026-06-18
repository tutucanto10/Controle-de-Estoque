import os
import threading
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv

# Carrega credenciais do .env (silencioso se não existir)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

_pool: ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()
_pool_failed = False  # evita retry loop se o banco estiver fora


def _get_db_params() -> dict:
    return {
        "host":     os.environ.get("DB_HOST", ""),
        "database": os.environ.get("DB_NAME", "postgres"),
        "user":     os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", ""),
        "port":     int(os.environ.get("DB_PORT", "5432")),
    }


def _ensure_pool() -> ThreadedConnectionPool | None:
    global _pool, _pool_failed
    if _pool_failed:
        return None
    with _pool_lock:
        if _pool is None or _pool.closed:
            try:
                _pool = ThreadedConnectionPool(minconn=1, maxconn=5, **_get_db_params())
            except Exception:
                _pool_failed = True
                return None
    return _pool


class _PooledConn:
    """Wrapper que devolve a conexão ao pool ao invés de fechá-la."""

    def __init__(self, conn, pool: ThreadedConnectionPool):
        self._conn = conn
        self._pool = pool

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def cursor(self, *args, **kwargs):
        return self._conn.cursor(*args, **kwargs)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    @property
    def closed(self):
        return self._conn.closed

    def close(self):
        try:
            if not self._conn.closed:
                self._pool.putconn(self._conn)
        except Exception:
            try:
                self._conn.close()
            except Exception:
                pass


def get_db_connection():
    """Retorna conexão do pool se disponível, caso contrário cria uma direta."""
    pool = _ensure_pool()
    if pool is not None:
        try:
            conn = pool.getconn()
            return _PooledConn(conn, pool)
        except Exception:
            pass
    # fallback: conexão direta (sem pool)
    return psycopg2.connect(**_get_db_params())


# --- Wrappers de consulta ---

def fetch_all(query, params=None):
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params or ())
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


def execute_query(query, params=None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params or ())
        conn.commit()
        cur.close()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --- Utilitários ---

def get_obra_id(obra_nome):
    rows = fetch_all("SELECT id FROM obras WHERE nome = %s", (obra_nome,))
    return rows[0]["id"] if rows else None


def get_obras():
    """Retorna lista de nomes de obras ordenadas."""
    try:
        rows = fetch_all("SELECT nome FROM obras ORDER BY nome")
        return [r["nome"] for r in rows] if rows else []
    except Exception:
        return []


def get_dashboard_stats(obra_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT
                COALESCE(SUM(qtd_total), 0)    AS total,
                COALESCE(SUM(qtd_em_uso), 0)   AS em_uso,
                COALESCE(SUM(qtd_estoque), 0)  AS disponivel
            FROM itens WHERE obra_id = %s
            """,
            (obra_id,),
        )
        stats = cur.fetchone() or {}

        cur.execute(
            """
            SELECT COUNT(*) AS manutencao
            FROM itens
            WHERE obra_id = %s AND status IN ('Em Manutenção', 'Quebrado')
            """,
            (obra_id,),
        )
        manutencao = cur.fetchone() or {}
        return {
            "total": stats.get("total", 0),
            "em_uso": stats.get("em_uso", 0),
            "disponivel": stats.get("disponivel", 0),
            "manutencao": manutencao.get("manutencao", 0),
        }
    finally:
        conn.close()


def get_items_by_obra(obra_id, search_term=""):
    query = """
        SELECT i.*, c.nome AS categoria_nome
        FROM itens i
        JOIN categorias c ON i.categoria_id = c.id
        WHERE i.obra_id = %s
    """
    params = [obra_id]
    if search_term:
        query += " AND (i.nome ILIKE %s OR i.numero_serie ILIKE %s)"
        params.extend([f"%{search_term}%", f"%{search_term}%"])
    return fetch_all(query, tuple(params))


def log_movement(cur, item_id, tipo, quantidade, observacao, responsavel=None):
    cur.execute(
        """
        INSERT INTO movimentacoes (item_id, tipo, quantidade, observacao, responsavel, data)
        VALUES (%s, %s, %s, %s, %s, NOW())
        """,
        (item_id, tipo, quantidade, observacao, responsavel),
    )


# --- Operações de estoque ---

def dar_baixa_item(item_id, quantidade, observacao, responsavel):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        log_movement(cur, item_id, "baixa", quantidade, observacao, responsavel)
        conn.commit()
        return True, "Baixa registrada com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao registrar baixa: {e}"
    finally:
        conn.close()


def transfer_item(item_id, obra_id_destino, destino_nome, quantidade, observacao, responsavel):
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            "SELECT nome, categoria_id, qtd_estoque, qtd_em_uso, condicao, status FROM itens WHERE id = %s",
            (item_id,),
        )
        item = cur.fetchone()
        if not item:
            raise Exception("Item não encontrado para transferência.")

        nome, categoria_id, qtd_estoque, qtd_em_uso, condicao, status = item

        if quantidade > qtd_estoque:
            raise Exception(
                f"Quantidade solicitada ({quantidade}) maior que o estoque disponível ({qtd_estoque})."
            )

        cur.execute(
            "UPDATE itens SET qtd_estoque = %s WHERE id = %s",
            (qtd_estoque - quantidade, item_id),
        )

        cur.execute(
            "SELECT id, qtd_estoque FROM itens WHERE obra_id = %s AND nome = %s AND categoria_id = %s",
            (obra_id_destino, nome, categoria_id),
        )
        destino = cur.fetchone()

        if destino:
            destino_id, qtd_destino = destino
            cur.execute(
                "UPDATE itens SET qtd_estoque = %s WHERE id = %s",
                (qtd_destino + quantidade, destino_id),
            )
            destino_item_id = destino_id
        else:
            cur.execute(
                """
                INSERT INTO itens (obra_id, categoria_id, nome, numero_serie, qtd_total, qtd_estoque, qtd_em_uso, condicao, status)
                SELECT %s, categoria_id, nome, numero_serie, %s, %s, 0, condicao, status
                FROM itens WHERE id = %s
                RETURNING id
                """,
                (obra_id_destino, quantidade, quantidade, item_id),
            )
            destino_item_id = cur.fetchone()[0]

        cur.execute(
            "SELECT nome FROM obras WHERE id = (SELECT obra_id FROM itens WHERE id = %s)",
            (item_id,),
        )
        row_origem = cur.fetchone()
        nome_origem = row_origem[0] if row_origem else "Obra desconhecida"

        log_movement(
            cur, item_id, "Transferência (Saída)", quantidade,
            f"{observacao} | Destino: {destino_nome}", responsavel,
        )
        log_movement(
            cur, destino_item_id, "Transferência (Entrada)", quantidade,
            f"Recebido de {nome_origem}", responsavel,
        )

        conn.commit()
        return True, f"{quantidade} unidade(s) transferida(s) para {destino_nome}."

    except Exception as e:
        conn.rollback()
        return False, f"Erro ao transferir item: {e}"
    finally:
        conn.close()


def add_item(data, responsavel=None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO itens (obra_id, categoria_id, nome, numero_serie, qtd_total, qtd_estoque, qtd_em_uso, condicao, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                data["obra_id"],
                data["categoria_id"],
                data["nome"],
                data["numero_serie"],
                data["qtd_total"],
                data["qtd_estoque"],
                data.get("qtd_em_uso", 0),
                data["condicao"],
                data["status"],
            ),
        )
        item_id = cur.fetchone()[0]
        log_movement(cur, item_id, "Entrada", data["qtd_total"], "Item novo cadastrado.", responsavel)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_item(data, responsavel=None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE itens
            SET nome=%s, numero_serie=%s, categoria_id=%s, qtd_total=%s,
                qtd_em_uso=%s, qtd_estoque=%s, condicao=%s, status=%s
            WHERE id=%s
            """,
            (
                data["nome"],
                data["numero_serie"],
                data["categoria_id"],
                data["qtd_total"],
                data.get("qtd_em_uso", 0),
                data["qtd_estoque"],
                data["condicao"],
                data["status"],
                data["id"],
            ),
        )
        log_movement(cur, data["id"], "Atualização", 0, f"Item '{data['nome']}' atualizado.", responsavel)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def devolver_item(item_id, quantidade, observacao="Retorno ao estoque", responsavel=None):
    item = fetch_all("SELECT qtd_em_uso, qtd_estoque FROM itens WHERE id=%s", (item_id,))
    if not item:
        return False, "Item não encontrado."
    item = item[0]
    if quantidade > item["qtd_em_uso"]:
        return False, "Quantidade de retorno maior que o que está em uso."

    novo_em_uso = item["qtd_em_uso"] - quantidade
    novo_estoque = item["qtd_estoque"] + quantidade

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE itens SET qtd_em_uso=%s, qtd_estoque=%s WHERE id=%s",
            (novo_em_uso, novo_estoque, item_id),
        )
        log_movement(cur, item_id, "Devolução", quantidade, observacao, responsavel)
        conn.commit()
        return True, "Item devolvido com sucesso."
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao devolver item: {e}"
    finally:
        conn.close()


def delete_item(item_id: int) -> tuple[bool, str]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        def _table_exists(table_name: str) -> bool:
            full = table_name if "." in table_name else f"public.{table_name}"
            cur.execute("SELECT to_regclass(%s)", (full,))
            return cur.fetchone()[0] is not None

        if _table_exists("movimentacoes"):
            cur.execute("DELETE FROM movimentacoes WHERE item_id = %s", (item_id,))
        if _table_exists("anexos"):
            cur.execute("DELETE FROM anexos WHERE item_id = %s", (item_id,))

        cur.execute("DELETE FROM itens WHERE id = %s", (item_id,))
        if cur.rowcount == 0:
            conn.rollback()
            return False, "Item não encontrado."

        conn.commit()
        return True, "Item excluído com sucesso."
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao excluir item: {e}"
    finally:
        conn.close()


def get_categorias():
    return fetch_all("SELECT * FROM categorias ORDER BY nome")


def get_movimentacoes_do_item(item_id, limit=200):
    return fetch_all(
        """
        SELECT m.data, m.tipo, m.quantidade,
               COALESCE(m.responsavel, '') AS responsavel,
               COALESCE(m.observacao, '') AS observacao
        FROM movimentacoes m
        WHERE m.item_id = %s
        ORDER BY m.data DESC
        LIMIT %s
        """,
        (item_id, limit),
    )


def get_items_simple(obra_id):
    return fetch_all(
        "SELECT id, nome, qtd_estoque, qtd_em_uso, status FROM itens WHERE obra_id = %s ORDER BY id",
        (obra_id,),
    )


def get_movimentacoes_por_usuario(username):
    return fetch_all(
        "SELECT * FROM movimentacoes WHERE responsavel = %s ORDER BY data DESC",
        (username,),
    )


def get_movimentacoes_por_periodo(obra_id, data_inicio, data_fim):
    return fetch_all(
        """
        SELECT m.id, m.item_id, i.nome, i.obra_id,
               m.tipo, m.quantidade, m.observacao,
               m.responsavel, m.data
        FROM movimentacoes m
        JOIN itens i ON i.id = m.item_id
        WHERE i.obra_id = %s
          AND m.data::date BETWEEN %s AND %s
        ORDER BY m.data DESC
        """,
        (obra_id, data_inicio, data_fim),
    )


def get_item_nome(item_id: int) -> str:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT nome FROM itens WHERE id = %s", (item_id,))
        r = cur.fetchone()
        return r[0] if r else str(item_id)
    except Exception:
        return str(item_id)
    finally:
        conn.close()


# --- Preferências de usuário ---

def ensure_preferences_table():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS preferencias_usuarios (
                username TEXT PRIMARY KEY,
                tema     TEXT NOT NULL DEFAULT 'light'
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def upsert_user_theme(username: str, tema: str):
    ensure_preferences_table()
    execute_query(
        """
        INSERT INTO preferencias_usuarios (username, tema)
        VALUES (%s, %s)
        ON CONFLICT (username) DO UPDATE SET tema = EXCLUDED.tema
        """,
        (username, tema),
    )


def get_user_theme(username: str):
    ensure_preferences_table()
    rows = fetch_all(
        "SELECT tema FROM preferencias_usuarios WHERE username = %s", (username,)
    )
    return rows[0]["tema"] if rows else None


# --- Usuários ---

def ensure_usuarios_table():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                username TEXT PRIMARY KEY,
                email    TEXT NOT NULL,
                senha    TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_usuario(username: str):
    ensure_usuarios_table()
    rows = fetch_all(
        "SELECT username, email, senha FROM usuarios WHERE username = %s", (username,)
    )
    return rows[0] if rows else None


def upsert_usuario(username: str, email: str, senha: str):
    ensure_usuarios_table()
    execute_query(
        """
        INSERT INTO usuarios (username, email, senha)
        VALUES (%s, %s, %s)
        ON CONFLICT (username) DO UPDATE SET email = EXCLUDED.email, senha = EXCLUDED.senha
        """,
        (username, email, senha),
    )


# --- Estrutura do banco ---

def ensure_correct_table_structure():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'itens' AND column_name = 'qtd_em_uso'
            """
        )
        if not cur.fetchone():
            cur.execute("ALTER TABLE itens ADD COLUMN qtd_em_uso INTEGER DEFAULT 0")

        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'itens' AND column_name = 'qtd_uso'
            """
        )
        if cur.fetchone():
            cur.execute(
                "UPDATE itens SET qtd_em_uso = qtd_uso WHERE qtd_em_uso = 0 AND qtd_uso IS NOT NULL"
            )
            cur.execute("ALTER TABLE itens DROP COLUMN qtd_uso")

        conn.commit()
    except Exception as e:
        print(f"[ERRO] Falha ao verificar estrutura: {e}")
        conn.rollback()
    finally:
        conn.close()


def setup_database():
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS obras (
                id   SERIAL PRIMARY KEY,
                nome TEXT UNIQUE NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS categorias (
                id   SERIAL PRIMARY KEY,
                nome TEXT UNIQUE NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS itens (
                id           SERIAL PRIMARY KEY,
                obra_id      INTEGER NOT NULL REFERENCES obras(id),
                categoria_id INTEGER NOT NULL REFERENCES categorias(id),
                nome         TEXT NOT NULL,
                numero_serie TEXT,
                qtd_total    INTEGER DEFAULT 0,
                qtd_estoque  INTEGER DEFAULT 0,
                qtd_em_uso   INTEGER DEFAULT 0,
                condicao     TEXT,
                status       TEXT,
                possui       TEXT DEFAULT 'Sim',
                funcionando  TEXT DEFAULT 'Sim',
                observacao   TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id          SERIAL PRIMARY KEY,
                item_id     INTEGER NOT NULL REFERENCES itens(id),
                data        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tipo        TEXT NOT NULL,
                quantidade  INTEGER NOT NULL,
                observacao  TEXT,
                responsavel TEXT
            )
            """
        )

        obras = [
            "Domma", "Seleto Primavera", "Unic São Gonçalo", "PRIME Caxias",
            "LIV Primavera", "Reserva Equitativa", "Encantado", "Seleto Inhaúma",
        ]
        categorias = [
            "Notebook", "Mouse", "Teclado", "Carregador", "Monitor",
            "Relógio de Ponto", "Firewall", "Switch", "Roteador", "Nobreak",
            "DVR das Câmeras", "Câmeras",
        ]
        for o in obras:
            cur.execute(
                "INSERT INTO obras (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING", (o,)
            )
        for c in categorias:
            cur.execute(
                "INSERT INTO categorias (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING", (c,)
            )

        conn.commit()
    except Exception as e:
        print(f"[ERRO] setup_database: {e}")
        conn.rollback()
    finally:
        conn.close()

    ensure_correct_table_structure()


def ensure_notebook_schema():
    """Garante que a tabela notebooks no SQLite tenha todas as colunas necessárias."""
    from controle_estoque import db_connect_notebooks
    conn, cursor = db_connect_notebooks()
    cursor.execute("PRAGMA table_info(notebooks)")
    cols = {row[1] for row in cursor.fetchall()}
    for col_name, ddl in [
        ("obra",       "ALTER TABLE notebooks ADD COLUMN obra TEXT"),
        ("autocad",    "ALTER TABLE notebooks ADD COLUMN autocad TEXT DEFAULT 'Não'"),
        ("fotos",      "ALTER TABLE notebooks ADD COLUMN fotos TEXT DEFAULT 'Não'"),
        ("perifericos","ALTER TABLE notebooks ADD COLUMN perifericos TEXT"),
    ]:
        if col_name not in cols:
            try:
                cursor.execute(ddl)
            except Exception:
                pass
    conn.commit()
    conn.close()


# --- Realtime (desativado) ---

def start_realtime_listener(callback):
    return None


def safe_callback(callback):
    try:
        if callback and callable(callback):
            callback()
    except Exception as e:
        print(f"[ERRO] Falha no callback do listener: {e}")
