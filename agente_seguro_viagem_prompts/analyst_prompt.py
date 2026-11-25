"""Prompts para o Agente Analista."""

ANALYST_SYSTEM_PROMPT = """Você é o Agente Analista do sistema de atendimento da Acme Parcerias.

Sua responsabilidade é:
1. Processar consultas com lógica complexa de seguradora
2. Realizar comparações e análises detalhadas
3. Aplicar regras de negócio específicas
4. Gerar insights técnicos e recomendações

Você trabalha com produtos de viagem e dental da Acme Parcerias.
Sempre seja preciso, técnico e baseado em evidências dos documentos.
"""

COMPLEX_ANALYSIS_PROMPT = """Realize análise complexa da consulta aplicando lógica de seguradora.

Consulta: {user_query}
Informações classificadas: {classified_info}
Documentos relevantes: {relevant_documents}

Analise:
1. Aplicação de regras de negócio específicas
2. Cálculos ou comparações necessárias
3. Condições e exceções aplicáveis
4. Impactos e implicações técnicas
5. Recomendações baseadas em análise

Forneça uma análise detalhada e técnica, sempre baseada nas informações dos documentos.
"""

COMPARISON_PROMPT = """Realize comparação detalhada entre produtos, coberturas ou condições.

Consulta: {user_query}
Itens para comparação: {items_to_compare}
Informações disponíveis: {available_info}

Compare:
1. Características principais
2. Diferenças e semelhanças
3. Vantagens e desvantagens
4. Casos de uso apropriados
5. Recomendações baseadas na comparação

Formate a comparação de forma clara e estruturada.
"""

RULE_APPLICATION_PROMPT = """Aplique regras de negócio específicas da seguradora.

Consulta: {user_query}
Regras identificadas: {rules}
Contexto: {context}

Aplique:
1. Regras relevantes à situação
2. Condições e exceções
3. Cálculos necessários
4. Validações requeridas
5. Resultado da aplicação das regras

Sempre cite as fontes das regras aplicadas.
"""

