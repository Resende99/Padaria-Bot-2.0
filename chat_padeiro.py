# chat_padeiro.py
import os, re, random, unicodedata, logging
from flask import Flask, render_template, request, jsonify, session

from services.ia_services import gerar_resposta, buscar_e_responder_web
from db import (
    cache_get, cache_set,
    carregar_catalogo,
    salvar_ultima_receita, buscar_ultima_receita,
    salvar_historico, buscar_receita_completa,
    listar_receitas, obter_receita,
    criar_receita, atualizar_receita, deletar_receita,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
ADMIN_SENHA = os.getenv("ADMIN_SENHA", "padaria123")


# ══════════════════════════════════════════
# UTILITÁRIO
# ══════════════════════════════════════════
def norm(s):
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii").lower()


# ══════════════════════════════════════════
# CATÁLOGO
# ══════════════════════════════════════════
DB, RECEITAS_QUENTES, RECEITAS_FRIAS = carregar_catalogo()

def recarregar_catalogo():
    global DB, RECEITAS_QUENTES, RECEITAS_FRIAS, PALAVRAS_PANIFICACAO
    DB, RECEITAS_QUENTES, RECEITAS_FRIAS = carregar_catalogo()
    PALAVRAS_PANIFICACAO = _palavras_panificacao()


# ══════════════════════════════════════════
# FILTRO DE TEMA
# ══════════════════════════════════════════
_PALAVRAS_FIXAS = [
    "receita", "fazer", "preparar", "ingrediente", "modo", "preparo",
    "massa", "forno", "assar", "temperatura", "grau", "kg",
    "mais", "outra", "proxima", "dias", "quente", "frio",
    "obrigado", "obrigada", "valeu", "otimo", "gostei", "perfeito",
]

def _palavras_panificacao():
    palavras = set(_PALAVRAS_FIXAS)
    for info in DB.values():
        for kw in info["keywords"]:
            palavras.update(norm(kw).split())
    return palavras

PALAVRAS_PANIFICACAO = _palavras_panificacao()
CONTEXTO_CURTO = {"sim", "nao", "ok", "legal", "certo", "entendi", "obrigado", "obrigada", "valeu", "otimo", "show"}

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
# SORTEIA RECEITA
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
# ROTAS PRINCIPAIS
# ══════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/v1/health")
def health():
    return jsonify({"status": "ok"}), 200


# ══════════════════════════════════════════
# ROTAS ADMIN
# ══════════════════════════════════════════
@app.route("/admin")
def admin():
    if not session.get("admin_logado"):
        return render_template("admin_login.html")
    return render_template("admin.html", receitas=listar_receitas())

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin_login.html")
    senha = request.form.get("senha", "")
    if senha == ADMIN_SENHA:
        session["admin_logado"] = True
        return render_template("admin.html", receitas=listar_receitas())
    return render_template("admin_login.html", erro="Senha incorreta.")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logado", None)
    return render_template("admin_login.html")

@app.route("/admin/nova", methods=["GET", "POST"])
def admin_nova():
    if not session.get("admin_logado"):
        return render_template("admin_login.html")
    erro = None
    if request.method == "POST":
        keywords = [k.strip() for k in request.form.get("keywords", "").split(",") if k.strip()]
        ok = criar_receita(
            request.form.get("nome"),
            keywords,
            request.form.get("categoria"),
            request.form.get("ingredientes"),
            request.form.get("modo"),
        )
        recarregar_catalogo()
        if ok:
            return render_template("admin.html", receitas=listar_receitas(), msg="Receita criada!")
        erro = "Erro ao criar receita."
    return render_template("admin_form.html", receita=None, acao="Nova Receita", erro=erro)

@app.route("/admin/editar/<int:rid>", methods=["GET", "POST"])
def admin_editar(rid):
    if not session.get("admin_logado"):
        return render_template("admin_login.html")
    erro = None
    if request.method == "POST":
        keywords = [k.strip() for k in request.form.get("keywords", "").split(",") if k.strip()]
        ok = atualizar_receita(
            rid,
            request.form.get("nome"),
            keywords,
            request.form.get("categoria"),
            request.form.get("ingredientes"),
            request.form.get("modo"),
        )
        recarregar_catalogo()
        if ok:
            return render_template("admin.html", receitas=listar_receitas(), msg="Receita atualizada!")
        erro = "Erro ao atualizar receita."
    receita = obter_receita(rid)
    if receita:
        receita["keywords"] = ", ".join(receita["keywords"])
    return render_template("admin_form.html", receita=receita, acao="Editar Receita", erro=erro)

@app.route("/admin/deletar/<int:rid>", methods=["POST"])
def admin_deletar(rid):
    if not session.get("admin_logado"):
        return render_template("admin_login.html")
    deletar_receita(rid)
    recarregar_catalogo()
    return render_template("admin.html", receitas=listar_receitas(), msg="Receita deletada!")


# ══════════════════════════════════════════
# CHAT
# ══════════════════════════════════════════
@app.route("/api/v1/chat", methods=["POST"])
def api_chat():
    dados    = request.get_json() or {}
    mensagem = (dados.get("mensagem") or "").strip()
    if not mensagem:
        return jsonify({"resposta": "Digite algo."}), 200

    msg_lower  = mensagem.lower()
    msg_norm   = norm(mensagem)
    session_id = session.get("session_id") or os.urandom(16).hex()
    session["session_id"] = session_id

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
    PADROES_QUENTE = [r"dias?.quentes?", r"dia de calor", r"calor", r"faz calor", r"dia quente", r"temperatura alta", r"verao"]
    PADROES_FRIO   = [r"dias?.frios?", r"dia de frio", r"faz frio", r"dia frio", r"temperatura baixa", r"inverno", r"gelado", r"tempo frio", r"dia gelado"]
    PADROES_MAIS   = [r"\b(mais|outra|proxima|outro|proximo|diferente)\b", r"me da (mais|outra)", r"quero (mais|outra)"]

    if any(re.search(p, msg_norm) for p in PADROES_QUENTE):
        escolhida = sortear_receita("quentes")
    elif any(re.search(p, msg_norm) for p in PADROES_FRIO):
        escolhida = sortear_receita("frias")
    elif any(re.search(p, msg_norm) for p in PADROES_MAIS) and session.get("ultima_categoria"):
        escolhida = sortear_receita(session["ultima_categoria"])

    if escolhida:
        kw        = DB[escolhida]["keywords"][0]
        mensagem  = f"receita de {kw}"
        msg_lower = mensagem.lower()
        msg_norm  = norm(mensagem)

    # ── 3. FILTRO DE TEMA ─────────────────────────────────────────────────────
    if not eh_panificacao(mensagem):
        return jsonify({"resposta": "Só falo sobre panificação e cálculo de fermento."}), 200

    # ── 4. INGREDIENTES / MODO DA ÚLTIMA RECEITA ─────────────────────────────
    quer_ing  = bool(re.search(r"\bingrediente\b", msg_lower))
    quer_modo = bool(re.search(r"\b(modo|preparo|como fazer|como se faz)\b", msg_lower))
    kg        = detectar_kg(mensagem)

    if quer_modo and not kg:
        ultima = buscar_ultima_receita(session_id)
        if ultima and ultima.get("modo"):
            return jsonify({"resposta": f"Receita: {ultima['nome']}\n\nModo de preparo:\n{ultima['modo']}"}), 200
        return jsonify({"resposta": "Qual receita você quer o modo de preparo?"}), 200

    if quer_ing and not kg:
        ultima = buscar_ultima_receita(session_id)
        if ultima and ultima.get("ingredientes"):
            return jsonify({"resposta": f"Receita: {ultima['nome']}\n\nIngredientes:\n{ultima['ingredientes']}"}), 200
        return jsonify({"resposta": "Qual receita você quer os ingredientes?"}), 200

    # ── 5. CACHE ──────────────────────────────────────────────────────────────
    chave_cache = f"{mensagem}|{session_id}"
    cached = cache_get(chave_cache)
    if cached:
        return jsonify({"resposta": cached}), 200

    # ── 6. BUSCA NO BANCO ─────────────────────────────────────────────────────
    receita = buscar_receita_completa(mensagem, DB)
    if receita:
        ing  = receita.get("ingredientes", "")
        modo = receita.get("modo", "")
        nome = receita.get("nome", "Receita")

        salvar_ultima_receita(session_id, receita["id"])

        if kg and ing:
            ing = escalar_ingredientes(ing, kg)

        resp = f"Receita: {nome}\n\nIngredientes:\n{ing}\n\nModo de preparo:\n{modo}"
        cache_set(chave_cache, resp)
        salvar_historico(session_id, mensagem, resp)
        return jsonify({"resposta": resp}), 200

    # ── 7. BUSCA WEB ──────────────────────────────────────────────────────────
    try:
        resp_web = buscar_e_responder_web(mensagem)
        if resp_web:
            cache_set(chave_cache, resp_web)
            salvar_historico(session_id, mensagem, resp_web)
            return jsonify({"resposta": resp_web}), 200
    except Exception as e:
        logger.error(f"Erro busca web: {e}")

    # ── 8. FALLBACK IA ────────────────────────────────────────────────────────
    historico_txt = "\n".join(historico)
    resp = gerar_resposta(f"Histórico:\n{historico_txt}\n\nUsuário: {mensagem}")
    cache_set(chave_cache, resp)
    salvar_historico(session_id, mensagem, resp)
    return jsonify({"resposta": resp}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)