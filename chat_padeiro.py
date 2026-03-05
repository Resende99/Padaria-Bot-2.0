# chat_padeiro.py
from flask import Flask, render_template, request, jsonify, session
import os, json, time, threading, re, random, unicodedata

try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

from services.ia_services import gerar_resposta, buscar_e_responder_web

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret_key_trocar")

CACHE_FILE = "receitas_cache.json"
PDF_FOLDER = "pdfs_upload"
os.makedirs(PDF_FOLDER, exist_ok=True)
pdf_content = ""

def norm(s):
    return unicodedata.normalize("NFD", s).encode("ascii","ignore").decode("ascii").lower()

# ══ CACHE ══
def carregar_cache():
    try:
        with open(CACHE_FILE,"r",encoding="utf-8") as f: return json.load(f)
    except: return {}

cache = carregar_cache()

def salvar_cache():
    try:
        with open(CACHE_FILE,"w",encoding="utf-8") as f: json.dump(cache,f,ensure_ascii=False,indent=2)
    except: pass

threading.Thread(target=lambda: [time.sleep(3600) or cache.update(carregar_cache()) for _ in iter(int,1)], daemon=True).start()

# ══ CONTEXTO BASE ══
contexto_base = (
    "Você é um assistente de padaria e confeitaria. "
    "SEMPRE responda em português brasileiro. "
    "Responda apenas sobre receitas de pães, bolos, massas, salgados e confeitaria artesanal. "
    "Regras: ao pedir receita envie só nome e modo de preparo. "
    "Se pedirem ingredientes envie a lista completa. "
    "Respostas objetivas e técnicas. Sem emojis.\n"
)

# ══ FILTRO DE TEMA ══
TEMAS_PANIFICACAO = [
    "receita","bolo","pao","massa","recheio","cobertura","sorvete","mousse",
    "confeit","padaria","forno","assar","ingrediente","farinha","fermento",
    "acucar","manteiga","leite","ovo","chocolate","creme","brigadeiro",
    "salgado","torta","biscoito","cookie","eclair","pamonha","empadinha",
    "focaccia","baguete","tapioca","fuba","mandioca","macaxeira","abacaxi",
    "pudim","doce","bombom","pacoca","queijo","presunto","salsicha","frango",
    "pizza","petit","sequilho","navete","mel","couve","cenoura","abacate",
    "milho","aveia","morango","cafe","iogurte","amido","polvilho","requeijao",
    "calda","ganache","glace","fazer","preparar","quente","frio","dias",
    "temperatura","grau","kg","mais","outra","proxima","porcao",
]
CONTEXTO_CURTO = ["sim","nao","ok","legal","certo","entendi","obrigado","obrigada"]

def eh_panificacao(mensagem):
    m = norm(mensagem).strip()
    if len(m) <= 4 or m in CONTEXTO_CURTO:
        return True
    return any(t in m for t in TEMAS_PANIFICACAO)

# ══ FERMENTO ══
def calcular_fermento(farinha_val, temp_val):
    try:
        kg = float(farinha_val.replace(",","."))
        temp = float(temp_val.replace(",","."))
        pct = 3.5 if temp < 20 else 2.0 if temp <= 25 else 1.0 if temp <= 30 else 0.5
        gramas = round(kg * 1000 * pct / 100, 1)
        return f"Para {kg} kg de farinha a {temp}°C, use {gramas} g de fermento seco.\n(Percentual: {pct}%)"
    except:
        return None

# ══ PDF — LEITURA ══
def extrair_texto_pdf(caminho):
    if not PDF_SUPPORT: return ""
    try:
        texto = ""
        with open(caminho,"rb") as f:
            for p in PdfReader(f).pages:
                texto += (p.extract_text() or "") + "\n\n"
        return texto.strip()
    except: return ""

def carregar_pdfs_pasta():
    global pdf_content
    pdf_content = ""
    if not os.path.exists(PDF_FOLDER): return
    for arq in os.listdir(PDF_FOLDER):
        if arq.lower().endswith(".pdf"):
            t = extrair_texto_pdf(os.path.join(PDF_FOLDER, arq))
            if t:
                pdf_content += f"\n\n[PDF: {arq}]\n{t}"
                print(f"PDF carregado: {arq}")

