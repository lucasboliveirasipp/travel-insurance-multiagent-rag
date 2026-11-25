"""Estado compartilhado do pipeline LangGraph.

Define o TypedDict que será usado para comunicação entre os nós do pipeline.
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """Estado compartilhado entre os nós do pipeline de chatbot conversacional.
    
    Campos:
        messages: Histórico de mensagens da conversa
        user_query: Consulta original do usuário
        query_intent: Intenção identificada pelo supervisor
        extracted_documents: Documentos extraídos dos PDFs
        classified_info: Informações classificadas pelo classificador
        analysis_result: Resultado da análise complexa (se aplicável)
        response: Resposta conversacional ao usuário
        conversation_context: Contexto da conversa para manter histórico
        validation_status: Status da validação básica do supervisor
        next: Próximo nó a executar
        error: Mensagem de erro (se houver)
        metadata: Metadados adicionais do processamento
    """
    
    # Histórico de mensagens
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Consulta do usuário
    user_query: str
    
    # Intenção e roteamento
    query_intent: Optional[str]  # "simple_query", "comparison", "complex_analysis", etc.
    requires_analysis: bool  # Se requer análise do agente analista
    
    # Dados extraídos
    extracted_documents: Dict[str, Any]  # Documentos extraídos dos PDFs
    relevant_chunks: List[Dict[str, Any]]  # Chunks relevantes da busca vetorial
    
    # Classificação
    classified_info: Dict[str, Any]  # Informações classificadas
    query_type: Optional[str]  # Tipo de consulta identificado
    
    # Análise
    analysis_result: Optional[Dict[str, Any]]  # Resultado da análise complexa
    
    # Resposta final
    response: Optional[str]  # Resposta conversacional direta ao usuário
    
    # Contexto de conversa
    conversation_context: Optional[str]  # Contexto da conversa para manter histórico
    
    # Validação básica
    validation_status: Optional[str]  # "approved", "rejected" (simplificado)
    
    # Controle de fluxo
    next: Optional[str]  # Próximo nó a executar
    
    # Tratamento de erros
    error: Optional[str]  # Mensagem de erro
    
    # Metadados gerais
    metadata: Dict[str, Any]  # Metadados adicionais
    
    # Controle de iterações (para prevenir loops infinitos)
    iteration_count: int  # Contador de iterações do grafo

