# Documentação da API - Padaria-Bot

Endpoints principais

- `GET /api/v1/health` : retorna JSON `{ "status": "ok" }`.
- `POST /api/v1/chat` : recebe JSON `{ "mensagem": "texto" }` e retorna `{ "resposta": "texto" }`.

Exemplo de requisição com `curl`:

```
curl -X POST http://localhost:5000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"mensagem":"Como faço uma massa de pão frances?"}'
```

Variáveis de ambiente necessárias

- `API_KEY` : chave para acesso à API generativa.
