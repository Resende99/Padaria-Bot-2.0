

PadariaBot 2.0

Assistente inteligente especializado em panificação e confeitaria, utilizando base de conhecimento em PDF e modelo de linguagem via API.

Sobre o Projeto

O PadariaBot é uma aplicação web desenvolvida para auxiliar padarias e profissionais da área de panificação, oferecendo:

Respostas técnicas sobre receitas

Ajuste proporcional de ingredientes

Cálculo automático de fermento

Base de conhecimento carregada a partir de PDFs

Integração com modelo de linguagem (Groq – Llama 3)

A aplicação prioriza respostas locais (regras internas e PDFs) antes de recorrer à IA, reduzindo custo e latência.

Arquitetura

Fluxo da aplicação:

Usuário
→ API Flask (/api/v1/chat)
→ Regras internas (ex: cálculo de fermento)
→ Cache local
→ Conteúdo dos PDFs carregados
→ Histórico da sessão
→ IA (Groq – Llama 3) como fallback
→ Resposta final

A IA é utilizada apenas quando a resposta não pode ser resolvida localmente.

Tecnologias Utilizadas

Python

Flask

Flask-RESTX

PyPDF2

Requests

Gunicorn

Groq API (Llama 3)

Funcionalidades

Upload dinâmico de PDFs

Extração automática de texto

Contexto baseado em regras específicas de panificação

Histórico de conversa por sessão

Sistema de cache para otimização de desempenho

API estruturada em namespaces

Endpoints
POST /api/v1/chat

Entrada:

{
  "mensagem": "Como fazer pão francês?"
}

Saída:

{
  "resposta": "..."
}
POST /upload_pdf

Permite envio de novos arquivos PDF para a base de conhecimento.

Variáveis de Ambiente
API_KEY=sua_chave_groq
FLASK_SECRET_KEY=chave_segura
PORT=5000
Execução Local
pip install -r requirements.txt
python api.py
Deploy

Aplicação preparada para deploy em ambientes como Render utilizando Gunicorn.

Procfile:

web: gunicorn api:app
Estrutura do Projeto
app/
routes/
services/
templates/
static/
api.py
requirements.txt
Procfile
Objetivo

Demonstrar aplicação prática de:

Arquitetura backend estruturada

Integração com modelo de linguagem

Sistema RAG simplificado

Organização modular de projeto Flask

Boas práticas para deploy em produção