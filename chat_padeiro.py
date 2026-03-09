# chat_padeiro.py
from flask import Flask, render_template, request, jsonify, session
import os, re, random, unicodedata

try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

from services.ia_services import gerar_resposta, buscar_e_responder_web
from db import cache_get, cache_set, carregar_catalogo as db_carregar_catalogo

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

PDF_FOLDER = "pdfs_upload"
os.makedirs(PDF_FOLDER, exist_ok=True)

pdf_content = ""


# ══════════════════════════════════════════
# UTILITÁRIO
# ══════════════════════════════════════════
def norm(s):
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii").lower()


# ══════════════════════════════════════════
# CATÁLOGO DE RECEITAS  ←  carregado do banco
# ══════════════════════════════════════════
DB, RECEITAS_QUENTES, RECEITAS_FRIAS = db_carregar_catalogo()


def buscar_chave_catalogo(mensagem):
    """Retorna a chave do DB que combina com a mensagem, ou None."""
    m = norm(mensagem)
    for chave, info in DB.items():
        if any(norm(kw) in m for kw in info["keywords"]):
            return chave
    return None


# ══════════════════════════════════════════
# FILTRO DE TEMA
# ══════════════════════════════════════════
# Palavras que liberam a resposta — geradas dinamicamente a partir do DB + fixas
_PALAVRAS_FIXAS = [
    "receita", "fazer", "preparar", "ingrediente", "modo", "preparo",
    "massa", "forno", "assar", "temperatura", "grau", "kg",
    "mais", "outra", "proxima", "dias", "quente", "frio",
]

def _palavras_panificacao():
    palavras = set(_PALAVRAS_FIXAS)
    for info in DB.values():
        for kw in info["keywords"]:
            palavras.update(norm(kw).split())
    return palavras

PALAVRAS_PANIFICACAO = _palavras_panificacao()
CONTEXTO_CURTO = {"sim", "nao", "ok", "legal", "certo", "entendi", "obrigado", "obrigada"}

def eh_panificacao(mensagem):
    m = norm(mensagem).strip()
    if len(m) <= 4 or m in CONTEXTO_CURTO:
        return True
    return any(p in m for p in PALAVRAS_PANIFICACAO)


# ══════════════════════════════════════════
# CÁLCULO DE FERMENTO
# ══════════════════════════════════════════
def calcular_fermento(fv, tv):
    try:
        kg   = float(fv.replace(",", "."))
        temp = float(tv.replace(",", "."))
        pct  = 3.5 if temp < 20 else 2.0 if temp <= 25 else 1.0 if temp <= 30 else 0.5
        g    = round(kg * 1000 * pct / 100, 1)
        return f"Para {kg} kg de farinha a {temp}°C, use {g} g de fermento seco.\n(Percentual: {pct}%)"
    except:
        return None


# ══════════════════════════════════════════
# PDF — LEITURA
# ══════════════════════════════════════════
def extrair_texto_pdf(caminho):
    if not PDF_SUPPORT:
        return ""
    try:
        texto = ""
        with open(caminho, "rb") as f:
            for p in PdfReader(f).pages:
                texto += (p.extract_text() or "") + "\n\n"
        return texto.strip()
    except:
        return ""

def carregar_pdfs_pasta():
    global pdf_content
    pdf_content = ""
    if not os.path.exists(PDF_FOLDER):
        return
    for arq in os.listdir(PDF_FOLDER):
        if arq.lower().endswith(".pdf"):
            t = extrair_texto_pdf(os.path.join(PDF_FOLDER, arq))
            if t:
                pdf_content += f"\n\n[PDF: {arq}]\n{t}"
                print(f"PDF carregado: {arq}")

carregar_pdfs_pasta()


# ══════════════════════════════════════════
# PDF — BUSCA E EXTRAÇÃO
# ══════════════════════════════════════════
def buscar_no_pdf(mensagem):
    if not pdf_content:
        return None
    chave = buscar_chave_catalogo(mensagem)
    if not chave:
        return None
    nome_real = DB[chave]["nome_pdf"]
    idx = pdf_content.find(nome_real)
    if idx == -1:
        return None
    fim = len(pdf_content)
    for info in DB.values():
        outro = info["nome_pdf"]
        if outro == nome_real:
            continue
        pos = pdf_content.find(outro, idx + len(nome_real))
        if 0 < pos < fim:
            fim = pos
    return pdf_content[idx:fim].strip()


