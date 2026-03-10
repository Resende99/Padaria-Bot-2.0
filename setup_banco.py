"""
Roda UMA VEZ para criar as tabelas.
Execute: python setup_banco.py
"""
import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL não configurada.")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS receitas (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    keywords TEXT[] NOT NULL,
    categoria TEXT NOT NULL,
    ingredientes TEXT NOT NULL,
    modo TEXT NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW()
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS cache (
    chave TEXT PRIMARY KEY,
    resposta TEXT NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW()
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS ultima_receita (
    session_id TEXT PRIMARY KEY,
    nome TEXT,
    ingredientes TEXT,
    modo TEXT,
    atualizado_em TIMESTAMP DEFAULT NOW()
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS historico (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    mensagem TEXT NOT NULL,
    resposta TEXT NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW()
);
""")

conn.commit()
cur.close()
conn.close()
print("Tabelas criadas com sucesso!")