carregar_pdfs_pasta()

# ══ CATÁLOGO ══
CATALOGO = {
    "Sorvete Artesanal":                        ["sorvete"],
    "Mousse de Cafe com Chocolate":             ["mousse","cafe"],
    "Mousse de Morango sem Leite Condensado":   ["morango"],
    "Bombom de Prestigio":                      ["prestigio"],
    "Bombom Surpresa com Pacoca":               ["pacoca","surpresa"],
    "Bicho de Pe":                              ["bicho de pe"],
    "Pacoquinha de Leite Condensado":           ["pacoquinha","amendoim"],
    "Pizza de Chocolate Brigadeiro":            ["pizza"],
    "Petit Gateau de Bacuri":                   ["petit","gateau","bacuri"],
    "Sequilhos de Limao":                       ["sequilho","limao"],
    "Bolo de Abacaxi com Doce de Leite":        ["abacaxi","doce de leite"],
    "Bolo de Cenoura com Pudim de Chocolate":   ["cenoura"],
    "Bolo de Couve":                            ["couve"],
    "Bolo de Fuba":                             ["fuba"],
    "Bolo de Mandioca Cremoso":                 ["mandioca"],
    "Bolo de Chocolate Peteleco":               ["peteleco","chocolate"],
    "Bolo de Macaxeira Caramelizado":           ["macaxeira"],
    "Pastel de Forno com Creme de Galinha":     ["pastel","galinha","guarana"],
    "Pudim de Queijo":                          ["pudim"],
    "Navete Francesa":                          ["navete"],
    "Pao de Mel":                               ["pao de mel"],
    "Pao de Queijo Simples":                    ["pao de queijo"],
    "Pao de Sal":                               ["pao de sal","pao de leite"],
    "Pao Caseiro Recheado":                     ["pao caseiro"],
    "Mini Focaccia":                            ["focaccia"],
    "Enroladinho de Salsicha":                  ["salsicha","enroladinho"],
    "Cookies de Chocolate":                     ["cookie"],
    "Joelho ou Enroladinho de Presunto":        ["presunto","joelho"],
    "Baguete Recheada":                         ["baguete"],
    "Bolinho de Queijo":                        ["bolinho"],
    "Pao de Aveia":                             ["aveia"],
    "Pao de Milho":                             ["milho"],
    "Pao de Cenoura":                           ["pao de cenoura"],
    "Pao de Abacate":                           ["abacate"],
    "Torta de Escarola":                        ["escarola","torta"],
    "Pamonha de Forno":                         ["pamonha"],
    "Empadinha de Leite Condensado":            ["empadinha"],
    "Eclair":                                   ["eclair","carolina"],
}