def extrair_receita(trecho):
    # Junta linhas quebradas (continuação começa com espaço)
    linhas_raw = trecho.splitlines()
    linhas = []
    for l in linhas_raw:
        if l.startswith(" ") and linhas:
            linhas[-1] = linhas[-1].rstrip() + " " + l.strip()
        else:
            linhas.append(l)
    linhas = [l.strip() for l in linhas if l.strip()]

    nome, ingredientes_linhas, modo_linhas = None, [], []
    secao = None

    for linha in linhas:
        ll = linha.lower().strip()

        if nome is None:
            if ll not in ("ingredientes", "ingredientes:", "modo de preparo") and                not ll.startswith("origem:") and "receitas para" not in ll:
                nome = linha.strip()
                continue

        if ll.startswith("origem:"):
            continue

        if ll in ("ingredientes", "ingredientes:"):
            secao = "ing"
            continue

        if ll == "modo de preparo":
            secao = "modo"
            continue

        # No modo de preparo, junta linha que é continuação (não começa com número)
        if secao == "modo" and modo_linhas and not re.match(r"^\d+\.", linha):
            modo_linhas[-1] = modo_linhas[-1] + " " + linha.strip()
            continue

        # Subseção ex: "Massa:" ou "Calda:"
        if re.match(r"^[A-Za-zÀ-ú ]+:$", linha) and secao == "ing":
            ingredientes_linhas.append(f"--- {linha.rstrip(':')} ---")
            continue

        if re.match(r"^(obs|dica|nota)", ll):
            continue

        # Remove bullet - e numeração de passos
        item = re.sub(r"^-\s*", "", linha)
        item = re.sub(r"^\d+\.\s*", "", item).strip()

        if not item:
            continue

        if secao == "ing":
            ingredientes_linhas.append(item)
        elif secao == "modo":
            modo_linhas.append(item)

    ing  = "\n".join(("  " + l if not l.startswith("---") else "\n" + l) for l in ingredientes_linhas).strip() or None
    modo = "\n".join(f"{i}. {l}" for i, l in enumerate(modo_linhas, 1)) or None
    return nome, ing, modo


def formatar(nome, ing, modo, quer_ing):
    if not nome or not modo:
        return None
    for pat in [r"\[PDF:[^\]]+\]", r"Receitas?\s+para\s+Dias?\s+\w+", r"Padaria\s+Artesanal\s+CRI", r"Origem:.*"]:
        nome = re.sub(pat, "", nome, flags=re.I).strip()
    nome = nome.strip("[]().,—– ")
    if not nome:
        return None
    if quer_ing and ing:
        return f"Receita: {nome}\n\nIngredientes:\n{ing}\n\nModo de preparo:\n{modo}"
    return f"Receita: {nome}\n\nModo de preparo:\n{modo}"


# ══════════════════════════════════════════
# ESCALA POR KG
# ══════════════════════════════════════════
def detectar_kg(msg):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*kg", msg.lower())
    return float(m.group(1).replace(",", ".")) if m else None

def escalar_ingredientes(texto, fator):
    out = []
    for linha in (texto or "").splitlines():
        m = re.match(r"^(\d+(?:[.,]\d+)?)\s*(.*)$", linha.strip())
        if m:
            novo = float(m.group(1).replace(",", ".")) * fator
            s = str(int(round(novo))) if abs(novo - round(novo)) < 1e-9 else str(round(novo, 2)).replace(".", ",")
            out.append(f"{s} {m.group(2)}".strip())
        else:
            out.append(linha)
    return "\n".join(out)


# ══════════════════════════════════════════
# HELPER — SORTEIA RECEITA DA CATEGORIA
# ══════════════════════════════════════════
def sortear_receita(cat):
    lista    = RECEITAS_QUENTES if cat == "quentes" else RECEITAS_FRIAS
    enviadas = session.get(f"{cat}_enviadas", [])
    disponiveis = [r for r in lista if r not in enviadas]
    if not disponiveis:
        enviadas, disponiveis = [], lista[:]
    escolhida = random.choice(disponiveis)
    enviadas.append(escolhida)
    session[f"{cat}_enviadas"] = enviadas
    session["ultima_categoria"] = cat
    return escolhida


# ══════════════════════════════════════════
# ROTAS
# ══════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/v1/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():
    global pdf_content
    if "pdf" not in request.files:
        return jsonify({"erro": "Nenhum arquivo"}), 400
    f = request.files["pdf"]
    if not f.filename.lower().endswith(".pdf"):
        return jsonify({"erro": "Apenas PDFs"}), 400
    f.save(os.path.join(PDF_FOLDER, f.filename))
    carregar_pdfs_pasta()
    return jsonify({"status": "ok", "mensagem": f"PDF '{f.filename}' carregado!"}), 200


