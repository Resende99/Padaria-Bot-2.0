# db.py
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

try:
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,
        pool_timeout=5,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )
    Session = sessionmaker(bind=engine)
    logger.info("Engine SQLAlchemy criado com sucesso.")
except Exception as e:
    logger.error(f"Erro ao criar engine: {e}")
    engine  = None
    Session = None


# ══════════════════════════════════════════
# CATÁLOGO
# ══════════════════════════════════════════
def carregar_catalogo():
    if not Session:
        return {}, [], []
    try:
        with Session() as s:
            rows = s.execute(
                text("SELECT id, nome, keywords, categoria, ingredientes, modo FROM receitas")
            ).fetchall()

        if not rows:
            logger.warning("Nenhuma receita no banco.")
            return {}, [], []

        db = {}
        for r in rows:
            db[r[1]] = {
                "id":          r[0],
                "keywords":    r[2],
                "categoria":   r[3],
                "ingredientes": r[4],
                "modo":        r[5],
            }

        receitas_quentes = [k for k, v in db.items() if v["categoria"] == "quente"]
        receitas_frias   = [k for k, v in db.items() if v["categoria"] == "frio"]
        logger.info(f"Catálogo carregado: {len(db)} receitas.")
        return db, receitas_quentes, receitas_frias

    except Exception as e:
        logger.error(f"carregar_catalogo erro: {e}")
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
# ADMIN — CRUD RECEITAS
# ══════════════════════════════════════════
def listar_receitas():
    if not Session:
        return []
    try:
        with Session() as s:
            rows = s.execute(
                text("SELECT id, nome, keywords, categoria FROM receitas ORDER BY nome")
            ).fetchall()
            return [{"id": r[0], "nome": r[1], "keywords": r[2], "categoria": r[3]} for r in rows]
    except Exception as e:
        logger.error(f"listar_receitas erro: {e}")
        return []


def buscar_receita_por_id(receita_id: int):
    if not Session:
        return None
    try:
        with Session() as s:
            row = s.execute(
                text("SELECT id, nome, keywords, categoria, ingredientes, modo FROM receitas WHERE id = :id"),
                {"id": receita_id}
            ).fetchone()
            if not row:
                return None
            return {"id": row[0], "nome": row[1], "keywords": row[2], "categoria": row[3], "ingredientes": row[4], "modo": row[5]}
    except Exception as e:
        logger.error(f"buscar_receita_por_id erro: {e}")
        return None


def salvar_receita(nome, keywords, categoria, ingredientes, modo, receita_id=None):
    if not Session:
        return False
    try:
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        with Session() as s:
            if receita_id:
                s.execute(text("""
                    UPDATE receitas SET nome=:nome, keywords=:kw, categoria=:cat,
                    ingredientes=:ing, modo=:modo WHERE id=:id
                """), {"nome": nome, "kw": kw_list, "cat": categoria, "ing": ingredientes, "modo": modo, "id": receita_id})
            else:
                s.execute(text("""
                    INSERT INTO receitas (nome, keywords, categoria, ingredientes, modo)
                    VALUES (:nome, :kw, :cat, :ing, :modo)
                """), {"nome": nome, "kw": kw_list, "cat": categoria, "ing": ingredientes, "modo": modo})
            s.commit()
        return True
    except Exception as e:
        logger.error(f"salvar_receita erro: {e}")
        return False


def deletar_receita(receita_id: int):
    if not Session:
        return False
    try:
        with Session() as s:
            s.execute(text("DELETE FROM receitas WHERE id = :id"), {"id": receita_id})
            s.commit()
        return True
    except Exception as e:
        logger.error(f"deletar_receita erro: {e}")
        return False