NOMES_PDF = {
    "Sorvete Artesanal":                        "Sorvete Artesanal",
    "Mousse de Cafe com Chocolate":             "Mousse de Café com Chocolate",
    "Mousse de Morango sem Leite Condensado":   "Mousse de Morango sem Leite Condensado",
    "Bombom de Prestigio":                      "Bombom de Prestígio",
    "Bombom Surpresa com Pacoca":               "Bombom Surpresa com Paçoca",
    "Bicho de Pe":                              "Bicho de Pé (Docinho de Gelatina)",
    "Pacoquinha de Leite Condensado":           "Paçoquinha de Leite Condensado",
    "Pizza de Chocolate Brigadeiro":            "Pizza de Chocolate Brigadeiro com Morangos",
    "Petit Gateau de Bacuri":                   "Petit Gateau de Bacuri",
    "Sequilhos de Limao":                       "Sequilhos de Limão",
    "Bolo de Abacaxi com Doce de Leite":        "Bolo de Abacaxi com Doce de Leite",
    "Bolo de Cenoura com Pudim de Chocolate":   "Bolo de Cenoura com Pudim de Chocolate",
    "Bolo de Couve":                            "Bolo de Couve",
    "Bolo de Fuba":                             "Bolo de Fubá",
    "Bolo de Mandioca Cremoso":                 "Bolo de Mandioca Cremoso",
    "Bolo de Chocolate Peteleco":               "Bolo de Chocolate (Peteleco)",
    "Bolo de Macaxeira Caramelizado":           "Bolo de Macaxeira Caramelizado",
    "Pastel de Forno com Creme de Galinha":     "Pastel de Forno com Creme de Galinha",
    "Pudim de Queijo":                          "Pudim de Queijo",
    "Navete Francesa":                          "Navete Francesa",
    "Pao de Mel":                               "Pão de Mel",
    "Pao de Queijo Simples":                    "Pão de Queijo Simples",
    "Pao de Sal":                               "Pão de Sal (Pão de Leite)",
    "Pao Caseiro Recheado":                     "Pão Caseiro Recheado",
    "Mini Focaccia":                            "Mini Focaccia",
    "Enroladinho de Salsicha":                  "Enroladinho de Salsicha",
    "Cookies de Chocolate":                     "Cookies de Chocolate",
    "Joelho ou Enroladinho de Presunto":        "Joelho ou Enroladinho de Presunto e Queijo",
    "Baguete Recheada":                         "Baguete Recheada",
    "Bolinho de Queijo":                        "Bolinho de Queijo",
    "Pao de Aveia":                             "Pão de Aveia com Iogurte",
    "Pao de Milho":                             "Pão de Milho",
    "Pao de Cenoura":                           "Pão de Cenoura",
    "Pao de Abacate":                           "Pão de Abacate",
    "Torta de Escarola":                        "Torta de Escarola",
    "Pamonha de Forno":                         "Pamonha de Forno",
    "Empadinha de Leite Condensado":            "Empadinha de Leite Condensado",
    "Eclair":                                   "Éclair",
}

RECEITAS_QUENTES = [
    "Sorvete Artesanal","Mousse de Cafe com Chocolate",
    "Mousse de Morango sem Leite Condensado","Bombom de Prestigio",
    "Bombom Surpresa com Pacoca","Bicho de Pe",
    "Pacoquinha de Leite Condensado","Pizza de Chocolate Brigadeiro",
    "Petit Gateau de Bacuri","Sequilhos de Limao",
]
RECEITAS_FRIAS = [
    "Bolo de Abacaxi com Doce de Leite","Bolo de Cenoura com Pudim de Chocolate",
    "Bolo de Couve","Bolo de Fuba","Bolo de Mandioca Cremoso",
    "Bolo de Chocolate Peteleco","Bolo de Macaxeira Caramelizado",
    "Pastel de Forno com Creme de Galinha","Pudim de Queijo",
    "Navete Francesa","Pao de Mel","Joelho ou Enroladinho de Presunto",
]

# ══ BUSCA NO PDF ══
def buscar_no_pdf(mensagem):
    if not pdf_content: return None
    m = norm(mensagem)
    chave = None
    for k, kws in CATALOGO.items():
        if any(norm(kw) in m for kw in kws):
            chave = k
            break
    if not chave: return None
    nome_real = NOMES_PDF[chave]
    idx = pdf_content.find(nome_real)
    if idx == -1: return None
    fim = len(pdf_content)
    for outro in NOMES_PDF.values():
        if outro == nome_real: continue
        pos = pdf_content.find(outro, idx + len(nome_real))
        if 0 < pos < fim: fim = pos
    return pdf_content[idx:fim].strip()

# ══ EXTRAÇÃO ══
def extrair_receita(trecho):
    linhas = [l.strip() for l in trecho.splitlines() if l.strip()]
    nome = ingredientes_linhas = modo_linhas = None
    ingredientes_linhas, modo_linhas = [], []
    secao = None
    for linha in linhas:
        ll = linha.lower()
        if nome is None:
            if not any(p in ll for p in ["ingrediente","modo de preparo","receitas para","origem:"]):
                nome = re.sub(r"Padaria\s+Artesanal\s+CRI","",linha,flags=re.I).strip()
                continue
        if ll.strip() == "ingredientes": secao = "ing"; continue
        if "modo de preparo" in ll: secao = "modo"; continue
        if re.match(r"^\[.+\]$", linha):
            if secao == "ing": ingredientes_linhas.append("--- " + linha.strip("[] ") + " ---")
            continue
        if re.match(r"^(obs|dica|nota|origem)", ll): continue
        item = re.sub(r"^\d+\.\s*","",linha).strip()
        item = re.sub(r"Padaria\s+Artesanal\s+CRI","",item,flags=re.I).strip()
        if secao == "ing" and item: ingredientes_linhas.append(item)
        elif secao == "modo" and item: modo_linhas.append(item)

    ing = "\n".join(("  "+l if not l.startswith("---") else "\n"+l) for l in ingredientes_linhas).strip() if ingredientes_linhas else None
    modo = "\n".join(f"{i}. {l}" for i,l in enumerate(modo_linhas,1)) if modo_linhas else None
    return nome, ing, modo

