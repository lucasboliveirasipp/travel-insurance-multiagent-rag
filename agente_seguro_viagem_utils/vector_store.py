"""Armazenamento vetorial usando Azure AI Search.

Gerencia indexação e busca semântica de documentos extraídos dos PDFs.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import requests

# Configurar path para imports
current_dir = Path(__file__).parent
if str(current_dir.parent) not in sys.path:
    sys.path.insert(0, str(current_dir.parent))

from config import (
    search_client,
    ai_search_available,
    AZURE_AI_SEARCH_INDEX_NAME,
    AZURE_AI_SEARCH_ENDPOINT,
    AZURE_AI_SEARCH_KEY,
    llm
)
from agente_seguro_viagem_utils.cache_manager import get_cache_manager, get_cache_key

logger = logging.getLogger(__name__)

# Importação lazy para embeddings
EMBEDDINGS_AVAILABLE = False
try:
    from langchain_openai import AzureOpenAIEmbeddings
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Azure OpenAI Embeddings não disponível")

# Importação para busca vetorial
VECTOR_QUERY_AVAILABLE = False
try:
    from azure.search.documents.models import VectorizedQuery
    VECTOR_QUERY_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ VectorizedQuery não disponível, usando API REST")


def get_embeddings() -> Optional[Any]:
    """Retorna instância de embeddings.
    
    Returns:
        Instância de AzureOpenAIEmbeddings ou None
    """
    if not EMBEDDINGS_AVAILABLE:
        return None
    
    try:
        from config import (
            AZURE_EMBEDDINGS_ENDPOINT,
            AZURE_EMBEDDINGS_KEY,
            AZURE_EMBEDDINGS_DEPLOYMENT,
            AZURE_EMBEDDINGS_API_VERSION
        )
        
        embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=AZURE_EMBEDDINGS_ENDPOINT,
            openai_api_key=AZURE_EMBEDDINGS_KEY,
            api_version=AZURE_EMBEDDINGS_API_VERSION,
            azure_deployment=AZURE_EMBEDDINGS_DEPLOYMENT
        )
        return embeddings
    except Exception as e:
        logger.warning(f"⚠️ Erro ao inicializar embeddings: {e}")
        return None


def create_embedding(text: str) -> Optional[List[float]]:
    """Cria embedding para um texto.
    
    Args:
        text: Texto para criar embedding
        
    Returns:
        Lista de floats representando o embedding ou None
    """
    embeddings = get_embeddings()
    if not embeddings:
        logger.warning("⚠️ Embeddings não disponíveis")
        return None
    
    try:
        result = embeddings.embed_query(text)
        return result
    except Exception as e:
        logger.error(f"❌ Erro ao criar embedding: {e}", exc_info=True)
        return None


def index_document(
    document_id: str,
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
    page_number: Optional[int] = None
) -> bool:
    """Indexa um documento no Azure AI Search.
    
    Args:
        document_id: ID único do documento
        text: Texto do documento
        metadata: Metadados adicionais
        page_number: Número da página (se aplicável)
        
    Returns:
        True se indexado com sucesso
    """
    if not ai_search_available or not search_client:
        logger.warning("⚠️ Azure AI Search não disponível, pulando indexação")
        return False
    
    try:
        logger.info(f"📚 Indexando documento: {document_id}")
        
        # Criar embedding
        embedding = create_embedding(text)
        
        # Preparar documento
        doc = {
            "id": document_id,
            "content": text,
            "page_number": page_number or 0,
        }
        
        # Adicionar embedding se disponível
        if embedding:
            doc["contentVector"] = embedding
        
        # Adicionar metadados
        if metadata:
            for key, value in metadata.items():
                if key not in ["id", "content", "contentVector"]:
                    doc[key] = value
        
        # Indexar
        search_client.upload_documents(documents=[doc])
        
        logger.info(f"✅ Documento indexado: {document_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao indexar documento: {e}", exc_info=True)
        return False


def search_documents_rest(
    query: str,
    query_embedding: List[float],
    top_k: int = 5,
    filters: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Busca documentos usando API REST diretamente.
    
    Args:
        query: Texto da consulta
        query_embedding: Embedding da consulta
        top_k: Número de resultados
        filters: Filtros OData (opcional)
        
    Returns:
        Lista de documentos
    """
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_AI_SEARCH_KEY,
    }
    
    url = f"{AZURE_AI_SEARCH_ENDPOINT}/indexes/{AZURE_AI_SEARCH_INDEX_NAME}/docs/search?api-version=2023-11-01"
    
    # Payload para busca híbrida (texto + vetor)
    payload = {
        "search": query,
        "top": top_k,
        "select": "id,content,filepathField",
        "vectorQueries": [
            {
                "kind": "vector",
                "vector": query_embedding,
                "fields": "contentVector",
                "k": top_k
            }
        ]
    }
    
    if filters:
        payload["filter"] = filters
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("value", [])
            
            documents = []
            for result in results:
                doc = {
                    "id": result.get("id", ""),
                    "content": result.get("content", ""),
                    "score": result.get("@search.score", 0.0),
                    "filepathField": result.get("filepathField", ""),
                    "metadata": {"filepathField": result.get("filepathField", "")}
                }
                documents.append(doc)
            
            return documents
        else:
            logger.error(f"❌ Erro na API REST: {response.status_code} - {response.text[:200]}")
            return []
    except Exception as e:
        logger.error(f"❌ Erro na busca REST: {e}")
        return []


