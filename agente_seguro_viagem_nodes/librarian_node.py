"""Nó Bibliotecário - Gerenciamento e extração de PDFs."""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import MAX_CONCURRENT_FILES

# Configurar path para imports
current_dir = Path(__file__).parent
if str(current_dir.parent) not in sys.path:
    sys.path.insert(0, str(current_dir.parent))

from agent_state import AgentState
from config import FILES_DIR
from agente_seguro_viagem_utils.pdf_extractor import extract_pdf
from agente_seguro_viagem_utils.vector_store import search_documents
from agente_seguro_viagem_prompts.librarian_prompt import (
    LIBRARIAN_SYSTEM_PROMPT,
    EXTRACTION_PROMPT,
    SEARCH_PROMPT
)
from config import llm
from agente_seguro_viagem_utils.metrics import track_execution, log_structured
import time

logger = logging.getLogger(__name__)


def find_pdf_files() -> List[str]:
    """Encontra arquivos PDF no diretório de arquivos.
    
    Returns:
        Lista de caminhos de arquivos PDF
    """
    pdf_files = []
    if os.path.exists(FILES_DIR):
        for file in os.listdir(FILES_DIR):
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(FILES_DIR, file))
    
    logger.info(f"📚 Encontrados {len(pdf_files)} arquivos PDF")
    return pdf_files


def process_pdfs_parallel(pdf_files: List[str]) -> List[Dict[str, Any]]:
    """Processa múltiplos PDFs em paralelo.
    
    Args:
        pdf_files: Lista de caminhos de arquivos PDF
        
    Returns:
        Lista de resultados de extração
    """
    results = []
    
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_FILES) as executor:
        # Submeter tarefas
        futures = {
            executor.submit(extract_pdf, file_path=pdf_file): pdf_file
            for pdf_file in pdf_files
        }
        
        # Coletar resultados
        for future in as_completed(futures):
            pdf_file = futures[future]
            try:
                result = future.result()
                results.append(result)
                logger.info(f"✅ PDF processado: {os.path.basename(pdf_file)}")
            except Exception as e:
                logger.error(f"❌ Erro ao processar {pdf_file}: {e}", exc_info=True)
                results.append(None)  # Manter ordem
    
    return results


