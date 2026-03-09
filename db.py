# db.py — gerencia conexão e operações com o banco
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


# ══════════════════════════════════════════
# CACHE
# ══════════════════════════════════════════
def cache_get(chave: str):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT resposta FROM cache WHERE chave = %s;", (chave,))
                row = cur.fetchone()
                return row[0] if row else None
    except Exception as e:
        logger.warning(f"cache_get erro: {e}")
        return None


def cache_set(chave: str, resposta: str):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO cache (chave, resposta)
                    VALUES (%s, %s)
                    ON CONFLICT (chave) DO UPDATE SET resposta = EXCLUDED.resposta;
                """, (chave, resposta))
            conn.commit()
    except Exception as e:
        logger.warning(f"cache_set erro: {e}")


# ══════════════════════════════════════════
# CATÁLOGO DE RECEITAS
# ══════════════════════════════════════════
def carregar_catalogo():
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT chave, keywords, categoria, nome_pdf FROM receitas;")
                rows = cur.fetchall()

        db = {r["chave"]: {
            "keywords":  r["keywords"],
            "categoria": r["categoria"],
            "nome_pdf":  r["nome_pdf"],
        } for r in rows}

        receitas_quentes = [k for k, v in db.items() if v["categoria"] == "quente"]
        receitas_frias   = [k for k, v in db.items() if v["categoria"] == "frio"]
        return db, receitas_quentes, receitas_frias

    except Exception as e:
        logger.error(f"carregar_catalogo erro: {e}")
        return {}, [], []