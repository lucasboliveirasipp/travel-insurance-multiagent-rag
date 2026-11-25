"""Serviço de indexação para Azure AI Search.

Gerencia criação de índices, extração de documentos, chunking e upload
de documentos vetorizados para Azure AI Search.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from glob import glob

# Configurar path para imports
current_dir = Path(__file__).parent
if str(current_dir.parent) not in sys.path:
    sys.path.insert(0, str(current_dir.parent))

from config import (
    AZURE_AI_SEARCH_ENDPOINT,
    AZURE_AI_SEARCH_KEY,
    AZURE_AI_SEARCH_INDEX_NAME,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_EMBEDDINGS_ENDPOINT,
    AZURE_EMBEDDINGS_KEY,
    AZURE_EMBEDDINGS_DEPLOYMENT,
    AZURE_EMBEDDINGS_API_VERSION,
    ai_search_available
)
from agente_seguro_viagem_utils.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)

# Importações lazy para dependências opcionais
PDF_AVAILABLE = False
try:
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ PyPDF2 não disponível")

EMBEDDINGS_AVAILABLE = False
try:
    from langchain_openai import AzureOpenAIEmbeddings
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Azure OpenAI Embeddings não disponível")

REQUESTS_AVAILABLE = False
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ requests não disponível")

TQDM_AVAILABLE = False
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ tqdm não disponível")


def delete_index(index_name: str) -> bool:
    """Deleta um índice do Azure AI Search.
    
    Args:
        index_name: Nome do índice a ser deletado
        
    Returns:
        True se deletado com sucesso, False caso contrário
    """
    if not REQUESTS_AVAILABLE:
        logger.error("❌ Biblioteca requests não disponível")
        return False
    
    if not AZURE_AI_SEARCH_ENDPOINT or not AZURE_AI_SEARCH_KEY:
        logger.error("❌ Azure AI Search não configurado")
        return False
    
    try:
        logger.info("=" * 60)
        logger.info(f"DELETANDO ÍNDICE: {index_name}")
        logger.info("=" * 60)
        
        headers = {
            "api-key": AZURE_AI_SEARCH_KEY,
        }
        
        url = f"{AZURE_AI_SEARCH_ENDPOINT}/indexes/{index_name}?api-version=2023-11-01"
        
        response = requests.delete(url, headers=headers, timeout=30)
        
        if response.status_code == 204:
            logger.info(f"✅ Índice '{index_name}' deletado com sucesso!")
            return True
        elif response.status_code == 404:
            logger.warning(f"⚠️ Índice '{index_name}' não encontrado.")
            return True  # Considera sucesso se não existe
        else:
            logger.error(f"❌ Erro ao deletar índice: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao deletar índice: {e}", exc_info=True)
        return False


def get_embeddings_client() -> Optional[Any]:
    """Retorna cliente de embeddings configurado.
    
    Returns:
        Instância de AzureOpenAIEmbeddings ou None
    """
    if not EMBEDDINGS_AVAILABLE:
        return None
    
    try:
        # Usar configurações hardcoded do config.py (valores padrão)
        # Podem ser sobrescritos via variáveis de ambiente se necessário
        embeddings_endpoint = AZURE_EMBEDDINGS_ENDPOINT or AZURE_OPENAI_ENDPOINT
        embeddings_key = AZURE_EMBEDDINGS_KEY or AZURE_OPENAI_KEY
        embeddings_deployment = AZURE_EMBEDDINGS_DEPLOYMENT
        embeddings_api_version = AZURE_EMBEDDINGS_API_VERSION or AZURE_OPENAI_API_VERSION or "2023-05-15"
        
        if not embeddings_endpoint or not embeddings_key:
            logger.warning("⚠️ Credenciais de embeddings não configuradas")
            return None
        
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment=embeddings_deployment,
            azure_endpoint=embeddings_endpoint,
            api_version=embeddings_api_version,
            api_key=embeddings_key
        )
        
        logger.info(f"✅ Embeddings configurados: {embeddings_deployment}")
        return embeddings
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar embeddings: {e}", exc_info=True)
        return None


def create_embedding(text: str) -> Optional[List[float]]:
    """Cria embedding para um texto.
    
    Args:
        text: Texto para criar embedding
        
    Returns:
        Lista de floats representando o embedding ou None
    """
    embeddings_client = get_embeddings_client()
    if not embeddings_client:
        logger.warning("⚠️ Embeddings não disponíveis")
        return None
    
    try:
        result = embeddings_client.embed_documents([text])
        return result[0] if result else None
    except Exception as e:
        logger.error(f"❌ Erro ao criar embedding: {e}", exc_info=True)
        return None


def load_index_template(template_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Carrega template de índice do Azure AI Search.
    
    Args:
        template_path: Caminho para arquivo de template (opcional)
        
    Returns:
        Template de índice ou None se não encontrado
    """
    if template_path and os.path.exists(template_path):
        template_file = template_path
    else:
        # Tentar encontrar template_index.json no diretório do projeto
        base_dir = Path(__file__).parent.parent
        template_file = base_dir / "template_index.json"
        
        if not template_file.exists():
            logger.warning("⚠️ template_index.json não encontrado, usando template padrão")
            return get_default_index_template()
    
    try:
        with open(template_file, "r", encoding="utf-8") as f:
            template = json.load(f)
        logger.info(f"✅ Template carregado: {template_file}")
        return template
    except Exception as e:
        logger.error(f"❌ Erro ao carregar template: {e}", exc_info=True)
        return get_default_index_template()