@app.route("/api/v1/chat", methods=["POST"])
def api_chat():
    dados    = request.get_json() or {}
    mensagem = (dados.get("mensagem") or "").strip()
    if not mensagem:
        return jsonify({"resposta": "Digite algo."}), 200

    msg_lower = mensagem.lower()
    msg_norm  = norm(mensagem)

    historico = session.get("historico", [])
    historico.append(mensagem)
    session["historico"] = historico[-3:]

    # ── 1. FERMENTO ──────────────────────────────────────────────────────────
    aguardando  = session.get("aguardando_fermento", False)
    eh_pedido   = any(p in msg_norm for p in ["calcular fermento", "calcule fermento", "calculo fermento"])
    tem_kg      = bool(re.search(r"\d.*kg|kg.*\d", msg_lower))
    tem_grau    = bool(re.search(r"\d.*grau|\d.*°|\d.*celsius", msg_lower))
    eh_resposta = aguardando and bool(re.search(r"\d+", mensagem))
    eh_fermento = eh_pedido or eh_resposta or ("fermento" in msg_lower and (tem_kg or tem_grau))

    if eh_fermento:
        fm   = re.search(r"(\d+(?:[.,]\d+)?)\s*kg", mensagem, re.I)
        tm   = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:°|graus?|celsius|grau)", mensagem, re.I)
        nums = re.findall(r"(\d+(?:[.,]\d+)?)", mensagem)
        fv   = fm.group(1) if fm else (nums[0] if nums else None)
        tv   = tm.group(1) if tm else (nums[1] if len(nums) > 1 else None)
        if fv and tv:
            session["aguardando_fermento"] = False
            res = calcular_fermento(fv, tv)
            return jsonify({"resposta": res or "Não consegui calcular. Verifique os valores."}), 200
        session["aguardando_fermento"] = True
        return jsonify({"resposta": (
            "Para calcular o fermento, preciso de duas informações:\n\n"
            "1. Quantidade de farinha (em kg)\n"
            "2. Temperatura ambiente (em °C)\n\n"
            "Digite assim: \"2 kg, 28 graus\""
        )}), 200

    # ── 2. DIAS QUENTES / FRIOS / MAIS ───────────────────────────────────────
    escolhida = None

    PADROES_QUENTE = [
        r"dias?.quentes?", r"dia de calor", r"calor", r"faz calor",
        r"dia quente", r"temperatura alta", r"verao",
    ]
    PADROES_FRIO = [
        r"dias?.frios?", r"dia de frio", r"frio", r"faz frio",
        r"dia frio", r"temperatura baixa", r"inverno", r"gelado",
        r"tempo frio", r"dia gelado",
    ]
    PADROES_MAIS = [
        r"\b(mais|outra|proxima|outro|proximo|diferente)\b",
        r"me da (mais|outra)", r"quero (mais|outra)",
    ]

    if any(re.search(p, msg_norm) for p in PADROES_QUENTE):
        escolhida = sortear_receita("quentes")
    elif any(re.search(p, msg_norm) for p in PADROES_FRIO):
        escolhida = sortear_receita("frias")
    elif any(re.search(p, msg_norm) for p in PADROES_MAIS) and session.get("ultima_categoria"):
        escolhida = sortear_receita(session["ultima_categoria"])

    if escolhida:
        kw       = DB[escolhida]["keywords"][0]
        mensagem = f"receita de {kw}"
        msg_lower = mensagem.lower()
        msg_norm  = norm(mensagem)

    # ── 3. FILTRO DE TEMA ─────────────────────────────────────────────────────
    if not eh_panificacao(mensagem):
        return jsonify({"resposta": "Só falo sobre panificação e cálculo de fermento."}), 200

    # ── 4. INGREDIENTES DA ÚLTIMA RECEITA ─────────────────────────────────────
    quer_ing = bool(re.search(r"\bingrediente\b", msg_lower))
    kg       = detectar_kg(mensagem)

    if quer_ing and not kg:
        last_nome = session.get("ultima_receita_nome", "")
        last_ing  = session.get("ultima_receita_ingredientes", "")
        if last_ing:
            return jsonify({"resposta": f"Receita: {last_nome}\n\nIngredientes:\n{last_ing}"}), 200

    # ── 5. CACHE ──────────────────────────────────────────────────────────────
    chave_cache = f"{mensagem}|{session.get('ultima_receita', '')}"
    cached = cache_get(chave_cache)
    if cached:
        return jsonify({"resposta": cached}), 200

    # ── 6. BUSCA NO PDF ───────────────────────────────────────────────────────
    trecho = buscar_no_pdf(mensagem)
    if trecho:
        nome, ing, modo = extrair_receita(trecho)
        if nome: session["ultima_receita_nome"] = nome
        if ing:  session["ultima_receita_ingredientes"] = ing
        if modo: session["ultima_receita_modo"] = modo
        if kg and ing:
            ing     = escalar_ingredientes(ing, kg)
            quer_ing = True
        resp = formatar(nome or "Receita", ing or "", modo or trecho, quer_ing)
        if not resp:
            resp = f"Encontrei na base:\n\n{trecho[:1500]}"
        cache_set(chave_cache, resp)
        return jsonify({"resposta": resp}), 200

    # ── 7. BUSCA WEB (Groq compound-beta) ─────────────────────────────────────
    try:
        resp_web = buscar_e_responder_web(mensagem)
        if resp_web:
            cache_set(chave_cache, resp_web)
            return jsonify({"resposta": resp_web}), 200
    except Exception as e:
        print(f"Erro web: {e}")

    # ── 8. FALLBACK IA (Groq llama3) ──────────────────────────────────────────
    historico_txt = "\n".join(historico)
    resp = gerar_resposta(f"Histórico:\n{historico_txt}\n\nUsuário: {mensagem}")
    cache_set(chave_cache, resp)
    return jsonify({"resposta": resp}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)