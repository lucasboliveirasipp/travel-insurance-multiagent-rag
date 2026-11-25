"""Configurações centralizadas do Agente de Viagem.

Inclui configuração de proxy corporativo, Azure OpenAI, Form Recognizer,
Computer Vision e AI Search com fallbacks automáticos.
"""

# Carrega variáveis do arquivo .env mais próximo (pasta do projeto)
def _carregar_env():
    from pathlib import Path
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for pasta in Path(__file__).resolve().parents:
        if (pasta / ".env").exists():
            load_dotenv(pasta / ".env")
            break


_carregar_env()


import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURAÇÃO DE PROXY CORPORATIVO
# ============================================================================

proxy_host = os.getenv("HTTP_PROXY_HOST", "")
proxy_port = os.getenv("HTTP_PROXY_PORT", "80")
if proxy_host:  # proxy opcional (defina HTTP_PROXY_HOST no .env)
    os.environ['HTTP_PROXY'] = f'http://{proxy_host}:{proxy_port}'
if proxy_host:  # proxy opcional (defina HTTP_PROXY_HOST no .env)
    os.environ['HTTPS_PROXY'] = f'http://{proxy_host}:{proxy_port}'

if proxy_host:  # proxy opcional (defina HTTP_PROXY_HOST no .env)
    logger.info(f"✅ Proxy configurado: {proxy_host}:{proxy_port}")

# ============================================================================
# AZURE OPENAI - LLM Principal
# ============================================================================

# Azure OpenAI - valores hardcoded como padrão, podem ser sobrescritos via variáveis de ambiente
AZURE_OPENAI_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT",
    ""
)
AZURE_OPENAI_KEY = os.getenv(
    "AZURE_OPENAI_KEY",
    ""
)
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

llm = None
try:
    from langchain_openai import AzureChatOpenAI
    
    llm = AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        openai_api_key=AZURE_OPENAI_KEY,
        deployment_name=AZURE_OPENAI_DEPLOYMENT,
        api_version=AZURE_OPENAI_API_VERSION,
        temperature=0,
        max_retries=2,
        timeout=60
    )
    logger.info(f"✅ Azure OpenAI configurado: {AZURE_OPENAI_DEPLOYMENT}")
except Exception as e:
    logger.error(f"❌ Erro ao inicializar Azure OpenAI: {e}", exc_info=True)
    # Fallback para instância alternativa se necessário
    try:
        AZURE_OPENAI_ENDPOINT_FALLBACK = os.getenv("AZURE_OPENAI_ENDPOINT_FALLBACK", "")
        AZURE_OPENAI_KEY_FALLBACK = os.getenv("AZURE_OPENAI_KEY_FALLBACK", "")
        if AZURE_OPENAI_ENDPOINT_FALLBACK and AZURE_OPENAI_KEY_FALLBACK:
            llm = AzureChatOpenAI(
                azure_endpoint=AZURE_OPENAI_ENDPOINT_FALLBACK,
                openai_api_key=AZURE_OPENAI_KEY_FALLBACK,
                deployment_name=AZURE_OPENAI_DEPLOYMENT,
                api_version=AZURE_OPENAI_API_VERSION,
                temperature=0,
                max_retries=2,
                timeout=60
            )
            logger.info("✅ Azure OpenAI fallback configurado")
    except Exception as e2:
        logger.error(f"❌ Erro ao inicializar fallback: {e2}", exc_info=True)

# ============================================================================
# AZURE FORM RECOGNIZER - Extração de PDFs
# ============================================================================

AZURE_FORM_RECOGNIZER_ENDPOINT = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT", "")
AZURE_FORM_RECOGNIZER_KEY = os.getenv("AZURE_FORM_RECOGNIZER_KEY", "")

# Inicializar como None por padrão
form_recognizer_client = None
form_recognizer_available = False

try:
    if AZURE_FORM_RECOGNIZER_ENDPOINT and AZURE_FORM_RECOGNIZER_KEY:
        from azure.ai.formrecognizer import DocumentAnalysisClient
        
        form_recognizer_client = DocumentAnalysisClient(
            endpoint=AZURE_FORM_RECOGNIZER_ENDPOINT,
            credential=AZURE_FORM_RECOGNIZER_KEY
        )
        form_recognizer_available = True
        logger.info("✅ Azure Form Recognizer configurado")
    else:
        logger.debug("Azure Form Recognizer não configurado (variáveis de ambiente ausentes)")
