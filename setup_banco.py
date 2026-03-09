"""
Roda UMA VEZ para criar as tabelas e popular com as receitas do JSON.
Execute: python setup_banco.py
"""
import psycopg2
import json
import os

DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# ── Cria tabelas ──────────────────────────────────────
cur.execute("""
CREATE TABLE IF NOT EXISTS cache (
    chave TEXT PRIMARY KEY,
    resposta TEXT NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW()
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS receitas (
    chave TEXT PRIMARY KEY,
    keywords TEXT[],
    categoria TEXT NOT NULL,
    nome_pdf TEXT NOT NULL
);
""")

conn.commit()
print("Tabelas criadas.")

# ── Popula receitas do JSON ───────────────────────────
with open("receitas.json", "r", encoding="utf-8") as f:
    db = json.load(f)

for chave, info in db.items():
    cur.execute("""
        INSERT INTO receitas (chave, keywords, categoria, nome_pdf)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (chave) DO UPDATE
        SET keywords = EXCLUDED.keywords,
            categoria = EXCLUDED.categoria,
            nome_pdf  = EXCLUDED.nome_pdf;
    """, (chave, info["keywords"], info["categoria"], info["nome_pdf"]))

conn.commit()
cur.execute("SELECT COUNT(*) FROM receitas;")
print(f"Receitas inseridas: {cur.fetchone()[0]}")

cur.close()
conn.close()
print("Pronto!")