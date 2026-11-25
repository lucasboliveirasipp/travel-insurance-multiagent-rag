"""Sistema de métricas e logging estruturado para o pipeline."""

import os
import sys
import time
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from functools import wraps

# Configurar path para imports
current_dir = Path(__file__).parent
if str(current_dir.parent) not in sys.path:
    sys.path.insert(0, str(current_dir.parent))

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Coletor de métricas de execução."""
    
    def __init__(self):
        self.metrics = {
            "executions": [],
            "agent_stats": {},
            "total_executions": 0,
            "total_errors": 0,
            "iteration_stats": {
                "total_runs": 0,
                "iterations_sum": 0,
                "min_iterations": float("inf"),
                "max_iterations": 0,
                "avg_iterations": 0.0
            }
        }
    
    def record_execution(
        self,
        agent_name: str,
        duration: float,
        success: bool,
        tokens_used: Optional[int] = None,
        error: Optional[str] = None
    ):
        """Registra execução de um agente.
        
        Args:
            agent_name: Nome do agente
            duration: Duração em segundos
            success: Se executou com sucesso
            tokens_used: Número de tokens usados (se aplicável)
            error: Mensagem de erro (se houver)
        """
        execution = {
            "agent": agent_name,
            "timestamp": datetime.now().isoformat(),
            "duration": duration,
            "success": success,
            "tokens_used": tokens_used,
            "error": error
        }
        
        self.metrics["executions"].append(execution)
        self.metrics["total_executions"] += 1
        
        if not success:
            self.metrics["total_errors"] += 1
        
        # Atualizar estatísticas do agente
        if agent_name not in self.metrics["agent_stats"]:
            self.metrics["agent_stats"][agent_name] = {
                "total": 0,
                "success": 0,
                "errors": 0,
                "total_duration": 0.0,
                "total_tokens": 0
            }
        
        stats = self.metrics["agent_stats"][agent_name]
        stats["total"] += 1
        if success:
            stats["success"] += 1
        else:
            stats["errors"] += 1
        stats["total_duration"] += duration
        if tokens_used:
            stats["total_tokens"] += tokens_used
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas coletadas.
        
        Returns:
            Dicionário com estatísticas
        """
        return self.metrics
    
    def get_agent_stats(self, agent_name: str) -> Dict[str, Any]:
        """Retorna estatísticas de um agente específico.
        
        Args:
            agent_name: Nome do agente
            
        Returns:
            Dicionário com estatísticas do agente
        """
        return self.metrics["agent_stats"].get(agent_name, {})
    
    def record_iterations(self, iteration_count: int):
        """Registra número de iterações de uma execução do pipeline.
        
        Args:
            iteration_count: Número de iterações usadas
        """
        stats = self.metrics["iteration_stats"]
        stats["total_runs"] += 1
        stats["iterations_sum"] += iteration_count
        stats["min_iterations"] = min(stats["min_iterations"], iteration_count)
        stats["max_iterations"] = max(stats["max_iterations"], iteration_count)
        stats["avg_iterations"] = stats["iterations_sum"] / stats["total_runs"]
        
        logger.info(f"📊 Estatísticas de iterações: média={stats['avg_iterations']:.1f}, min={stats['min_iterations']}, max={stats['max_iterations']}")
    
    def reset(self):
        """Reseta todas as métricas."""
        self.metrics = {
            "executions": [],
            "agent_stats": {},
            "total_executions": 0,
            "total_errors": 0,
            "iteration_stats": {
                "total_runs": 0,
                "iterations_sum": 0,
                "min_iterations": float("inf"),
                "max_iterations": 0,
                "avg_iterations": 0.0
            }
        }


# Instância global do coletor
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Retorna instância do coletor de métricas.
    
    Returns:
        Instância do MetricsCollector
    """
    return _metrics_collector


def track_execution(agent_name: str):
    """Decorator para rastrear execução de funções.
    
    Args:
        agent_name: Nome do agente
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            tokens_used = None
            
            try:
                result = func(*args, **kwargs)
                
                # Tentar extrair tokens do resultado se for AgentState
                if isinstance(result, dict) and "metadata" in result:
                    metadata = result.get("metadata", {})
                    tokens_used = metadata.get("tokens_used")
                
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                duration = time.time() - start_time
                _metrics_collector.record_execution(
                    agent_name=agent_name,
                    duration=duration,
                    success=success,
                    tokens_used=tokens_used,
                    error=error
                )
                
                # Log estruturado
                log_data = {
                    "agent": agent_name,
                    "duration": f"{duration:.2f}s",
                    "success": success,
                    "tokens": tokens_used
                }
                if error:
                    log_data["error"] = error
                
                logger.info(f"📊 Métricas: {json.dumps(log_data)}")
        
        return wrapper
    return decorator


def log_structured(level: str, message: str, **kwargs):
    """Log estruturado com dados adicionais.
    
    Args:
        level: Nível do log (info, warning, error)
        message: Mensagem do log
        **kwargs: Dados adicionais para incluir no log
    """
    log_data = {
        "message": message,
        "timestamp": datetime.now().isoformat(),
        **kwargs
    }
    
    log_message = f"📊 {json.dumps(log_data)}"
    
    if level == "info":
        logger.info(log_message)
    elif level == "warning":
        logger.warning(log_message)
    elif level == "error":
        logger.error(log_message)
    else:
        logger.debug(log_message)