except Exception as e:
    logger.warning(f"⚠️ Azure Form Recognizer não disponível: {e}")
    form_recognizer_client = None

# ============================================================================
# AZURE COMPUTER VISION - OCR para Imagens
# ============================================================================

AZURE_COMPUTER_VISION_ENDPOINT = os.getenv("AZURE_COMPUTER_VISION_ENDPOINT", "")
AZURE_COMPUTER_VISION_KEY = os.getenv("AZURE_COMPUTER_VISION_KEY", "")

# Inicializar como None por padrão
computer_vision_client = None
computer_vision_available = False

try:
    if AZURE_COMPUTER_VISION_ENDPOINT and AZURE_COMPUTER_VISION_KEY:
        from azure.cognitiveservices.vision.computervision import ComputerVisionClient
        from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
        from msrest.authentication import CognitiveServicesCredentials
        
        computer_vision_client = ComputerVisionClient(
            AZURE_COMPUTER_VISION_ENDPOINT,
            CognitiveServicesCredentials(AZURE_COMPUTER_VISION_KEY)
        )
        computer_vision_available = True
        logger.info("✅ Azure Computer Vision configurado")
    else:
        logger.debug("Azure Computer Vision não configurado (variáveis de ambiente ausentes)")
except Exception as e:
    logger.warning(f"⚠️ Azure Computer Vision não disponível: {e}")
    computer_vision_client = None

# ============================================================================
# AZURE AI SEARCH - Busca Vetorial
# ============================================================================

# Azure AI Search - valores hardcoded
AZURE_AI_SEARCH_ENDPOINT = os.getenv("AZURE_AI_SEARCH_ENDPOINT", "")
AZURE_AI_SEARCH_KEY = os.getenv("AZURE_AI_SEARCH_KEY", "")
AZURE_AI_SEARCH_INDEX_NAME = "book-parcerias-index"

# Azure Embeddings - TEMPORARIO ate 04/02/2026
# Apos 04/02/2026, restaurar para:
#   AZURE_EMBEDDINGS_DEPLOYMENT = "text-embedding-ada-002"
AZURE_EMBEDDINGS_ENDPOINT = os.getenv("AZURE_EMBEDDINGS_ENDPOINT", "")
AZURE_EMBEDDINGS_KEY = os.getenv("AZURE_EMBEDDINGS_KEY", "")
AZURE_EMBEDDINGS_DEPLOYMENT = "text-embedding-ada-002"
AZURE_EMBEDDINGS_API_VERSION = "2023-05-15"

# Inicializar como None por padrão
search_client = None
ai_search_available = False

try:
    if AZURE_AI_SEARCH_ENDPOINT and AZURE_AI_SEARCH_KEY:
        from azure.search.documents import SearchClient
        from azure.core.credentials import AzureKeyCredential
        
        search_client = SearchClient(
            endpoint=AZURE_AI_SEARCH_ENDPOINT,
            index_name=AZURE_AI_SEARCH_INDEX_NAME,
            credential=AzureKeyCredential(AZURE_AI_SEARCH_KEY)
        )
        ai_search_available = True
        logger.info(f"✅ Azure AI Search configurado: {AZURE_AI_SEARCH_INDEX_NAME}")
    else:
        logger.warning("⚠️ Azure AI Search não configurado (variáveis de ambiente ausentes)")
except Exception as e:
    logger.warning(f"⚠️ Azure AI Search não disponível: {e}")
    search_client = None

# ============================================================================
# CONFIGURAÇÕES GERAIS
# ============================================================================

# Diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = os.path.join(BASE_DIR, "files")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Criar diretórios se não existirem
os.makedirs(FILES_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configurações de cache
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hora

# Configurações de processamento
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
MAX_CONCURRENT_FILES = int(os.getenv("MAX_CONCURRENT_FILES", "4"))

logger.info("=" * 60)
logger.info("CONFIGURAÇÃO INICIALIZADA")
logger.info("=" * 60)

