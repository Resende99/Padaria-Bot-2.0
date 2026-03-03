from flask_restx import Namespace, Resource, fields
from flask import request, session
from services.ia_services import gerar_resposta
import re
import json

import chat_padeiro


chat_ns = Namespace("chat", description="Chat operations")

chat_model = chat_ns.model("ChatRequest", {
    "mensagem": fields.String(required=True, description="Texto da pergunta")
})


@chat_ns.route("")
class ChatResource(Resource):

    @chat_ns.expect(chat_model)
    def post(self):

        dados = request.get_json() or {}
        mensagem = dados.get("mensagem")

        if not mensagem:
            return {"error": "Campo 'mensagem' é obrigatório."}, 400

        mensagem = mensagem.strip()

        if not mensagem:
            return {"resposta": "Digite algo."}, 200


        # inicia sessão
        if "historico" not in session:
            session["historico"] = []

        if "ultima_receita" not in session:
            session["ultima_receita"] = ""

        historico = session["historico"]
        ultima_receita = session["ultima_receita"]


        # REGRA: cálculo de fermento
        if "fermento" in mensagem.lower() and "temperatura" in mensagem.lower():

            farinha = re.search(r"(\d+(?:[.,]\d+)?)\s*kg", mensagem, re.I)
            temp = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:°|graus|c)", mensagem, re.I)

            if farinha and temp:

                f_kg = farinha.group(1)
                t_c = temp.group(1)

                fermento = chat_padeiro.calcular_fermento(f_kg, t_c)

                if fermento is not None:
                    return {
                        "resposta": f"Para {f_kg} kg de farinha a {t_c}°C, use {fermento} g de fermento seco."
                    }, 200

                else:
                    return {"resposta": "Valores inválidos."}, 200

            else:
                return {"resposta": "Informe farinha (kg) e temperatura (°C)."}, 200


        # usuário pediu ingredientes
        if re.search(r"\bingrediente\b", mensagem.lower()):

            if ultima_receita:
                mensagem = f"Liste apenas os ingredientes da receita: {ultima_receita}"

            else:
                return {"resposta": "Não sei de qual receita você está falando."}, 200


        chave = f"{mensagem}|{ultima_receita}"


        # verifica cache
        if chave in chat_padeiro.cache:
            return {"resposta": chat_padeiro.cache[chave]}, 200


        # histórico curto
        historico.append(mensagem)

        if len(historico) > 3:
            historico.pop(0)


        # monta contexto
        contexto = chat_padeiro.contexto_base
        contexto += "\n\nHistórico:\n" + "\n".join(historico[-3:])


        # adiciona conteúdo dos PDFs
        if chat_padeiro.pdf_content:
            contexto += f"\n\n[CONTEÚDO DE PDFs]\n{chat_padeiro.pdf_content[:5000]}"


        # prompt final
        prompt = f"{contexto}\nUsuário: {mensagem}"


        # chama IA
        resposta = gerar_resposta(prompt)


        # salva cache
        try:
            chat_padeiro.cache[chave] = resposta

            with open(chat_padeiro.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(chat_padeiro.cache, f, ensure_ascii=False, indent=2)

        except Exception:
            pass


        # atualiza última receita
        match = re.search(r"(?i)(receita de|para fazer)\s+([a-zà-ú\s]+)", mensagem)

        if match:
            session["ultima_receita"] = match.group(2).strip().lower()


        session["historico"] = historico


        return {"resposta": resposta}, 200