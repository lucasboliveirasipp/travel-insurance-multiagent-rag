"""Conector para MongoDB - Sistema de Feedback."""

from __future__ import annotations

import os
import logging
from typing import Optional

from pymongo import MongoClient
from pymongo.database import Database

logger = logging.getLogger(__name__)


class DBConnector:
    """Classe para gerenciar conexão com MongoDB."""

    def __init__(self, connection_string: str, database_name: str):
        self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        self.database = self.client[database_name]

    def get_db(self) -> Database:
        return self.database


def _create_mongo_connection() -> Optional[Database]:
    """Cria conexão com MongoDB usando variáveis de ambiente."""
    connection_string = os.getenv("MONGO_CONNECTION_STRING", "")
    db_name = os.getenv("MONGO_DB_NAME", "feedbacks")

    if not connection_string:
        logger.warning(
            "MONGO_CONNECTION_STRING não configurada. "
            "Sistema de feedback funcionará em modo offline."
        )
        return None

    try:
        connector = DBConnector(connection_string, db_name)
        connector.client.admin.command('ping')
        logger.info(f"Conectado ao MongoDB: {db_name}")
        return connector.get_db()
    except Exception as e:
        logger.error(f"Erro ao conectar ao MongoDB: {e}")
        return None


MONGO: Optional[Database] = _create_mongo_connection()