def formatar(nome, ing, modo, quer_ing):
    if not nome or not modo: return None
    nome = re.sub(r"\[PDF:[^\]]+\]","",nome).strip()
    nome = re.sub(r"Receitas?\s+para\s+Dias?\s+\w+","",nome,flags=re.I).strip()
    nome = re.sub(r"Padaria\s+Artesanal\s+CRI","",nome,flags=re.I).strip()
    nome = re.sub(r"Origem:.*","",nome,flags=re.I).strip().strip("[]().,—– ")
    if not nome: return None
    if quer_ing and ing:
        return f"Receita: {nome}\n\nIngredientes:\n{ing}\n\nModo de preparo:\n{modo}"
    return f"Receita: {nome}\n\nModo de preparo:\n{modo}"

# ══ ESCALA KG ══
def detectar_kg(msg):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*kg", msg.lower())
    return float(m.group(1).replace(",",".")) if m else None

def escalar_ingredientes(texto, fator):
    out = []
    for linha in (texto or "").splitlines():
        m = re.match(r"^(\d+(?:[.,]\d+)?)\s*(.*)$", linha.strip())
        if m:
            novo = float(m.group(1).replace(",",".")) * fator
            s = str(int(round(novo))) if abs(novo-round(novo))<1e-9 else str(round(novo,2)).replace(".",",")
            out.append(f"{s} {m.group(2)}".strip())
        else:
            out.append(linha)
    return "\n".join(out)

# ══ ROTAS ══
@app.route("/")
def index(): return render_template("index.html")

@app.route("/api/v1/health")
def health(): return jsonify({"status":"ok"}), 200

@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():
    global pdf_content
    if "pdf" not in request.files: return jsonify({"erro":"Nenhum arquivo"}), 400
    f = request.files["pdf"]
    if not f.filename.lower().endswith(".pdf"): return jsonify({"erro":"Apenas PDFs"}), 400
    f.save(os.path.join(PDF_FOLDER, f.filename))
    carregar_pdfs_pasta()
    return jsonify({"status":"ok","mensagem":f"PDF '{f.filename}' carregado!"}), 200

