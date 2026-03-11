Aqui está uma versão **Padaria-Bot 2.0** baseada no seu texto antigo, mas atualizada com as melhorias do novo projeto (banco de dados, cache, admin, Groq, etc.), mantendo o estilo **simples e direto**.

---

# Padaria-Bot 2.0

Padaria-Bot 2.0 é um chatbot desenvolvido para auxiliar atividades de padarias e confeitarias. Ele responde perguntas sobre receitas, fermentação e panificação utilizando um banco de receitas e inteligência artificial como apoio.

O sistema busca primeiro respostas em sua base de dados e utiliza IA apenas quando necessário para complementar informações.

Demo online:
[https://padaria-bot-2-0.onrender.com](https://padaria-bot-2-0.onrender.com)

---

# O que o projeto faz

• Recebe perguntas do usuário através de um chat no navegador.
• Consulta primeiro o banco de receitas armazenado no sistema.
• Utiliza IA quando precisa complementar ou melhorar uma resposta.
• Sugere receitas de acordo com o clima (dias quentes ou frios).
• Calcula automaticamente a quantidade de fermento com base na temperatura e na farinha.
• Mantém as respostas sempre relacionadas a panificação e confeitaria.

---

# Como funciona

## Front-end

• Interface simples onde o usuário envia perguntas.
• Envia mensagens para o servidor Flask.
• Recebe respostas em JSON e exibe no chat.

Tecnologias utilizadas:
HTML
CSS
JavaScript

---

## Back-end (Flask)

O servidor é responsável por:

• Receber as perguntas do usuário.
• Consultar o banco de dados de receitas.
• Verificar o cache de perguntas já respondidas.
• Executar cálculos de fermentação.
• Enviar contexto para a IA quando necessário.
• Retornar a resposta final para o front-end.

---

## Banco de dados

O sistema utiliza **PostgreSQL** para armazenar:

• Receitas de panificação e confeitaria.
• Respostas em cache para perguntas frequentes.

O banco contém **92 receitas cadastradas** que podem ser consultadas diretamente pelo chatbot.

---

## Integração com IA

A IA é utilizada apenas como complemento.

Fluxo de uso da IA:

1. O sistema tenta responder com o banco de receitas.
2. Caso não encontre informação suficiente, consulta a IA.
3. A IA recebe o contexto e gera uma resposta focada em panificação.

Tecnologia utilizada:

Groq API
Modelo LLaMA 3

---

# Principais recursos

• Chat funcional no navegador.
• Banco de receitas com dezenas de receitas cadastradas.
• Cálculo automático de fermentação.
• Sugestão de receitas com base no clima.
• Cache inteligente de respostas.
• Painel administrativo para gerenciar receitas.
• Busca web quando necessário.

---

# Painel administrativo

O sistema possui um painel protegido por senha para gerenciamento das receitas.

Através do painel é possível:

• Criar novas receitas
• Editar receitas existentes
• Excluir receitas

Acesso:

```
/admin
```

---

# Estrutura do projeto

```
Padaria-Bot/
│
├── chat_padeiro.py
├── db.py
│
├── services/
│   └── ia_services.py
│
├── templates/
│   ├── index.html
│   ├── admin.html
│   ├── admin_login.html
│   └── admin_form.html
│
├── static/
│   ├── style.css
│   └── script.js
│
├── requirements.txt
└── Procfile
```

---

# Deploy

O projeto está hospedado online utilizando **Render**.

Fluxo de deploy:

• Código enviado para o GitHub
• Repositório conectado ao Render
• Build automático da aplicação
• Flask executado como aplicação web

Isso permite que o chatbot fique disponível online sem necessidade de rodar localmente.

---

# Objetivo do projeto

Criar um assistente simples, direto e funcional para padarias e confeitarias, centralizando informações de receitas, fermentação e técnicas de panificação, permitindo respostas rápidas através de chat.

---

# Autor

Samuel Andrade Resende
Estudante de Sistemas de Informação

---

