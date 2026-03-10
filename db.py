# db.py
import os
import json
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
RECEITAS_DB  = "receitas.json"

# ── Engine com pool e timeout ─────────────────────────
try:
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,
        pool_timeout=5,
        pool_pre_ping=True,  # testa conexão antes de usar
        connect_args={"connect_timeout": 5},
    )
    Session = sessionmaker(bind=engine)
    logger.info("Engine SQLAlchemy criado com sucesso.")
except Exception as e:
    logger.error(f"Erro ao criar engine: {e}")
    engine  = None
    Session = None


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
    if not Session:
        return None
    try:
        with Session() as s:
            row = s.execute(
                text("SELECT resposta FROM cache WHERE chave = :chave"),
                {"chave": chave}
            ).fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.warning(f"cache_get erro: {e}")
        return None


def cache_set(chave: str, resposta: str):
    if not Session:
        return
    try:
        with Session() as s:
            s.execute(text("""
                INSERT INTO cache (chave, resposta)
                VALUES (:chave, :resposta)
                ON CONFLICT (chave) DO UPDATE SET resposta = EXCLUDED.resposta
            """), {"chave": chave, "resposta": resposta})
            s.commit()
    except Exception as e:
        logger.warning(f"cache_set erro: {e}")


# ══════════════════════════════════════════
# ÚLTIMA RECEITA
# ══════════════════════════════════════════
def salvar_ultima_receita(session_id: str, nome: str, ingredientes: str, modo: str):
    if not Session:
        return
    try:
        with Session() as s:
            s.execute(text("""
                INSERT INTO ultima_receita (session_id, nome, ingredientes, modo, atualizado_em)
                VALUES (:sid, :nome, :ing, :modo, NOW())
                ON CONFLICT (session_id) DO UPDATE
                SET nome = EXCLUDED.nome,
                    ingredientes = EXCLUDED.ingredientes,
                    modo = EXCLUDED.modo,
                    atualizado_em = NOW()
            """), {"sid": session_id, "nome": nome, "ing": ingredientes, "modo": modo})
            s.commit()
    except Exception as e:
        logger.warning(f"salvar_ultima_receita erro: {e}")


def buscar_ultima_receita(session_id: str):
    if not Session:
        return None
    try:
        with Session() as s:
            row = s.execute(
                text("SELECT nome, ingredientes, modo FROM ultima_receita WHERE session_id = :sid"),
                {"sid": session_id}
            ).fetchone()
            return {"nome": row[0], "ingredientes": row[1], "modo": row[2]} if row else None
    except Exception as e:
        logger.warning(f"buscar_ultima_receita erro: {e}")
        return None


# ══════════════════════════════════════════
# HISTÓRICO
# ══════════════════════════════════════════
def salvar_historico(session_id: str, mensagem: str, resposta: str):
    if not Session:
        return
    try:
        with Session() as s:
            s.execute(text("""
                INSERT INTO historico (session_id, mensagem, resposta, criado_em)
                VALUES (:sid, :msg, :resp, NOW())
            """), {"sid": session_id, "msg": mensagem, "resp": resposta})
            s.commit()
    except Exception as e:
        logger.warning(f"salvar_historico erro: {e}")


# ══════════════════════════════════════════
# CATÁLOGO DE RECEITAS
# ══════════════════════════════════════════
def carregar_catalogo():
    if not Session:
        return _catalogo_do_json()
    try:
        with Session() as s:
            rows = s.execute(
                text("SELECT chave, keywords, categoria, nome_pdf FROM receitas")
            ).fetchall()

        if not rows:
            raise RuntimeError("Nenhuma receita no banco.")

        db = {r[0]: {
            "keywords":  r[1],
            "categoria": r[2],
            "nome_pdf":  r[3],
        } for r in rows}

        receitas_quentes = [k for k, v in db.items() if v["categoria"] == "quente"]
        receitas_frias   = [k for k, v in db.items() if v["categoria"] == "frio"]
        logger.info(f"Catálogo carregado do banco: {len(db)} receitas.")
        return db, receitas_quentes, receitas_frias

    except Exception as e:
        logger.error(f"carregar_catalogo erro: {e} — usando fallback JSON.")
        return _catalogo_do_json()