def extract_relevant_info(query: str, extracted_text: str) -> Dict[str, Any]:
    """Extrai informações relevantes usando LLM.
    
    Args:
        query: Consulta do usuário
        extracted_text: Texto extraído do PDF
        
    Returns:
        Dicionário com informações relevantes
    """
    try:
        prompt = EXTRACTION_PROMPT.format(
            user_query=query,
            extracted_text=extracted_text[:5000]  # Limitar tamanho
        )
        
        messages = [
            {"role": "system", "content": LIBRARIAN_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        if llm:
            response = llm.invoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            
            return {
                "extracted_info": content,
                "method": "llm_extraction"
            }
        else:
            # Fallback: retornar texto completo
            return {
                "extracted_info": extracted_text[:2000],
                "method": "direct_extraction"
            }
            
    except Exception as e:
        logger.error(f"❌ Erro na extração com LLM: {e}", exc_info=True)
        return {
            "extracted_info": extracted_text[:2000],
            "method": "fallback_extraction"
        }


@track_execution("librarian")
def librarian_node(state: AgentState) -> AgentState:
    """
    Nó Bibliotecário - Extrai informações dos PDFs e busca documentos relevantes.
    
    Args:
        state: Estado atual do pipeline
        
    Returns:
        Estado atualizado
    """
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("EXECUTANDO: Agente Bibliotecário")
    logger.info("=" * 60)
    
    try:
        user_query = state.get("user_query", "")
        log_structured("info", "Bibliotecário iniciado", query=user_query[:50])
        
        # Buscar documentos relevantes usando busca vetorial
        logger.info("🔍 Buscando documentos relevantes...")
        relevant_chunks = search_documents(user_query, top_k=5)
        
        if relevant_chunks:
            logger.info(f"✅ Encontrados {len(relevant_chunks)} chunks relevantes")
            state["relevant_chunks"] = relevant_chunks
            
            # Consolidar informações dos chunks
            consolidated_text = "\n\n".join([
                f"[Página {chunk.get('page_number', 0)}] {chunk.get('content', '')}"
                for chunk in relevant_chunks
            ])
            
            # Extrair informações relevantes
            extracted_info = extract_relevant_info(user_query, consolidated_text)
            
            state["extracted_documents"] = {
                "chunks": relevant_chunks,
                "consolidated_text": consolidated_text,
                "extracted_info": extracted_info.get("extracted_info", ""),
                "extraction_method": extracted_info.get("method", "unknown"),
                "total_chunks": len(relevant_chunks)
            }
        else:
            # Se não encontrou na busca vetorial, tentar extrair de PDFs disponíveis
            logger.info("⚠️ Nenhum chunk encontrado, tentando extrair PDFs...")
            pdf_files = find_pdf_files()
            
            if pdf_files:
                # Processar PDFs em paralelo se houver múltiplos
                if len(pdf_files) > 1:
                    logger.info(f"📚 Processando {len(pdf_files)} PDFs em paralelo...")
                    extracted_results = process_pdfs_parallel(pdf_files[:MAX_CONCURRENT_FILES])
                    
                    # Combinar resultados
                    all_text = []
                    all_pages = []
                    for result in extracted_results:
                        if result and result.get("text"):
                            all_text.append(result["text"])
                            all_pages.extend(result.get("pages", []))
                            # NOTA: Indexação deve ser feita previamente, não durante execução
                            # Para indexar documentos, use o script: python scripts/index_documents.py
                    
                    # Buscar nos dados já indexados (se houver)
                    relevant_chunks = search_documents(user_query, top_k=5)
                    
                    if relevant_chunks:
                        consolidated_text = "\n\n".join([
                            f"[Página {chunk.get('page_number', 0)}] {chunk.get('content', '')}"
                            for chunk in relevant_chunks
                        ])
                        extracted_info = extract_relevant_info(user_query, consolidated_text)
                        
                        state["extracted_documents"] = {
                            "chunks": relevant_chunks,
                            "consolidated_text": consolidated_text,
                            "extracted_info": extracted_info.get("extracted_info", ""),
                            "extraction_method": extracted_info.get("method", "unknown"),
                            "total_chunks": len(relevant_chunks),
                            "pdfs_processed": len(extracted_results)
                        }
                    else:
                        # Usar texto combinado diretamente
                        combined_text = "\n\n".join(all_text)
                        extracted_info = extract_relevant_info(user_query, combined_text)
                        state["extracted_documents"] = {
                            "text": combined_text,
                            "extracted_info": extracted_info.get("extracted_info", ""),
                            "extraction_method": extracted_info.get("method", "unknown"),
                            "total_pages": sum(len(r.get("pages", [])) for r in extracted_results if r),
                            "pdfs_processed": len(extracted_results)
                        }
                else:
                    # Processar único PDF
                    try:
                        extracted_data = extract_pdf(file_path=pdf_files[0])
                        
                        # NOTA: Indexação deve ser feita previamente, não durante execução
                        # Para indexar documentos, use o script: python scripts/index_documents.py
                        # Por enquanto, apenas buscar nos dados já indexados
                        relevant_chunks = search_documents(user_query, top_k=5)
                        
                        if relevant_chunks:
                            consolidated_text = "\n\n".join([
                                f"[Página {chunk.get('page_number', 0)}] {chunk.get('content', '')}"
                                for chunk in relevant_chunks
                            ])
                            extracted_info = extract_relevant_info(user_query, consolidated_text)
                            
                            state["extracted_documents"] = {
                                "chunks": relevant_chunks,
                                "consolidated_text": consolidated_text,
                                "extracted_info": extracted_info.get("extracted_info", ""),
                                "extraction_method": extracted_info.get("method", "unknown"),
                                "total_chunks": len(relevant_chunks)
                            }
                        else:
                            # Usar texto extraído diretamente
                            extracted_info = extract_relevant_info(user_query, extracted_data.get("text", ""))
                            state["extracted_documents"] = {
                                "text": extracted_data.get("text", ""),
                                "extracted_info": extracted_info.get("extracted_info", ""),
                                "extraction_method": extracted_info.get("method", "unknown"),
                                "total_pages": extracted_data.get("total_pages", 0)
                            }
                    except Exception as e:
                        logger.error(f"❌ Erro ao extrair PDF: {e}", exc_info=True)
                        state["extracted_documents"] = {
                            "error": str(e),
                            "extracted_info": ""
                        }
            else:
                logger.warning("⚠️ Nenhum PDF disponível")
                state["extracted_documents"] = {
                    "error": "Nenhum documento disponível",
                    "extracted_info": ""
                }
        
        state["next"] = "classifier"
        duration = time.time() - start_time
        chunks_found = len(state.get("relevant_chunks", []))
        log_structured(
            "info",
            "Bibliotecário concluído",
            duration=f"{duration:.2f}s",
            chunks_found=chunks_found
        )
        logger.info("✅ Bibliotecário executado com sucesso")
        return state
        
    except Exception as e:
        logger.error(f"❌ Erro no bibliotecário: {e}", exc_info=True)
        state["error"] = str(e)
        state["metadata"] = state.get("metadata", {})
        state["metadata"]["librarian_errors"] = state["metadata"].get("librarian_errors", []) + [str(e)]
        
        # Tentar continuar mesmo sem documentos extraídos
        # O classificador pode trabalhar com informações mínimas
        if not state.get("extracted_documents"):
            state["extracted_documents"] = {
                "error": str(e),
                "extracted_info": "",
                "extraction_method": "error"
            }
        state["next"] = "classifier"  # Tentar continuar
        return state

