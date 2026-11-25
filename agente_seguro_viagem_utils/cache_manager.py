"""Gerenciador de cache para operações custosas.

Utiliza diskcache para cachear resultados de extração de PDFs e outras
operações que não precisam ser repetidas.
"""

import os
import hashlib
import logging
from typing import Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Importação lazy para dependência opcional
CACHE_AVAILABLE = False
try:
    import diskcache as dc
    CACHE_AVAILABLE = True
except ImportError:
    logger.debug("diskcache não disponível, cache desabilitado")

# Configuração
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", ".cache")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hora padrão

# TTLs específicos por tipo de operação
CACHE_TTL_EXTRACTION = int(os.getenv("CACHE_TTL_EXTRACTION", "7200"))  # 2 horas para extrações
CACHE_TTL_SEARCH = int(os.getenv("CACHE_TTL_SEARCH", "1800"))  # 30 minutos para buscas
CACHE_TTL_EMBEDDINGS = int(os.getenv("CACHE_TTL_EMBEDDINGS", "86400"))  # 24 horas para embeddings

cache = None
if CACHE_AVAILABLE:
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache = dc.Cache(CACHE_DIR)
        logger.info(f"✅ Cache inicializado: {CACHE_DIR}")
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar cache: {e}", exc_info=True)
        cache = None


def get_file_hash(file_data: bytes) -> str:
    """Gera hash SHA256 de dados de arquivo.
    
    Args:
        file_data: Bytes do arquivo
        
    Returns:
        Hash hexadecimal do arquivo
    """
    return hashlib.sha256(file_data).hexdigest()


def get_cache_key(operation: str, *args, **kwargs) -> str:
    """Gera chave de cache baseada em operação e argumentos.
    
    Args:
        operation: Nome da operação
        *args: Argumentos posicionais
        **kwargs: Argumentos nomeados
        
    Returns:
        Chave de cache única
    """
    key_parts = [operation]
    
    # Adicionar argumentos posicionais
    for arg in args:
        if isinstance(arg, bytes):
            key_parts.append(get_file_hash(arg))
        else:
            key_parts.append(str(arg))
    
    # Adicionar argumentos nomeados (ordenados)
    for k, v in sorted(kwargs.items()):
        if isinstance(v, bytes):
            key_parts.append(f"{k}:{get_file_hash(v)}")
        else:
            key_parts.append(f"{k}:{str(v)}")
    
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def get_cache_manager() -> Optional[Any]:
    """Retorna instância do gerenciador de cache.
    
    Returns:
        Instância do cache ou None se não disponível
    """
    return cache


def cache_get(key: str) -> Optional[Any]:
    """Recupera valor do cache.
    
    Args:
        key: Chave do cache
        
    Returns:
        Valor em cache ou None se não encontrado
    """
    if not cache:
        return None
    
    try:
        value = cache.get(key)
        if value is not None:
            logger.debug(f"✅ Cache hit: {key[:20]}...")
        return value
    except Exception as e:
        logger.warning(f"⚠️ Erro ao recuperar cache: {e}")
        return None


def cache_set(key: str, value: Any, ttl: Optional[int] = None, cache_type: Optional[str] = None) -> bool:
    """Armazena valor no cache.
    
    Args:
        key: Chave do cache
        value: Valor a armazenar
        ttl: Time to live em segundos (None = usar padrão ou tipo)
        cache_type: Tipo de cache ("extraction", "search", "embeddings") para TTL específico
        
    Returns:
        True se armazenado com sucesso, False caso contrário
    """
    if not cache:
        return False
    
    try:
        # Determinar TTL baseado no tipo se não especificado
        if ttl is None and cache_type:
            ttl_map = {
                "extraction": CACHE_TTL_EXTRACTION,
                "search": CACHE_TTL_SEARCH,
                "embeddings": CACHE_TTL_EMBEDDINGS
            }
            ttl = ttl_map.get(cache_type, CACHE_TTL)
        elif ttl is None:
            ttl = CACHE_TTL
        
        cache.set(key, value, expire=ttl)
        logger.debug(f"✅ Cache set: {key[:20]}... (TTL: {ttl}s)")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Erro ao armazenar cache: {e}")
        return False


def cache_clear() -> bool:
    """Limpa todo o cache.
    
    Returns:
        True se limpeza bem-sucedida
    """
    if not cache:
        return False
    
    try:
        cache.clear()
        logger.info("✅ Cache limpo")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao limpar cache: {e}", exc_info=True)
        return False

