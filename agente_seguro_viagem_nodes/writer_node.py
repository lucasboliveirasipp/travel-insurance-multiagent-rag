"""Nó Redator - Geração de respostas conversacionais."""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Configurar path para imports
current_dir = Path(__file__).parent
if str(current_dir.parent) not in sys.path:
    sys.path.insert(0, str(current_dir.parent))

from agent_state import AgentState
from config import llm, OUTPUT_DIR
from config_constants_viagem import MAX_PROMPT_CONTENT_LENGTH, MAX_SOURCES_IN_DOSSIER
from agente_seguro_viagem_prompts.writer_prompt import (
    WRITER_SYSTEM_PROMPT,
    RESPONSE_GENERATION_PROMPT,
    CONSOLIDATION_PROMPT,
    QUICK_RESPONSE_PROMPT
)
from agente_seguro_viagem_utils.metrics import track_execution, log_structured
from agente_seguro_viagem_utils.state_helpers import safe_get_nested, safe_get_analysis_result, increment_error_counter
import time

logger = logging.getLogger(__name__)


def consolidate_information(state: AgentState) -> str:
    """Consolida informações de todos os agentes para resposta conversacional.
    
    Args:
        state: Estado atual do pipeline
        
    Returns:
        Texto consolidado para resposta conversacional
    """
    librarian_info = safe_get_nested(state, "extracted_documents", "extracted_info")
    classified_info = safe_get_nested(state, "classified_info", "organized_info")
    analysis_result = safe_get_analysis_result(state)
    
    try:
        prompt = CONSOLIDATION_PROMPT.format(
            librarian_info=librarian_info[:MAX_PROMPT_CONTENT_LENGTH] if librarian_info else "Nenhuma informação encontrada",
            classified_info=classified_info[:MAX_PROMPT_CONTENT_LENGTH] if classified_info else "Nenhuma informação classificada",
            analysis_result=analysis_result[:MAX_PROMPT_CONTENT_LENGTH] if analysis_result else "N/A"
        )
        
        messages = [
            {"role": "system", "content": WRITER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        if llm:
            response = llm.invoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            return content
        else:
            # Fallback: concatenação simples
            consolidated = f"{librarian_info or 'Nenhuma informação disponível'}\n\n{classified_info or ''}"
            if analysis_result:
                consolidated += f"\n\n{analysis_result}"
            return consolidated
            
    except Exception as e:
        logger.error(f"❌ Erro na consolidação: {e}", exc_info=True)
        # Fallback
        consolidated = f"{librarian_info or 'Nenhuma informação disponível'}\n\n{classified_info or ''}"
        if analysis_result:
            consolidated += f"\n\n{analysis_result}"
        return consolidated


def validate_response_structure(response: str) -> bool:
    """Valida se a resposta tem conteúdo válido.
    
    Args:
        response: Conteúdo da resposta
        
    Returns:
        True se resposta válida
    """
    has_content = len(response.strip()) > 50
    has_reasonable_length = len(response.strip()) < 10000  # Máximo 10k caracteres
    
    return has_content and has_reasonable_length


def generate_response(state: AgentState) -> str:
    """Gera resposta conversacional natural para a consulta do usuário.
    
    Args:
        state: Estado atual do pipeline
        
    Returns:
        Resposta conversacional em texto natural
    """
    user_query = state.get("user_query", "")
    query_intent = state.get("query_intent", "simple_query")
    
    # Preparar informações para o prompt
    librarian_info = safe_get_nested(state, "extracted_documents", "extracted_info")
    classified_info = safe_get_nested(state, "classified_info", "organized_info")
    analysis_result = safe_get_analysis_result(state)
    
    # Preparar fontes (opcional, para referência)
    sources = []
    relevant_chunks = state.get("relevant_chunks", [])
    for chunk in relevant_chunks[:MAX_SOURCES_IN_DOSSIER]:
        page_num = chunk.get('page_number', 0)
        if page_num > 0:
            sources.append(f"página {page_num}")
    
    try:
        prompt = RESPONSE_GENERATION_PROMPT.format(
            user_query=user_query,
            query_intent=query_intent,
            librarian_info=librarian_info[:2000] if librarian_info else "Nenhuma informação encontrada nos documentos",
            classified_info=classified_info[:2000] if classified_info else "Nenhuma informação classificada",
            analysis_result=analysis_result[:2000] if analysis_result else "N/A"
        )
        
        messages = [
            {"role": "system", "content": WRITER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        if llm:
            response = llm.invoke(messages)
            response_content = response.content if hasattr(response, 'content') else str(response)
            
            # Validar estrutura da resposta
            if not validate_response_structure(response_content):
                logger.warning("⚠️ Resposta muito curta ou inválida, usando fallback")
                # Usar informações disponíveis como fallback
                if librarian_info:
                    response_content = f"Com base nas informações disponíveis: {librarian_info[:400]}"
                else:
                    response_content = "Desculpe, não encontrei informações suficientes para responder sua pergunta. Poderia reformular ou fornecer mais detalhes?"
            
            # Adicionar referência às fontes de forma natural se disponível
            if sources and len(sources) > 0:
                sources_text = ", ".join(sources[:3])
                response_content += f"\n\n(Informações baseadas no Book Acme Parcerias, {sources_text})"
            
            return response_content.strip()
        else:
            # Fallback: resposta direta do conteúdo disponível
            if librarian_info:
                response_text = librarian_info[:400]
                if sources:
                    sources_text = ", ".join(sources[:3])
                    response_text += f"\n\n(Informações baseadas no Book Acme Parcerias, {sources_text})"
            else:
                response_text = "Desculpe, não encontrei informações suficientes para responder sua pergunta."
            return response_text.strip()
            
    except Exception as e:
        logger.error(f"❌ Erro na geração da resposta: {e}", exc_info=True)
        # Fallback: resposta básica e amigável
        if librarian_info:
            response_text = f"Com base nas informações disponíveis: {librarian_info[:300]}"
        else:
            response_text = "Desculpe, ocorreu um erro ao processar sua pergunta. Poderia tentar novamente?"
        return response_text.strip()


def save_response(response: str, state: AgentState) -> str:
    """Salva resposta em arquivo (opcional, para histórico de conversas).
    
    Args:
        response: Conteúdo da resposta conversacional
        state: Estado atual do pipeline
        
    Returns:
        Caminho do arquivo salvo (ou string vazia se não salvar)
    """
    try:
        # Não salvar por padrão para respostas conversacionais (mais leve)
        # O histórico é mantido no Streamlit através das mensagens
        return ""
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar resposta: {e}", exc_info=True)
        return ""


@track_execution("writer")
def writer_node(state: AgentState) -> AgentState:
    """
    Nó Redator - Gera resposta conversacional natural para a consulta do usuário.
    
    Args:
        state: Estado atual do pipeline
        
    Returns:
        Estado atualizado
    """
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("EXECUTANDO: Agente Redator (Chatbot Conversacional)")
    logger.info("=" * 60)
    
    log_structured("info", "Redator iniciado")
    
    try:
        # Gerar resposta conversacional
        logger.info("💬 Gerando resposta conversacional...")
        response = generate_response(state)
        
        # Salvar resposta (opcional - histórico é mantido no Streamlit)
        response_path = save_response(response, state)
        
        # Preparar metadados básicos
        response_metadata = {
            "query": state.get("user_query", ""),
            "query_intent": state.get("query_intent", ""),
            "generated_at": datetime.now().isoformat(),
            "response_length": len(response)
        }
        
        # Atualizar estado com resposta conversacional
        state["response"] = response
        state["metadata"] = state.get("metadata", {})
        state["metadata"]["response_metadata"] = response_metadata
        
        # Próximo nó: validação básica pelo supervisor
        state["next"] = "supervisor"
        
        duration = time.time() - start_time
        response_length = len(response)
        log_structured(
            "info",
            "Redator concluído",
            duration=f"{duration:.2f}s",
            response_length=response_length
        )
        logger.info("✅ Redator executado com sucesso")
        return state
        
    except Exception as e:
        logger.error(f"❌ Erro no redator: {e}", exc_info=True)
        state["error"] = str(e)
        error_response = "Desculpe, ocorreu um erro ao processar sua pergunta. Poderia tentar novamente?"
        state["response"] = error_response
        state["next"] = "supervisor"  # Validar mesmo com erro
        
        # Incrementar contador de erros
        state = increment_error_counter(state, "writer_errors")
        
        return state