def get_default_index_template() -> Dict[str, Any]:
    """Retorna template padrão de índice.
    
    Returns:
        Template de índice padrão
    """
    return {
        "name": "",
        "fields": [
            {
                "name": "id",
                "type": "Edm.String",
                "key": True,
                "searchable": False,
                "retrievable": True
            }
        ],
        "semantic": {
            "configurations": [
                {
                    "name": "",
                    "prioritizedFields": {
                        "titleField": {"fieldName": "content"},
                        "prioritizedContentFields": [{"fieldName": "content"}]
                    }
                }
            ]
        },
        "vectorSearch": {
            "algorithms": [
                {
                    "name": "vector-profile-1700855443968",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine"
                    }
                }
            ],
            "profiles": [
                {
                    "name": "vector-profile-1700855443968",
                    "algorithm": "vector-profile-1700855443968"
                }
            ]
        }
    }


def create_index_v2(
    index_name: str,
    semantic_name: str,
    columns: List[Dict[str, Any]],
    template_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Cria um índice no Azure AI Search.
    
    Args:
        index_name: Nome do índice a ser criado
        semantic_name: Nome semântico do índice
        columns: Lista de dicionários com informações das colunas
        template_path: Caminho para template (opcional)
        
    Returns:
        Template do índice criado ou None se falhou
    """
    if not REQUESTS_AVAILABLE:
        logger.error("❌ Biblioteca requests não disponível")
        return None
    
    if not AZURE_AI_SEARCH_ENDPOINT or not AZURE_AI_SEARCH_KEY:
        logger.error("❌ Azure AI Search não configurado")
        return None
    
    try:
        logger.info("=" * 60)
        logger.info(f"CRIANDO ÍNDICE: {index_name}")
        logger.info("=" * 60)
        
        # Carregar template
        create_index_template = load_index_template(template_path)
        if not create_index_template:
            logger.error("❌ Não foi possível carregar template")
            return None
        
        # Configurar template
        create_index_template["name"] = index_name
        if "semantic" in create_index_template and "configurations" in create_index_template["semantic"]:
            if len(create_index_template["semantic"]["configurations"]) > 0:
                create_index_template["semantic"]["configurations"][0]["name"] = semantic_name
        
        # Adicionar campos padrão
        create_index_template["fields"].extend([
            {
                "name": "content",
                "type": "Edm.String",
                "searchable": True,
                "retrievable": True,
                "analyzer": "pt-Br.lucene",
            },
            {
                "name": "contentVector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "retrievable": True,
                "dimensions": 1536,
                "vectorSearchProfile": "vector-profile-1700855443968",
            },
        ])
        
        # Adicionar colunas personalizadas
        for column in columns:
            if column not in create_index_template["fields"]:
                create_index_template["fields"].append(column)
        
        # Criar índice via API REST
        headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_AI_SEARCH_KEY,
        }
        
        url = f"{AZURE_AI_SEARCH_ENDPOINT}/indexes/{index_name}?api-version=2023-10-01-Preview&allowIndexDowntime=true"
        
        response = requests.put(url, headers=headers, json=create_index_template)
        
        if response.status_code in [200, 201]:
            logger.info(f"✅ Índice criado com sucesso: {index_name}")
            return create_index_template
        else:
            logger.error(f"❌ Erro ao criar índice: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Erro ao criar índice: {e}", exc_info=True)
        return None


def upload_to_index(index_name: str, documents: List[Dict[str, Any]]) -> bool:
    """Faz upload de documentos para o índice.
    
    Args:
        index_name: Nome do índice
        documents: Lista de documentos para indexar
        
    Returns:
        True se upload bem-sucedido, False caso contrário
    """
    if not REQUESTS_AVAILABLE:
        logger.error("❌ Biblioteca requests não disponível")
        return False
    
    if not AZURE_AI_SEARCH_ENDPOINT or not AZURE_AI_SEARCH_KEY:
        logger.error("❌ Azure AI Search não configurado")
        return False
    
    if not documents:
        logger.warning("⚠️ Nenhum documento para indexar")
        return False
    
    try:
        logger.info(f"📤 Indexando {len(documents)} documentos...")
        
        headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_AI_SEARCH_KEY,
        }
        
        template = {"value": documents}
        url = f"{AZURE_AI_SEARCH_ENDPOINT}/indexes/{index_name}/docs/index?api-version=2023-10-01-Preview"
        
        response = requests.post(url, headers=headers, json=template)
        
        if response.status_code in [200, 201]:
            logger.info(f"✅ {len(documents)} documentos indexados com sucesso")
            return True
        else:
            logger.error(f"❌ Erro ao indexar: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao fazer upload: {e}", exc_info=True)
        return False


def split_text(
    text: str,
    token_chunks: int,
    overlap_percentage: float = 0.1
) -> List[str]:
    """Divide texto em chunks com sobreposição.
    
    Args:
        text: Texto a ser dividido
        token_chunks: Tamanho de cada chunk em tokens
        overlap_percentage: Porcentagem de sobreposição (0.0-1.0)
        
    Returns:
        Lista de chunks de texto
    """
    overlap_size = round(token_chunks * overlap_percentage)
    text_length = len(text)
    res = []
    start = 0
    
    while start < text_length:
        end = start + token_chunks
        chunk = text[start:end]
        res.append(chunk)
        start += token_chunks - overlap_size
        
        if end >= text_length:
            break
    
    return res


def extract_and_split_docs_v2(
    files_path: str,
    index_name: str,
    token_chunks: int = 1024,
    overlap_percentage: float = 0.2
) -> List[Dict[str, Any]]:
    """Extrai textos de arquivos e os divide em chunks.
    
    Args:
        files_path: Caminho para arquivos ou diretório
        index_name: Nome do índice para criação
        token_chunks: Tamanho de cada chunk em tokens
        overlap_percentage: Porcentagem de sobreposição
        
    Returns:
        Lista de dicionários com chunks e metadados
    """
    logger.info("=" * 60)
    logger.info("EXTRAINDO E DIVIDINDO DOCUMENTOS")
    logger.info("=" * 60)
    
    chunks = []
    documentos_processados = 0
    
    # Verificar se é diretório ou arquivo
    if os.path.isdir(files_path):
        files = [os.path.join(files_path, f) for f in os.listdir(files_path) if os.path.isfile(os.path.join(files_path, f))]
    else:
        files = [files_path] if os.path.isfile(files_path) else []
    
    logger.info(f"📚 Processando {len(files)} arquivo(s)...")
    
    for file in files:
        try:
            if file.lower().endswith(".pdf") and PDF_AVAILABLE:
                logger.info(f"📄 Processando PDF: {os.path.basename(file)}")
                reader = PdfReader(file)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if not text or not text.strip():
                        continue
                    
                    texts = split_text(text, token_chunks, overlap_percentage)
                    for chunk in texts:
                        chunks.append({
                            "filepathField": os.path.basename(file),
                            "pagina": f"Pagina {i+1}",
                            "content": chunk,
                        })
                documentos_processados += 1
                logger.info(f"✅ PDF processado: {os.path.basename(file)} ({len(reader.pages)} páginas)")
                
            elif file.lower().endswith(".txt"):
                logger.info(f"📄 Processando TXT: {os.path.basename(file)}")
                with open(file, "r", encoding="utf-8") as f:
                    text = f.read()
                if not text.strip():
                    continue
                
                texts = split_text(text, token_chunks, overlap_percentage)
                for chunk in texts:
                    chunks.append({
                        "filepathField": os.path.basename(file),
                        "content": chunk
                    })
                documentos_processados += 1
                logger.info(f"✅ TXT processado: {os.path.basename(file)}")
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar {file}: {e}", exc_info=True)
    
    logger.info(f"✅ {documentos_processados} documento(s) processado(s), {len(chunks)} chunk(s) criado(s)")
    
    # Criar índice se necessário
    if chunks:
        columns = []
        seen_keys = set()
        for chunk in chunks:
            for key in chunk.keys():
                if key != "content" and key not in seen_keys:
                    columns.append({
                        "name": key,
                        "type": "Edm.String",
                        "searchable": True,
                        "retrievable": True,
                    })
                    seen_keys.add(key)
        
        if columns:
            logger.info(f"📋 Criando índice com colunas: {[c['name'] for c in columns]}")
            create_index_v2(
                f"{index_name}-index",
                f"semantic-{index_name}",
                columns
            )
    
    return chunks


def vectorize_and_upload_v2(
    chunks: List[Dict[str, Any]],
    index: str,
    batch_size: int = 10,
    delay_seconds: float = 0.6
) -> bool:
    """Vetoriza e envia documentos para o índice.
    
    Args:
        chunks: Lista de chunks a serem vetorizados
        index: Nome do índice (sem sufixo -index)
        batch_size: Tamanho do lote para upload
        delay_seconds: Delay entre batches em segundos
        
    Returns:
        True se upload bem-sucedido, False caso contrário
    """
    if not chunks:
        logger.warning("⚠️ Nenhum chunk para vetorizar")
        return False
    
    index_name = f"{index}-index"
    logger.info("=" * 60)
    logger.info(f"VETORIZANDO E INDEXANDO: {len(chunks)} chunks")
    logger.info("=" * 60)
    
    template = {"value": []}
    batch_count = 0
    total_indexed = 0
    
    # Usar tqdm se disponível
    iterator = tqdm(enumerate(chunks)) if TQDM_AVAILABLE else enumerate(chunks)
    
    try:
        for i, chunk in iterator:
            # Validar estrutura do chunk
            if isinstance(chunk, dict) and "content" in chunk:
                content = str(chunk["content"])
            elif isinstance(chunk, str):
                content = chunk
            else:
                logger.warning(f"⚠️ Chunk inválido na posição {i}, pulando...")
                continue
            
            # Criar embedding
            embedding = create_embedding(content)
            if not embedding:
                logger.warning(f"⚠️ Falha ao criar embedding para chunk {i}, pulando...")
                continue
            
            # Preparar documento
            document = {
                "id": str(i),
                "content": content,
                "contentVector": embedding,
            }
            
            # Adicionar metadados se disponíveis
            if isinstance(chunk, dict):
                for key, value in chunk.items():
                    if key != "content":
                        document[key] = str(value)
            
            template["value"].append(document)
            batch_count += 1
            
            # Upload em batches
            if batch_count >= batch_size:
                if upload_to_index(index_name, template["value"]):
                    total_indexed += len(template["value"])
                batch_count = 0
                template["value"] = []
                time.sleep(delay_seconds)
        
        # Upload do último batch
        if template["value"]:
            if upload_to_index(index_name, template["value"]):
                total_indexed += len(template["value"])
        
        logger.info(f"✅ {total_indexed} documento(s) indexado(s) com sucesso")
        return total_indexed > 0
        
    except Exception as e:
        logger.error(f"❌ Erro ao vetorizar e indexar: {e}", exc_info=True)
        return False


def index_documents_from_directory(
    directory_path: str,
    index_name: str,
    token_chunks: int = 1024,
    overlap_percentage: float = 0.2,
    batch_size: int = 10,
    delay_seconds: float = 0.6
) -> bool:
    """Indexa todos os documentos de um diretório.
    
    Args:
        directory_path: Caminho do diretório com documentos
        index_name: Nome do índice
        token_chunks: Tamanho de cada chunk em tokens
        overlap_percentage: Porcentagem de sobreposição
        batch_size: Tamanho do lote para upload
        delay_seconds: Delay entre batches
        
    Returns:
        True se indexação bem-sucedida, False caso contrário
    """
    logger.info("=" * 60)
    logger.info(f"INDEXAÇÃO EM MASSA: {directory_path}")
    logger.info("=" * 60)
    
    # Extrair e dividir documentos
    chunks = extract_and_split_docs_v2(
        directory_path,
        index_name,
        token_chunks=token_chunks,
        overlap_percentage=overlap_percentage
    )
    
    if not chunks:
        logger.warning("⚠️ Nenhum chunk gerado")
        return False
    
    # Vetorizar e indexar
    return vectorize_and_upload_v2(
        chunks,
        index_name,
        batch_size=batch_size,
        delay_seconds=delay_seconds
    )

