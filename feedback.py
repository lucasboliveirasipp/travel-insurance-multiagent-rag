"""Sistema de Feedback para o Agente Seguro Viagem."""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional

import streamlit as st
from pymongo.database import Database

logger = logging.getLogger(__name__)


def get_local_datetime_for_mongo() -> datetime:
    """Retorna datetime ajustado para horário de Brasília (UTC-3)."""
    return datetime.utcnow() - timedelta(hours=3)


def log_interaction(
    mongo_db: Optional[Database],
    agent_name: str,
    thread_id: str,
    user_question: str,
    chatbot_response: str
) -> str:
    """Salva a interação no MongoDB. Retorna response_id."""
    response_id = str(uuid.uuid4())

    if mongo_db is None:
        return response_id

    try:
        collection = mongo_db[agent_name]

        collection.update_one(
            {"_id": thread_id},
            {
                "$set": {
                    "agent_name": agent_name,
                    "datetime": get_local_datetime_for_mongo()
                },
                "$push": {
                    "interactions": {
                        "response_id": response_id,
                        "timestamp": get_local_datetime_for_mongo(),
                        "user_question": user_question,
                        "chatbot_response": chatbot_response,
                        "feedback": None,
                        "justification": None,
                        "feedback_timestamp": None
                    }
                }
            },
            upsert=True
        )
        logger.info(f"Interação salva: {response_id[:8]}...")

    except Exception as e:
        logger.error(f"Erro ao salvar interação: {e}")

    return response_id


def render_feedback_widget(
    mongo_db: Optional[Database],
    agent_name: str,
    thread_id: str,
    response_id: str
) -> None:
    """Renderiza o widget de feedback (thumbs up/down) e salva a avaliação."""
    feedback_key = f"feedback_{agent_name}_{response_id}"
    submitted_key = f"submitted_{agent_name}_{response_id}"

    if submitted_key not in st.session_state:
        st.session_state[submitted_key] = False

    if st.session_state[submitted_key]:
        st.info("Obrigado pela sua avaliação!")
        return

    st.markdown("---")
    st.markdown("**Avalie esta resposta:**")

    feedback = st.feedback("thumbs", key=feedback_key)

    justification = ""
    if feedback == 0:
        justification_key = f"justification_{agent_name}_{response_id}"
        justification = st.text_area(
            "O que poderia ser melhorado?",
            key=justification_key,
            placeholder="Descreva o que esperava ou o que pode ser aprimorado...",
        )
        if not justification.strip():
            st.warning("Para enviar feedback negativo, preencha a justificativa.")
            return

    if feedback in [0, 1]:
        _save_feedback(
            mongo_db=mongo_db,
            agent_name=agent_name,
            thread_id=thread_id,
            response_id=response_id,
            feedback=feedback,
            justification=justification if feedback == 0 else None,
            submitted_key=submitted_key
        )


def _save_feedback(
    mongo_db: Optional[Database],
    agent_name: str,
    thread_id: str,
    response_id: str,
    feedback: int,
    justification: Optional[str],
    submitted_key: str
) -> None:
    """Salva o feedback no MongoDB e atualiza o estado da sessão."""
    if mongo_db is not None:
        try:
            collection = mongo_db[agent_name]

            collection.update_one(
                {
                    "_id": thread_id,
                    "interactions.response_id": response_id
                },
                {
                    "$set": {
                        "interactions.$.feedback": feedback,
                        "interactions.$.justification": justification,
                        "interactions.$.feedback_timestamp": get_local_datetime_for_mongo()
                    }
                }
            )
            logger.info(f"Feedback salvo: {'positivo' if feedback == 1 else 'negativo'}")

        except Exception as e:
            logger.error(f"Erro ao salvar feedback: {e}")
            st.error(f"Erro ao salvar feedback: {e}")
            return

    st.session_state[submitted_key] = True
    st.success("Obrigado pelo seu feedback!")
    st.rerun()
