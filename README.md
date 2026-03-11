Padaria-Bot 2.0

Padaria-Bot 2.0 é um chatbot voltado para padarias e confeitarias, desenvolvido em Python com Flask no backend e HTML/CSS/JavaScript no frontend. O sistema utiliza um banco de dados PostgreSQL e integração com IA para responder perguntas sobre receitas, fermentação e panificação.

Este projeto é uma evolução da primeira versão do Padaria-Bot, que foi desenvolvida inicialmente como um projeto acadêmico. A versão 2.0 reorganiza a arquitetura do sistema e adiciona novas funcionalidades, como cache de respostas, painel administrativo e um banco de receitas estruturado.

Demo do projeto:
https://padaria-bot-2-0.onrender.com

Arquitetura do Projeto

O sistema é dividido em três partes principais:

Chat com IA

Banco de dados de receitas

Painel administrativo

Chat com IA

O chatbot segue um fluxo de decisão em etapas para responder às mensagens do usuário:

Cálculo de fermento
Verifica se a pergunta é sobre fermentação e calcula automaticamente a quantidade ideal de fermento com base no peso da farinha e na temperatura ambiente.

Sugestão de receitas por clima
Caso o usuário peça sugestões para dias quentes ou frios, o sistema seleciona uma receita da categoria adequada.

Filtro de tema
O chatbot aceita apenas perguntas relacionadas a panificação e confeitaria.

Consulta à última receita visualizada
Caso o usuário peça ingredientes ou modo de preparo sem mencionar o nome da receita, o sistema utiliza a última receita visualizada na sessão.

Consulta ao cache
Antes de utilizar IA, o sistema verifica se aquela pergunta já foi respondida anteriormente.

Busca no banco de receitas
A mensagem do usuário é comparada com as palavras-chave das receitas armazenadas.

Busca na web
Caso a informação não esteja no banco de receitas, o sistema utiliza o modelo compound-beta da Groq, que possui acesso à internet.

Fallback com IA
Se nenhuma etapa anterior resolver, o sistema utiliza o modelo LLaMA 3 com histórico recente da conversa.

Banco de Dados

O projeto utiliza PostgreSQL com SQLAlchemy para gerenciar os dados.

O banco possui quatro tabelas principais:

Tabela	Função
receitas	Armazena todas as receitas completas
cache	Guarda respostas frequentes
ultima_receita	Registra a última receita vista por cada usuário
historico	Armazena o histórico de conversas

A conexão com o banco utiliza pool de conexões reutilizáveis, evitando abrir e fechar conexões a cada requisição e melhorando a performance da aplicação.

O banco atualmente possui 92 receitas cadastradas.

Painel Administrativo

O sistema possui um painel administrativo acessível em:

/admin

O painel permite:

Criar novas receitas

Editar receitas existentes

Excluir receitas

O acesso é protegido por senha e permite gerenciar o conteúdo do chatbot sem necessidade de alterar o código.

Sempre que uma receita é alterada, o catálogo em memória é atualizado automaticamente sem necessidade de reiniciar o servidor.

Frontend

O frontend foi desenvolvido utilizando HTML, CSS e JavaScript.

A interface possui:

área de chat com mensagens dinâmicas

indicador de digitação

animações suaves

sidebar com ações rápidas

A identidade visual utiliza tons de marrom, creme e dourado inspirados em padarias artesanais.

Em dispositivos móveis, a interface se adapta automaticamente e o chat ocupa toda a tela.

Tecnologias Utilizadas

Backend
Python
Flask

Banco de Dados
PostgreSQL
SQLAlchemy

IA
Groq API
LLaMA 3
compound-beta

Frontend
HTML
CSS
JavaScript

Deploy
Render
Gunicorn

Deploy

O projeto está hospedado no Render com deploy automático a partir do GitHub.

O processo funciona da seguinte forma:

Código enviado ao GitHub

Render detecta o push

A aplicação é buildada automaticamente

O Flask roda utilizando Gunicorn

Variáveis sensíveis como chave da API, senha do banco e senha do admin são armazenadas no ambiente do Render e não ficam expostas no código.

Estrutura do Projeto
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
Objetivo do Projeto

Criar um assistente digital simples e funcional para padarias, centralizando informações sobre receitas, fermentação e técnicas de panificação em um único sistema acessível via chat.

Autor

Samuel Andrade Resende
Estudante de Sistemas de Informação