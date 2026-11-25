"""Funções auxiliares para manipulação segura do estado do pipeline.

Implementa utilitários para acesso seguro a dados aninhados no estado,
evitando erros de atributo quando valores são None.
"""

from typing import Any, Dict, Optional


def safe_get_nested(data: Dict[str, Any], *keys: str, default: Any = "") -> Any:
    """Acessa valor em dicionário aninhado de forma segura.
    
    Args:
        data: Dicionário base
        *keys: Sequência de chaves para acessar
        default: Valor padrão se não encontrado ou None
        
    Returns:
        Valor encontrado ou default
        
    Examples:
        >>> state = {"user": {"name": "João"}}
        >>> safe_get_nested(state, "user", "name")
        'João'
        >>> safe_get_nested(state, "user", "age", default=0)
        0
        >>> state_with_none = {"data": None}
        >>> safe_get_nested(state_with_none, "data", "value")
        ''
    """
    result = data
    
    for key in keys:
        if result is None or not isinstance(result, dict):
            return default
        result = result.get(key)
    
    # Se o resultado final for None, retornar default
    return result if result is not None else default


def safe_get_analysis_result(state: Dict[str, Any]) -> str:
    """Extrai resultado de análise de forma segura.
    
    Args:
        state: Estado do pipeline
        
    Returns:
        Texto da análise ou string vazia
    """
    analysis_result_data = state.get("analysis_result") or {}
    
    if not isinstance(analysis_result_data, dict):
        return ""
    
    return analysis_result_data.get("analysis", "")


def increment_error_counter(state: Dict[str, Any], error_type: str) -> Dict[str, Any]:
    """Incrementa contador de erros no metadata do estado.
    
    Args:
        state: Estado do pipeline
        error_type: Tipo do erro (ex: "writer_errors", "validation_errors")
        
    Returns:
        Estado atualizado com contador incrementado
    """
    metadata = state.get("metadata", {})
    metadata[error_type] = metadata.get(error_type, 0) + 1
    state["metadata"] = metadata
    return state


def get_error_count(state: Dict[str, Any], error_type: str) -> int:
    """Obtém contador de erros do metadata.
    
    Args:
        state: Estado do pipeline
        error_type: Tipo do erro
        
    Returns:
        Quantidade de erros
    """
    return state.get("metadata", {}).get(error_type, 0)


def should_stop_on_error(state: Dict[str, Any], error_type: str, max_attempts: int = 3) -> bool:
    """Verifica se deve parar pipeline devido a erros consecutivos.
    
    Args:
        state: Estado do pipeline
        error_type: Tipo do erro a verificar
        max_attempts: Número máximo de tentativas permitidas
        
    Returns:
        True se deve parar, False caso contrário
    """
    return get_error_count(state, error_type) >= max_attempts