def search_documents(
    query: str,
    top_k: int = 5,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Busca documentos relevantes usando busca semântica.
    
    Args:
        query: Consulta de busca
        top_k: Número de resultados a retornar
        filters: Filtros adicionais (ex: {"file_name": "book.pdf"})
        
    Returns:
        Lista de documentos relevantes com scores
    """
    if not AZURE_AI_SEARCH_ENDPOINT or not AZURE_AI_SEARCH_KEY:
        logger.warning("⚠️ Azure AI Search não configurado, retornando lista vazia")
        return []
    
    try:
        logger.info(f"🔍 Buscando: {query[:50]}...")
        
        # Verificar cache
        cache = get_cache_manager()
        cache_key = get_cache_key("search", query, top_k=top_k, filters=filters)
        
        if cache:
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info("✅ Resultado encontrado no cache")
                return cached_result
        
        # Criar embedding da query
        query_embedding = create_embedding(query)
        
        if not query_embedding:
            logger.warning("⚠️ Não foi possível criar embedding, usando busca textual")
            # Fallback para busca textual apenas
            if ai_search_available and search_client:
                results = search_client.search(
                    search_text=query,
                    top=top_k,
                    include_total_count=True
                )
                documents = []
                for result in results:
                    doc = {
                        "id": result.get("id", ""),
                        "content": result.get("content", ""),
                        "score": result.get("@search.score", 0.0),
                        "metadata": {"filepathField": result.get("filepathField", "")}
                    }
                    documents.append(doc)
                return documents[:top_k]
            return []
        
        # Preparar filtros OData
        filter_string = None
        if filters:
            filter_parts = []
            for k, v in filters.items():
                if isinstance(v, str):
                    filter_parts.append(f"{k} eq '{v}'")
                elif isinstance(v, (int, float)):
                    filter_parts.append(f"{k} eq {v}")
                elif isinstance(v, list):
                    values = " or ".join([f"{k} eq '{item}'" for item in v])
                    filter_parts.append(f"({values})")
            if filter_parts:
                filter_string = " and ".join(filter_parts)
                logger.info(f"🔍 Aplicando filtros: {filter_string}")
        
        # Tentar usar VectorizedQuery se disponível
        if VECTOR_QUERY_AVAILABLE and ai_search_available and search_client:
            try:
                vector_query = VectorizedQuery(
                    vector=query_embedding,
                    k_nearest_neighbors=top_k,
                    fields="contentVector"
                )
                
                search_kwargs = {
                    "search_text": query,
                    "vector_queries": [vector_query],
                    "top": top_k,
                    "include_total_count": True
                }
                
                if filter_string:
                    search_kwargs["filter"] = filter_string
                
                results = search_client.search(**search_kwargs)
                
                documents = []
                seen_ids = set()
                
                for result in results:
                    doc_id = result.get("id", "")
                    if doc_id in seen_ids:
                        continue
                    seen_ids.add(doc_id)
                    
                    doc = {
                        "id": doc_id,
                        "content": result.get("content", ""),
                        "score": result.get("@search.score", 0.0),
                        "filepathField": result.get("filepathField", ""),
                        "metadata": {"filepathField": result.get("filepathField", "")}
                    }
                    documents.append(doc)
                
                documents.sort(key=lambda x: x.get("score", 0.0), reverse=True)
                documents = documents[:top_k]
                
                logger.info(f"✅ Encontrados {len(documents)} documentos (VectorizedQuery)")
                
                if cache:
                    cache.set(cache_key, documents, cache_type="search")
                
                return documents
                
            except Exception as e:
                logger.warning(f"⚠️ VectorizedQuery falhou: {e}, tentando API REST...")
        
        # Fallback para API REST
        logger.info("🔄 Usando API REST para busca vetorial...")
        documents = search_documents_rest(query, query_embedding, top_k, filter_string)
        
        if documents:
            logger.info(f"✅ Encontrados {len(documents)} documentos (API REST)")
            if cache:
                cache.set(cache_key, documents, cache_type="search")
        else:
            logger.warning("⚠️ Nenhum documento encontrado")
        
        return documents
        
    except Exception as e:
        logger.error(f"❌ Erro na busca: {e}", exc_info=True)
        return []


def index_pdf_pages(extracted_data: Dict[str, Any]) -> int:
    """Indexa todas as páginas de um PDF extraído.
    
    Args:
        extracted_data: Dados extraídos do PDF (de extract_pdf)
        
    Returns:
        Número de páginas indexadas
    """
    logger.info("=" * 60)
    logger.info("INDEXANDO PÁGINAS DO PDF")
    logger.info("=" * 60)
    
    file_name = extracted_data.get("file_name", "unknown")
    pages = extracted_data.get("pages", [])
    
    indexed_count = 0
    
    for page in pages:
        page_number = page.get("page_number", 0)
        page_text = page.get("text", "")
        
        if not page_text.strip():
            continue
        
        document_id = f"{file_name}_page_{page_number}"
        metadata = {
            "file_name": file_name,
            "extraction_method": extracted_data.get("extraction_method", "unknown")
        }
        
        if index_document(document_id, page_text, metadata, page_number):
            indexed_count += 1
    
    logger.info(f"✅ {indexed_count} páginas indexadas de {len(pages)} total")
    return indexed_count

