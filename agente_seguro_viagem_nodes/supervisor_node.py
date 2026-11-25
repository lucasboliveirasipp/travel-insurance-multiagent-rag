"""Nó Supervisor - Roteamento e validação de respostas."""

import os
import sys
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any

# Configurar path para imports
current_dir = Path(__file__).parent
if str(current_dir.parent) not in sys.path:
    sys.path.insert(0, str(current_dir.parent))

from agent_state import AgentState
from config import llm
from config_constants_viagem import MAX_VALIDATION_ATTEMPTS, MAX_WRITER_ERRORS, MAX_GRAPH_ITERATIONS
from agente_seguro_viagem_prompts.supervisor_prompt import (
    SUPERVISOR_SYSTEM_PROMPT,
    INTENT_CLASSIFICATION_PROMPT,
    ROUTING_PROMPT
)
from agente_seguro_viagem_schemas.query_schemas import QueryIntent
from agente_seguro_viagem_utils.metrics import track_execution, log_structured
from agente_seguro_viagem_utils.state_helpers import get_error_count, should_stop_on_error

logger = logging.getLogger(__name__)


def classify_intent(state: AgentState) -> Dict[str, Any]:
    """Classifica a intenção da consulta do usuário.
    
    Args:
        state: Estado atual do pipeline
        
    Returns:
        Dicionário com intenção classificada
    """
    user_query = state.get("user_query", "")
    
    if not user_query:
        logger.warning("⚠️ Consulta vazia, usando intenção padrão")
        return {
            "intent": "simple_query",
            "confidence": 0.5,
            "requires_analysis": False,
            "query_type": "unknown",
            "entities": []
        }
    
    try:
        prompt = INTENT_CLASSIFICATION_PROMPT.format(user_query=user_query)
        
        messages = [
            {"role": "system", "content": SUPERVISOR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        if llm:
            response = llm.invoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Tentar parsear JSON
            try:
                intent_data = json.loads(content)
            except json.JSONDecodeError:
                # Tentar extrair JSON do texto
                import re
                json_match = re.search(r'\{[^}]+\}', content)
                if json_match:
                    intent_data = json.loads(json_match.group())
                else:
                    raise ValueError("Não foi possível extrair JSON da resposta")
            
            logger.info(f"✅ Intenção classificada: {intent_data.get('intent')} (confiança: {intent_data.get('confidence', 0)})")
            return intent_data
        else:
            logger.warning("⚠️ LLM não disponível, usando intenção padrão")
            return {
                "intent": "simple_query",
                "confidence": 0.5,
                "requires_analysis": False,
                "query_type": "unknown",
                "entities": []
            }
            
    except Exception as e:
        logger.error(f"❌ Erro ao classificar intenção: {e}", exc_info=True)
        return {
            "intent": "simple_query",
            "confidence": 0.3,
            "requires_analysis": False,
            "query_type": "error",
            "entities": []
        }


def route_to_next_agent(state: AgentState) -> str:
    """Determina o próximo agente a executar (simplificado para chatbot).
    
    Args:
        state: Estado atual do pipeline
        
    Returns:
        Nome do próximo nó ou None para finalizar
    """
    # Se validação aprovada, finalizar
    if state.get("validation_status") == "approved":
        logger.info("✅ Validação aprovada, finalizando")
        return None  # None será tratado como END em route_after_supervisor
    
    # Se há erro crítico, tentar finalizar
    if state.get("error"):
        logger.warning("⚠️ Erro detectado")
        
        # Se já temos resposta mesmo com erro, tentar aprovar
        if state.get("response"):
            return None  # None será tratado como END
        
        # Se teve muitos erros no writer, finalizar para evitar loop infinito
        if should_stop_on_error(state, "writer_errors", MAX_WRITER_ERRORS):
            writer_errors = get_error_count(state, "writer_errors")
            logger.error(f"❌ Muitos erros no writer ({writer_errors}), finalizando")
            return None  # Finalizar mesmo sem resposta
        
        return "supervisor"
    
    # Lógica de roteamento normal
    extracted_documents = state.get("extracted_documents", {})
    classified_info = state.get("classified_info", {})
    requires_analysis = state.get("requires_analysis", False)
    
    if not extracted_documents:
        return "librarian"
    elif not classified_info:
        return "classifier"
    elif requires_analysis and not state.get("analysis_result"):
        return "analyst"
    elif not state.get("response"):
        return "writer"
    else:
        # Se já tem resposta mas não foi validado, manter no supervisor para validação básica
        return "supervisor"


def validate_response(state: AgentState) -> Dict[str, Any]:
    """Validação básica da resposta gerada (simplificada para chatbot).
    
    Args:
        state: Estado atual do pipeline
        
    Returns:
        Dicionário com status de validação básica
    """
    user_query = state.get("user_query", "")
    response = state.get("response", "")
    
    if not response:
        logger.warning("⚠️ Resposta vazia, validação rejeitada")
        return {
            "validation_status": "rejected",
            "validation_feedback": "Resposta não foi gerada"
        }
    
    # Validação básica de conteúdo (simplificada)
    has_content = len(response.strip()) > 20  # Mínimo de caracteres
    has_reasonable_length = len(response.strip()) < 5000  # Máximo razoável para conversa
    
    # Validação básica: se tem conteúdo e tamanho razoável, aprovar
    if has_content and has_reasonable_length:
        logger.info("✅ Validação básica aprovada: resposta tem conteúdo válido")
        return {
            "validation_status": "approved",
            "validation_feedback": "Resposta válida"
        }
    else:
        logger.warning("⚠️ Resposta não atende critérios básicos")
        return {
            "validation_status": "rejected",
            "validation_feedback": "Resposta muito curta ou muito longa"
        }


@track_execution("supervisor")
def supervisor_node(state: AgentState) -> AgentState:
    """
    Nó Supervisor - Identifica intenção, roteia e valida respostas.
    
    Args:
        state: Estado atual do pipeline
        
    Returns:
        Estado atualizado
    """
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("EXECUTANDO: Agente Supervisor")
    logger.info("=" * 60)
    
    log_structured("info", "Supervisor iniciado", query=state.get("user_query", "")[:50])
    
    try:
        # Incrementar contador de iterações
        iteration_count = state.get("iteration_count", 0) + 1
        state["iteration_count"] = iteration_count
        logger.info(f"🔄 Iteração #{iteration_count} do grafo")
        
        # Log de progresso para monitoramento
        if iteration_count % 5 == 0:
            logger.warning(f"⚠️ {iteration_count} iterações executadas - monitorando progresso")
        
        # Se é primeira execução, classificar intenção
        if not state.get("query_intent"):
            logger.info("🔍 Classificando intenção da consulta...")
            intent_data = classify_intent(state)
            
            state["query_intent"] = intent_data.get("intent", "simple_query")
            state["requires_analysis"] = intent_data.get("requires_analysis", False)
            state["query_type"] = intent_data.get("query_type")
            state["metadata"] = state.get("metadata", {})
            state["metadata"]["entities"] = intent_data.get("entities", [])
            state["metadata"]["intent_confidence"] = intent_data.get("confidence", 0.0)
        
        # Se já temos resposta e ainda não foi validado, validar
        response = state.get("response")
        if response and not state.get("validation_status"):
            logger.info("✅ Validando resposta gerada...")
            validation_data = validate_response(state)
            
            state["validation_status"] = validation_data.get("validation_status", "approved")
            state["metadata"] = state.get("metadata", {})
            state["metadata"]["validation_feedback"] = validation_data.get("validation_feedback", "")
        
        # Determinar próximo nó
        next_node = route_to_next_agent(state)
        
        # Prevenir loop infinito: se já passou por muitos ciclos, forçar aprovação
        if iteration_count >= (MAX_GRAPH_ITERATIONS - 5) and state.get("response"):
            logger.warning(f"⚠️ Muitas iterações ({iteration_count}), aprovando automaticamente")
            state["validation_status"] = "approved"
            state["next"] = None  # None será tratado como END em route_after_supervisor
        else:
            state["next"] = next_node
        
        duration = time.time() - start_time
        log_structured(
            "info",
            "Supervisor concluído",
            duration=f"{duration:.2f}s",
            next_node=next_node,
            validation_status=state.get("validation_status")
        )
        logger.info(f"✅ Supervisor executado com sucesso. Próximo nó: {next_node}")
        return state
        
    except Exception as e:
        logger.error(f"❌ Erro no supervisor: {e}", exc_info=True)
        state["error"] = str(e)
        state["metadata"] = state.get("metadata", {})
        state["metadata"]["supervisor_errors"] = state["metadata"].get("supervisor_errors", []) + [str(e)]
        
        # Em caso de erro, tentar continuar com o fluxo se possível
        # Se já temos informações suficientes, tentar gerar resposta mesmo com erro
        if state.get("extracted_documents") and state.get("classified_info"):
            state["next"] = "writer"
            logger.warning("⚠️ Erro no supervisor, mas continuando com informações disponíveis")
        else:
            state["next"] = "supervisor"  # Tentar novamente
        
        return state

