"""Nó Analista - Análise de lógica complexa de seguradora."""

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
from agente_seguro_viagem_prompts.analyst_prompt import (
    ANALYST_SYSTEM_PROMPT,
    COMPLEX_ANALYSIS_PROMPT,
    COMPARISON_PROMPT,
    RULE_APPLICATION_PROMPT
)
from agente_seguro_viagem_utils.metrics import track_execution, log_structured
import time

logger = logging.getLogger(__name__)


def perform_analysis(state: AgentState) -> Dict[str, Any]:
    """Realiza análise complexa da consulta.
    
    Args:
        state: Estado atual do pipeline
        
    Returns:
        Dicionário com resultado da análise
    """
    user_query = state.get("user_query", "")
    query_intent = state.get("query_intent", "simple_query")
    classified_info = state.get("classified_info", {})
    extracted_documents = state.get("extracted_documents", {})
    
    organized_info = classified_info.get("organized_info", "")
    if not organized_info:
        organized_info = extracted_documents.get("extracted_info", "")
    
    relevant_documents = extracted_documents.get("chunks", [])
    documents_text = "\n\n".join([
        f"[Página {doc.get('page_number', 0)}] {doc.get('content', '')}"
        for doc in relevant_documents[:5]
    ])
    
    try:
        # Escolher prompt baseado no tipo de consulta
        if query_intent == "comparison":
            prompt = COMPARISON_PROMPT.format(
                user_query=user_query,
                items_to_compare=organized_info[:2000],
                available_info=documents_text[:3000]
            )
        elif query_intent == "complex_analysis":
            prompt = COMPLEX_ANALYSIS_PROMPT.format(
                user_query=user_query,
                classified_info=organized_info[:2000],
                relevant_documents=documents_text[:3000]
            )
        else:
            # Análise padrão
            prompt = COMPLEX_ANALYSIS_PROMPT.format(
                user_query=user_query,
                classified_info=organized_info[:2000],
                relevant_documents=documents_text[:3000]
            )
        
        messages = [
            {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        if llm:
            response = llm.invoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            
            return {
                "analysis": content,
                "analysis_type": query_intent,
                "method": "llm_analysis"
            }
        else:
            logger.warning("⚠️ LLM não disponível, análise não realizada")
            return {
                "analysis": "Análise não disponível (LLM não disponível)",
                "analysis_type": query_intent,
                "method": "unavailable"
            }
            
    except Exception as e:
        logger.error(f"❌ Erro na análise: {e}", exc_info=True)
        return {
            "analysis": f"Erro na análise: {str(e)}",
            "analysis_type": query_intent,
            "method": "error"
        }


@track_execution("analyst")
def analyst_node(state: AgentState) -> AgentState:
    """
    Nó Analista - Processa consultas com lógica complexa de seguradora.
    
    Args:
        state: Estado atual do pipeline
        
    Returns:
        Estado atualizado
    """
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("EXECUTANDO: Agente Analista")
    logger.info("=" * 60)
    
    log_structured("info", "Analista iniciado")
    
    try:
        requires_analysis = state.get("requires_analysis", False)
        
        if not requires_analysis:
            logger.info("ℹ️ Análise não requerida, pulando...")
            state["analysis_result"] = None
            state["next"] = "writer"
            return state
        
        # Realizar análise
        logger.info("🔍 Realizando análise complexa...")
        analysis_result = perform_analysis(state)
        
        state["analysis_result"] = analysis_result
        
        state["next"] = "writer"
        duration = time.time() - start_time
        log_structured(
            "info",
            "Analista concluído",
            duration=f"{duration:.2f}s",
            analysis_type=state.get("analysis_result", {}).get("analysis_type", "unknown")
        )
        logger.info("✅ Analista executado com sucesso")
        return state
        
    except Exception as e:
        logger.error(f"❌ Erro no analista: {e}", exc_info=True)
        state["error"] = str(e)
        state["analysis_result"] = {
            "analysis": f"Erro na análise: {str(e)}",
            "analysis_type": "error",
            "method": "error"
        }
        state["next"] = "writer"  # Continuar mesmo com erro
        return state

