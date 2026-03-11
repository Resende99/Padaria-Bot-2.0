# db.py
import os
import json
import logging
import unicodedata
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
RECEITAS_JSON = "receitas.json"

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


def _norm(s):
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii").lower()


# ══════════════════════════════════════════
# FALLBACK JSON
# ══════════════════════════════════════════
def _catalogo_do_json():
    try:
        with open(RECEITAS_JSON, "r", encoding="utf-8") as f:
            db = json.load(f)
        quentes = [k for k, v in db.items() if v["categoria"] == "quente"]
        frias   = [k for k, v in db.items() if v["categoria"] == "frio"]
        logger.warning("Catálogo carregado do JSON local (fallback).")
        return db, quentes, frias
    except Exception as e:
        logger.error(f"Erro ao carregar JSON fallback: {e}")
        return {}, [], []


# ══════════════════════════════════════════
# CATÁLOGO
# ══════════════════════════════════════════
def carregar_catalogo():
    if not Session:
        return _catalogo_do_json()
    try:
        with Session() as s:
            rows = s.execute(
                text("SELECT id, nome, keywords, categoria FROM receitas")
            ).fetchall()
        if not rows:
            raise RuntimeError("Nenhuma receita no banco.")
        db = {}
        for r in rows:
            db[r[1]] = {
                "id":        r[0],
                "nome":      r[1],
                "keywords":  r[2],
                "categoria": r[3],
            }
        quentes = [k for k, v in db.items() if v["categoria"] == "quente"]
        frias   = [k for k, v in db.items() if v["categoria"] == "frio"]
        logger.info(f"Catálogo carregado: {len(db)} receitas.")
        return db, quentes, frias
    except Exception as e:
        logger.error(f"carregar_catalogo erro: {e} — fallback JSON.")
        return _catalogo_do_json()


# ══════════════════════════════════════════
# BUSCA RECEITA COMPLETA
# ══════════════════════════════════════════
def buscar_receita_completa(mensagem: str, db_catalogo: dict):
    if not Session:
        return None
    m = _norm(mensagem)
    chave = None
    for k, info in db_catalogo.items():
        if any(_norm(kw) in m for kw in info["keywords"]):
            chave = k
            break
    if not chave:
        return None
    receita_id = db_catalogo[chave].get("id")
    if not receita_id:
        return None
    try:
        with Session() as s:
            row = s.execute(
                text("SELECT id, nome, ingredientes, modo FROM receitas WHERE id = :id"),
                {"id": receita_id}
            ).fetchone()
            if row:
                return {"id": row[0], "nome": row[1], "ingredientes": row[2], "modo": row[3]}
            return None
    except Exception as e:
        logger.warning(f"buscar_receita_completa erro: {e}")
        return None


# ══════════════════════════════════════════
# CACHE
# ══════════════════════════════════════════
def cache_get(chave: str):
    if not Session:
        return None
    try:
        with Session() as s:
            row = s.execute(
                text("SELECT resposta FROM cache WHERE chave = :c"),
                {"c": chave}
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
                VALUES (:c, :r)
                ON CONFLICT (chave) DO UPDATE SET resposta = EXCLUDED.resposta
            """), {"c": chave, "r": resposta})
            s.commit()
    except Exception as e:
        logger.warning(f"cache_set erro: {e}")


# ══════════════════════════════════════════
# ÚLTIMA RECEITA
# ══════════════════════════════════════════
def salvar_ultima_receita(session_id: str, receita_id: int):
    if not Session:
        return
    try:
        with Session() as s:
            s.execute(text("""
                INSERT INTO ultima_receita (session_id, receita_id, atualizado_em)
                VALUES (:sid, :rid, NOW())
                ON CONFLICT (session_id) DO UPDATE
                SET receita_id = EXCLUDED.receita_id, atualizado_em = NOW()
            """), {"sid": session_id, "rid": receita_id})
            s.commit()
    except Exception as e:
        logger.warning(f"salvar_ultima_receita erro: {e}")


def buscar_ultima_receita(session_id: str):
    if not Session:
        return None
    try:
        with Session() as s:
            row = s.execute(text("""
                SELECT r.id, r.nome, r.ingredientes, r.modo
                FROM ultima_receita u
                JOIN receitas r ON r.id = u.receita_id
                WHERE u.session_id = :sid
            """), {"sid": session_id}).fetchone()
            if row:
                return {"id": row[0], "nome": row[1], "ingredientes": row[2], "modo": row[3]}
            return None
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
# ADMIN — CRUD
# ══════════════════════════════════════════
def listar_receitas():
    if not Session:
        return []
    try:
        with Session() as s:
            rows = s.execute(
                text("SELECT id, nome, keywords, categoria FROM receitas ORDER BY categoria, nome")
            ).fetchall()
            return [{"id": r[0], "nome": r[1], "keywords": r[2], "categoria": r[3]} for r in rows]
    except Exception as e:
        logger.error(f"listar_receitas erro: {e}")
        return []


def obter_receita(receita_id: int):
    if not Session:
        return None
    try:
        with Session() as s:
            row = s.execute(
                text("SELECT id, nome, keywords, categoria, ingredientes, modo FROM receitas WHERE id = :id"),
                {"id": receita_id}
            ).fetchone()
            if row:
                return {"id": row[0], "nome": row[1], "keywords": row[2], "categoria": row[3], "ingredientes": row[4], "modo": row[5]}
            return None
    except Exception as e:
        logger.error(f"obter_receita erro: {e}")
        return None


def criar_receita(nome, keywords, categoria, ingredientes, modo):
    if not Session:
        return False
    try:
        with Session() as s:
            s.execute(text("""
                INSERT INTO receitas (nome, keywords, categoria, ingredientes, modo)
                VALUES (:nome, :kw, :cat, :ing, :modo)
            """), {"nome": nome, "kw": keywords, "cat": categoria, "ing": ingredientes, "modo": modo})
            s.commit()
        return True
    except Exception as e:
        logger.error(f"criar_receita erro: {e}")
        return False


def atualizar_receita(receita_id, nome, keywords, categoria, ingredientes, modo):
    if not Session:
        return False
    try:
        with Session() as s:
            s.execute(text("""
                UPDATE receitas SET nome=:nome, keywords=:kw, categoria=:cat,
                ingredientes=:ing, modo=:modo WHERE id=:id
            """), {"nome": nome, "kw": keywords, "cat": categoria, "ing": ingredientes, "modo": modo, "id": receita_id})
            s.commit()
        return True
    except Exception as e:
        logger.error(f"atualizar_receita erro: {e}")
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