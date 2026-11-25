"""Construtor do pipeline LangGraph para o Agente de Viagem."""

import os
import sys
import logging
from pathlib import Path

# Configurar path para imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agent_state import AgentState
from config_constants_viagem import MAX_GRAPH_ITERATIONS, MAX_VALIDATION_ATTEMPTS
from agente_seguro_viagem_nodes.supervisor_node import supervisor_node
from agente_seguro_viagem_nodes.librarian_node import librarian_node
from agente_seguro_viagem_nodes.classifier_node import classifier_node
from agente_seguro_viagem_nodes.analyst_node import analyst_node
from agente_seguro_viagem_nodes.writer_node import writer_node

logger = logging.getLogger(__name__)


def route_after_supervisor(state: AgentState) -> str:
    """Roteia após execução do supervisor (simplificado para chatbot).
    
    Args:
        state: Estado atual
        
    Returns:
        Nome do próximo nó ou END para finalizar
    """
    # Verificar limite de iterações para prevenir loops infinitos
    iteration_count = state.get("iteration_count", 0)
    
    if iteration_count >= MAX_GRAPH_ITERATIONS:
        logger.warning(f"⚠️ Limite de iterações atingido ({MAX_GRAPH_ITERATIONS}), finalizando")
        return END
    
    # Se já validou e aprovou, finalizar
    if state.get("validation_status") == "approved":
        logger.info("✅ Validação aprovada, finalizando pipeline")
        return END
    
    # Se já tem resposta gerada e validada, finalizar
    if state.get("response") and state.get("validation_status") == "approved":
        logger.info("✅ Resposta gerada e validada, finalizando")
        return END
    
    # Determinar próximo nó baseado no estado
    next_node = state.get("next")
    
    # Se next_node é None, significa que deve finalizar
    if next_node is None:
        logger.info("✅ Próximo nó é None, finalizando pipeline")
        return END
    
    # Se não há next_node definido, usar padrão
    if not next_node:
        next_node = "librarian"
    
    # Se não há documentos extraídos, ir para bibliotecário
    if not state.get("extracted_documents"):
        return "librarian"
    
    # Se não há informações classificadas, ir para classificador
    if not state.get("classified_info"):
        return "classifier"
    
    # Se requer análise e não foi feita, ir para analista
    if state.get("requires_analysis") and not state.get("analysis_result"):
        return "analyst"
    
    # Se não há resposta, ir para redator
    if not state.get("response"):
        return "writer"
    
    # Se já tem resposta mas não foi validado ainda, voltar ao supervisor para validação básica
    if state.get("response") and not state.get("validation_status"):
        return "supervisor"
    
    # Fallback: usar o próximo nó definido pelo supervisor
    valid_nodes = ["librarian", "classifier", "analyst", "writer", "supervisor"]
    if next_node and next_node in valid_nodes:
        return next_node
    else:
        logger.warning(f"⚠️ Próximo nó inválido: {next_node}, finalizando")
        return END


def route_after_librarian(state: AgentState) -> str:
    """Roteia após execução do bibliotecário.
    
    Args:
        state: Estado atual
        
    Returns:
        Nome do próximo nó
    """
    return "classifier"


def route_after_classifier(state: AgentState) -> str:
    """Roteia após execução do classificador.
    
    Args:
        state: Estado atual
        
    Returns:
        Nome do próximo nó
    """
    requires_analysis = state.get("requires_analysis", False)
    
    if requires_analysis:
        return "analyst"
    else:
        return "writer"


def route_after_analyst(state: AgentState) -> str:
    """Roteia após execução do analista.
    
    Args:
        state: Estado atual
        
    Returns:
        Nome do próximo nó
    """
    return "writer"


def route_after_writer(state: AgentState) -> str:
    """Roteia após execução do redator.
    
    Args:
        state: Estado atual
        
    Returns:
        Nome do próximo nó
    """
    return "supervisor"  # Voltar para validação básica


def build_graph() -> StateGraph:
    """Constrói o grafo de execução do pipeline.
    
    Returns:
        Grafo compilado do LangGraph
    """
    logger.info("=" * 60)
    logger.info("CONSTRUINDO PIPELINE LANGRAPH")
    logger.info("=" * 60)
    
    # Criar grafo
    workflow = StateGraph(AgentState)
    
    # Adicionar nós
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("librarian", librarian_node)
    workflow.add_node("classifier", classifier_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("writer", writer_node)
    
    # Definir ponto de entrada
    workflow.set_entry_point("supervisor")
    
    # Adicionar arestas condicionais
    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "librarian": "librarian",
            "classifier": "classifier",
            "analyst": "analyst",
            "writer": "writer",
            END: END
        }
    )
    
    # Adicionar aresta de retorno do redator para supervisor (validação)
    # Isso já está implementado, mas garantimos que está correto
    
    workflow.add_edge("librarian", "classifier")
    
    workflow.add_conditional_edges(
        "classifier",
        route_after_classifier,
        {
            "analyst": "analyst",
            "writer": "writer"
        }
    )
    
    workflow.add_edge("analyst", "writer")
    workflow.add_edge("writer", "supervisor")
    
    # Compilar com checkpointing e limite de recursão
    memory = MemorySaver()
    compiled_graph = workflow.compile(
        checkpointer=memory,
        interrupt_before=[],  # Não interromper antes de nenhum nó
        interrupt_after=[],  # Não interromper após nenhum nó
    )
    
    # O limite de recursão é configurado na invocação do grafo, não na compilação
    # Valor padrão do LangGraph é 25, mas configuramos 100 na execução
    logger.info("✅ Pipeline construído com sucesso")
    logger.info("📊 Limite de recursão será configurado na execução (padrão: 100)")
    return compiled_graph


if __name__ == "__main__":
    # Teste básico
    logging.basicConfig(level=logging.INFO)
    graph = build_graph()
    print("✅ Grafo construído com sucesso")

