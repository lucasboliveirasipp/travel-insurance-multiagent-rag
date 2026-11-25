"""Constantes de configuração do pipeline.

Define valores constantes usados em todo o pipeline para evitar
números mágicos e facilitar manutenção.
"""

# ============================================================================
# LIMITES DE ITERAÇÃO E RECURSÃO
# ============================================================================

# Limite máximo de iterações do grafo antes de forçar finalização
MAX_GRAPH_ITERATIONS = 20

# Limite de recursão do LangGraph
# Fluxo típico: Supervisor(1) -> Librarian(1) -> Classifier(1) -> Analyst(0-1) -> Writer(1) -> Supervisor(1-3 validações)
# Mínimo: ~5-6 iterações | Máximo: ~10-12 iterações (com revisões)
# Definido como 100 para dar margem de segurança
LANGGRAPH_RECURSION_LIMIT = 100

# ============================================================================
# LIMITES DE TENTATIVAS POR NÓ
# ============================================================================

# Número máximo de tentativas de validação pelo supervisor
MAX_VALIDATION_ATTEMPTS = 3

# Número máximo de erros consecutivos no writer antes de finalizar
MAX_WRITER_ERRORS = 3

# ============================================================================
# LIMITES DE CONTEÚDO
# ============================================================================

# Tamanho máximo de conteúdo para prompts (em caracteres)
MAX_PROMPT_CONTENT_LENGTH = 2000

# Número máximo de fontes a incluir na resposta
MAX_SOURCES_IN_DOSSIER = 5

# ============================================================================
# SCORES E THRESHOLDS
# ============================================================================

# Confiança mínima de intenção para processar sem fallback
MIN_INTENT_CONFIDENCE = 0.5

# ============================================================================
# TIMEOUTS E PERFORMANCE
# ============================================================================

# Timeout para chamadas ao LLM (segundos)
LLM_TIMEOUT_SECONDS = 60

# Número máximo de retries para chamadas ao LLM
LLM_MAX_RETRIES = 2

# Temperatura padrão para geração de texto
LLM_TEMPERATURE = 0

