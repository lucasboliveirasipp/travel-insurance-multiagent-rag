"""Prompts para o Agente Bibliotecário."""

LIBRARIAN_SYSTEM_PROMPT = """Você é o Agente Bibliotecário do sistema de atendimento da Acme Parcerias.

Sua responsabilidade é:
1. Gerenciar e organizar a base de conhecimento (PDFs do Book Acme Parcerias)
2. Extrair informações relevantes dos documentos
3. Indexar documentos para busca eficiente
4. Manter a base de conhecimento atualizada

Você trabalha com documentos sobre produtos de viagem e dental da Acme Parcerias.
Sempre priorize precisão e organização das informações.
"""

EXTRACTION_PROMPT = """Extraia informações relevantes do documento para responder à consulta.

Consulta: {user_query}
Documento extraído: {extracted_text}

Identifique e extraia:
1. Informações diretamente relacionadas à consulta
2. Contexto relevante
3. Detalhes técnicos importantes
4. Referências a produtos, coberturas ou condições

Formate a resposta de forma estruturada e clara.
"""

SEARCH_PROMPT = """Com base na consulta, identifique quais documentos ou seções são mais relevantes.

Consulta: {user_query}
Documentos disponíveis: {available_documents}

Identifique:
1. Documentos mais relevantes
2. Seções específicas que devem ser consultadas
3. Palavras-chave para busca

Responda com uma lista de documentos e seções prioritárias.
"""

ORGANIZATION_PROMPT = """Organize as informações extraídas de forma estruturada.

Informações extraídas: {extracted_info}
Consulta original: {user_query}

Organize em:
1. Informações principais (diretamente relacionadas)
2. Informações secundárias (contexto)
3. Referências e fontes

Formate de forma clara e hierárquica.
"""

