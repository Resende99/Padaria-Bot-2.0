# db.py — gerencia conexão e operações com o banco
import os
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
RECEITAS_DB  = "receitas.json"

# Pool de conexões com timeout
try:
    _pool = pool.SimpleConnectionPool(1, 5, DATABASE_URL, connect_timeout=5)
    logger.info("Pool de conexões criado com sucesso.")
except Exception as e:
    logger.error(f"Erro ao criar pool de conexões: {e}")
    _pool = None


def get_conn():
    if _pool is None:
        raise RuntimeError("Pool não disponível")
    return _pool.getconn()

def release_conn(conn):
    if _pool and conn:
        _pool.putconn(conn)


# ══════════════════════════════════════════
# FALLBACK — carrega do JSON local
# ══════════════════════════════════════════
def _catalogo_do_json():
    try:
        with open(RECEITAS_DB, "r", encoding="utf-8") as f:
            db = json.load(f)
        receitas_quentes = [k for k, v in db.items() if v["categoria"] == "quente"]
        receitas_frias   = [k for k, v in db.items() if v["categoria"] == "frio"]
        logger.warning("Catálogo carregado do JSON local (fallback).")
        return db, receitas_quentes, receitas_frias
    except Exception as e:
        logger.error(f"Erro ao carregar JSON de fallback: {e}")
        return {}, [], []


# ══════════════════════════════════════════
# CACHE
# ══════════════════════════════════════════
def cache_get(chave: str):
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT resposta FROM cache WHERE chave = %s;", (chave,))
            row = cur.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.warning(f"cache_get erro: {e}")
        return None
    finally:
        release_conn(conn)


def cache_set(chave: str, resposta: str):
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO cache (chave, resposta)
                VALUES (%s, %s)
                ON CONFLICT (chave) DO UPDATE SET resposta = EXCLUDED.resposta;
            """, (chave, resposta))
        conn.commit()
    except Exception as e:
        logger.warning(f"cache_set erro: {e}")
    finally:
        release_conn(conn)


# ══════════════════════════════════════════
# ÚLTIMA RECEITA (substitui session)
# ══════════════════════════════════════════
def salvar_ultima_receita(session_id: str, nome: str, ingredientes: str, modo: str):
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ultima_receita (session_id, nome, ingredientes, modo, atualizado_em)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (session_id) DO UPDATE
                SET nome = EXCLUDED.nome,
                    ingredientes = EXCLUDED.ingredientes,
                    modo = EXCLUDED.modo,
                    atualizado_em = NOW();
            """, (session_id, nome, ingredientes, modo))
        conn.commit()
    except Exception as e:
        logger.warning(f"salvar_ultima_receita erro: {e}")
    finally:
        release_conn(conn)


def buscar_ultima_receita(session_id: str):
    conn = None
    try:
        conn = get_conn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT nome, ingredientes, modo FROM ultima_receita
                WHERE session_id = %s;
            """, (session_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.warning(f"buscar_ultima_receita erro: {e}")
        return None
    finally:
        release_conn(conn)


# ══════════════════════════════════════════
# HISTÓRICO DE CONVERSAS
# ══════════════════════════════════════════
def salvar_historico(session_id: str, mensagem: str, resposta: str):
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO historico (session_id, mensagem, resposta, criado_em)
                VALUES (%s, %s, %s, NOW());
            """, (session_id, mensagem, resposta))
        conn.commit()
    except Exception as e:
        logger.warning(f"salvar_historico erro: {e}")
    finally:
        release_conn(conn)


# ══════════════════════════════════════════
# CATÁLOGO DE RECEITAS
# ══════════════════════════════════════════
def carregar_catalogo():
    conn = None
    try:
        conn = get_conn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT chave, keywords, categoria, nome_pdf FROM receitas;")
            rows = cur.fetchall()

        if not rows:
            raise RuntimeError("Nenhuma receita no banco.")

        db = {r["chave"]: {
            "keywords":  r["keywords"],
            "categoria": r["categoria"],
            "nome_pdf":  r["nome_pdf"],
        } for r in rows}

        receitas_quentes = [k for k, v in db.items() if v["categoria"] == "quente"]
        receitas_frias   = [k for k, v in db.items() if v["categoria"] == "frio"]
        logger.info(f"Catálogo carregado do banco: {len(db)} receitas.")
        return db, receitas_quentes, receitas_frias

    except Exception as e:
        logger.error(f"carregar_catalogo erro: {e} — usando fallback JSON.")
        return _catalogo_do_json()
    finally:
        release_conn(conn)