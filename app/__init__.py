from flask import Flask, jsonify
import os
from flask_cors import CORS
from flask_restx import Api
import logging

from routes.chat_routes import chat_ns


def create_app(config_object: str = None) -> Flask:
    app = Flask(__name__)
    # Chave para sessões; use variável de ambiente em produção
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-this")
    CORS(app)
    logging.basicConfig(level=logging.INFO)

    api = Api(app, version="1.0", title="Padaria Bot API", description="API para o Padaria-Bot")
    api.add_namespace(chat_ns, path="/api/v1/chat")

    @app.route("/api/v1/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    return app


__all__ = ["create_app"]
