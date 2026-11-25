"""Nó Classificador - Classificação e organização de informações."""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any

# Configurar path para imports
current_dir = Path(__file__).parent
if str(current_dir.parent) not in sys.path:
    sys.path.insert(0, str(current_dir.parent))

from agent_state import AgentState
from config import llm
from agente_seguro_viagem_prompts.classifier_prompt import (
    CLASSIFIER_SYSTEM_PROMPT,
    CLASSIFICATION_PROMPT,
    ORGANIZATION_PROMPT
)
from agente_seguro_viagem_utils.metrics import track_execution, log_structured
import time

logger = logging.getLogger(__name__)


def classify_info(state: AgentState) -> Dict[str, Any]:
    """Classifica informações extraídas.
    
    Args:
        state: Estado atual do pipeline
        
    Returns:
        Dicionário com informações classificadas
    """
    user_query = state.get("user_query", "")
    extracted_documents = state.get("extracted_documents", {})
    
    extracted_info = extracted_documents.get("extracted_info", "")
    if not extracted_info:
        extracted_info = extracted_documents.get("consolidated_text", "")
    
    if not extracted_info:
        logger.warning("⚠️ Nenhuma informação extraída para classificar")
        return {
            "query_type": "unknown",
            "organized_info": {},
            "classification_method": "default"
        }
    
    try:
        prompt = CLASSIFICATION_PROMPT.format(
            user_query=user_query,
            extracted_info=extracted_info[:3000]  # Limitar tamanho
        )
        
        messages = [
            {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        if llm:
            response = llm.invoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Organizar informações
            org_prompt = ORGANIZATION_PROMPT.format(
                classified_info=content,
                user_query=user_query
            )
            
            org_messages = [
                {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": org_prompt}
            ]
            
            org_response = llm.invoke(org_messages)
            org_content = org_response.content if hasattr(org_response, 'content') else str(org_response)
            
            return {
                "classification": content,
                "organized_info": org_content,
                "query_type": state.get("query_type", "unknown"),
                "classification_method": "llm"
            }
        else:
            # Fallback: organização simples
            return {
                "classification": "Classificação não disponível (LLM não disponível)",
                "organized_info": extracted_info[:1000],
                "query_type": state.get("query_type", "unknown"),
                "classification_method": "fallback"
            }
            
    except Exception as e:
        logger.error(f"❌ Erro na classificação: {e}", exc_info=True)
        return {
            "classification": f"Erro na classificação: {str(e)}",
            "organized_info": extracted_info[:1000] if extracted_info else {},
            "query_type": "error",
            "classification_method": "error"
        }


@track_execution("classifier")
def classifier_node(state: AgentState) -> AgentState:
    """
    Nó Classificador - Classifica e organiza informações extraídas.
    
    Args:
        state: Estado atual do pipeline
        
    Returns:
        Estado atualizado
    """
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("EXECUTANDO: Agente Classificador")
    logger.info("=" * 60)
    
    log_structured("info", "Classificador iniciado")
    
    try:
        # Classificar informações
        logger.info("🔍 Classificando informações...")
        classified_data = classify_info(state)
        
        state["classified_info"] = classified_data
        state["query_type"] = classified_data.get("query_type", state.get("query_type", "unknown"))
        
        # Determinar próximo nó
        requires_analysis = state.get("requires_analysis", False)
        if requires_analysis:
            state["next"] = "analyst"
        else:
            state["next"] = "writer"
        
        duration = time.time() - start_time
        log_structured(
            "info",
            "Classificador concluído",
            duration=f"{duration:.2f}s",
            query_type=state.get("query_type", "unknown")
        )
        logger.info(f"✅ Classificador executado com sucesso. Tipo: {state['query_type']}")
        return state
        
    except Exception as e:
        logger.error(f"❌ Erro no classificador: {e}", exc_info=True)
        state["error"] = str(e)
        state["metadata"] = state.get("metadata", {})
        state["metadata"]["classifier_errors"] = state["metadata"].get("classifier_errors", []) + [str(e)]
        
        # Criar classificação mínima para continuar
        if not state.get("classified_info"):
            state["classified_info"] = {
                "classification": f"Erro na classificação: {str(e)}",
                "organized_info": state.get("extracted_documents", {}).get("extracted_info", ""),
                "query_type": "error",
                "classification_method": "error"
            }
        
        # Determinar próximo nó mesmo com erro
        requires_analysis = state.get("requires_analysis", False)
        if requires_analysis:
            state["next"] = "analyst"
        else:
            state["next"] = "writer"
        return state

