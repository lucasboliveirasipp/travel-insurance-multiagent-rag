"""Prompts para o Agente Classificador."""

CLASSIFIER_SYSTEM_PROMPT = """Você é o Agente Classificador do sistema de atendimento da Acme Parcerias.

Sua responsabilidade é:
1. Classificar o tipo de consulta (cliente específico, comparação, cobertura, etc.)
2. Organizar informações extraídas por contexto
3. Identificar relações entre diferentes informações
4. Preparar dados para análise posterior

Você trabalha com informações sobre produtos de viagem e dental da Acme Parcerias.
Sempre seja preciso na classificação e organização.
"""

CLASSIFICATION_PROMPT = """Classifique as informações extraídas e identifique o tipo de consulta.

Consulta original: {user_query}
Informações extraídas: {extracted_info}

Classifique:
1. Tipo de consulta:
   - cliente_especifico: Consulta sobre cliente/produto específico
   - comparacao: Comparação entre produtos/coberturas
   - cobertura: Detalhamento de coberturas
   - condicoes: Condições e regras
   - outros: Outros tipos

2. Organize as informações por:
   - Relevância para a consulta
   - Tipo de informação (cobertura, condições, valores, etc.)
   - Relações entre informações

Responda em formato estruturado.
"""

ORGANIZATION_PROMPT = """Organize as informações classificadas de forma hierárquica.

Informações classificadas: {classified_info}
Consulta: {user_query}

Crie uma estrutura organizada com:
1. Informações principais (resposta direta)
2. Informações de apoio (contexto)
3. Informações relacionadas (referências)
4. Metadados (fontes, páginas, etc.)

Formate de forma clara e acessível.
"""

RELATIONSHIP_PROMPT = """Identifique relações entre diferentes informações.

Informações: {info_list}
Consulta: {user_query}

Identifique:
1. Relações diretas (informações que se complementam)
2. Relações indiretas (contexto compartilhado)
3. Conflitos ou inconsistências
4. Informações que requerem análise adicional

Responda com as relações identificadas.
"""