@app.route("/api/v1/chat", methods=["POST"])
def api_chat():
    dados = request.get_json() or {}
    mensagem = (dados.get("mensagem") or "").strip()
    if not mensagem: return jsonify({"resposta":"Digite algo."}), 200

    msg_lower = mensagem.lower()
    msg_norm  = norm(mensagem)

    historico = session.get("historico", [])
    historico.append(mensagem)
    session["historico"] = historico[-3:]

    # ── 1. FERMENTO ──
    aguardando = session.get("aguardando_fermento", False)
    eh_pedido  = any(p in msg_norm for p in ["calcular fermento","calcule fermento","calculo fermento"])
    tem_kg     = bool(re.search(r"\d.*kg|kg.*\d", msg_lower))
    tem_grau   = bool(re.search(r"\d.*grau|\d.*°|\d.*celsius", msg_lower))
    eh_resposta = aguardando and bool(re.search(r"\d+", mensagem))
    eh_fermento = eh_pedido or eh_resposta or ("fermento" in msg_lower and (tem_kg or tem_grau))

    if eh_fermento:
        fm = re.search(r"(\d+(?:[.,]\d+)?)\s*kg", mensagem, re.I)
        tm = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:°|graus?|celsius|grau)", mensagem, re.I)
        nums = re.findall(r"(\d+(?:[.,]\d+)?)", mensagem)
        fv = fm.group(1) if fm else (nums[0] if nums else None)
        tv = tm.group(1) if tm else (nums[1] if len(nums)>1 else None)
        if fv and tv:
            session["aguardando_fermento"] = False
            res = calcular_fermento(fv, tv)
            return jsonify({"resposta": res or "Não consegui calcular. Verifique os valores."}), 200
        session["aguardando_fermento"] = True
        return jsonify({"resposta":(
            "Para calcular o fermento, preciso de duas informações:\n\n"
            "1. Quantidade de farinha (em kg)\n"
            "2. Temperatura ambiente (em °C)\n\n"
            "Digite assim: \"2 kg, 28 graus\""
        )}), 200

    # ── 2. DIAS QUENTES / FRIOS ──
    escolhida = None
    if re.search(r"dias?.quentes?", msg_norm):
        lista, cat = RECEITAS_QUENTES, "quentes"
    elif re.search(r"dias?.frios?", msg_norm):
        lista, cat = RECEITAS_FRIAS, "frias"
    elif re.search(r"\b(mais|outra|proxima)\b", msg_norm) and session.get("ultima_categoria"):
        cat = session["ultima_categoria"]
        lista = RECEITAS_QUENTES if cat == "quentes" else RECEITAS_FRIAS
    else:
        lista, cat = None, None

    if lista:
        enviadas = session.get(f"{cat}_enviadas", [])
        disponiveis = [r for r in lista if r not in enviadas]
        if not disponiveis:
            enviadas, disponiveis = [], lista[:]
        escolhida = random.choice(disponiveis)
        enviadas.append(escolhida)
        session[f"{cat}_enviadas"] = enviadas
        session["ultima_categoria"] = cat
        kws = CATALOGO.get(escolhida, [escolhida])
        mensagem = f"receita de {kws[0]}"
        msg_lower = mensagem.lower()
        msg_norm  = norm(mensagem)

    # ── 3. FILTRO DE TEMA ──
    if not eh_panificacao(mensagem):
        return jsonify({"resposta":"Só falo sobre panificação e cálculo de fermento."}), 200

    # ── 4. INGREDIENTES DA ÚLTIMA RECEITA ──
    quer_ing = bool(re.search(r"\bingrediente\b", msg_lower))
    kg = detectar_kg(mensagem)

    if quer_ing and not kg:
        last_nome = session.get("ultima_receita_nome","")
        last_ing  = session.get("ultima_receita_ingredientes","")
        if last_ing:
            return jsonify({"resposta":f"Receita: {last_nome}\n\nIngredientes:\n{last_ing}"}), 200

    # ── 5. CACHE ──
    chave_cache = f"{mensagem}|{session.get('ultima_receita','')}"
    if chave_cache in cache:
        return jsonify({"resposta": cache[chave_cache]}), 200

    # ── 6. BUSCA NO PDF ──
    trecho = buscar_no_pdf(mensagem)
    if trecho:
        nome, ing, modo = extrair_receita(trecho)
        if nome: session["ultima_receita_nome"] = nome
        if ing:  session["ultima_receita_ingredientes"] = ing
        if modo: session["ultima_receita_modo"] = modo
        if kg and ing:
            ing = escalar_ingredientes(ing, kg)
            quer_ing = True
        resp = formatar(nome or "Receita", ing or "", modo or trecho, quer_ing)
        if not resp: resp = f"Encontrei na base:\n\n{trecho[:1500]}"
        cache[chave_cache] = resp
        salvar_cache()
        return jsonify({"resposta": resp}), 200

    # ── 7. BUSCA WEB (Groq compound-beta) ──
    try:
        resp_web = buscar_e_responder_web(mensagem)
        if resp_web:
            cache[chave_cache] = resp_web
            salvar_cache()
            return jsonify({"resposta": resp_web}), 200
    except Exception as e:
        print(f"Erro web: {e}")

    # ── 8. FALLBACK IA (Groq llama3) ──
    prompt = contexto_base + "\n\nHistórico:\n" + "\n".join(historico) + f"\nUsuário: {mensagem}"
    resp = gerar_resposta(prompt)
    cache[chave_cache] = resp
    salvar_cache()
    return jsonify({"resposta": resp}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","5000")), debug=True)