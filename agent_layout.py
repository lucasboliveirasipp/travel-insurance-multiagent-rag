"""
Arquivo de Testes de Layout - Agente Acme Parcerias
==============================================

Este módulo é responsável por testar e visualizar o frontend da aplicação
sem necessidade de conexão com LLM ou processamento de backend.

Uso:
    streamlit run agent_layout.py
    
Ou via Python:
    python agent_layout.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Configurar path para imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import streamlit as st

from agente_seguro_viagem_style import (
    init_page_config,
    apply_app_style,
    build_institutional_header,
    build_footer,
    PRIMARY_COLOR,
    SECONDARY_COLOR,
)


# ============================================================================
# CONSTANTES DE MOCK PARA TESTES
# ============================================================================

MOCK_MESSAGES = [
    {
        "role": "user",
        "content": "Quais são os principais benefícios do seguro viagem internacional?"
    },
    {
        "role": "assistant", 
        "content": """O **Seguro Viagem Internacional Acme Parcerias** oferece diversos benefícios essenciais para sua tranquilidade:

**Coberturas Principais:**
- 🏥 **Despesas Médicas e Hospitalares**: Até USD 100.000 para emergências médicas
- 🦷 **Assistência Odontológica**: Cobertura para tratamentos dentários de emergência
- 💼 **Extravio de Bagagem**: Indenização em caso de perda ou atraso da bagagem
- ✈️ **Cancelamento de Viagem**: Reembolso de despesas não reembolsáveis

**Assistências Adicionais:**
- Assistência jurídica no exterior
- Traslado médico de emergência
- Regresso sanitário
- Hospedagem por acompanhante

Posso detalhar alguma cobertura específica?"""
    },
    {
        "role": "user",
        "content": "Qual o valor da cobertura para despesas médicas?"
    },
    {
        "role": "assistant",
        "content": """As coberturas de **Despesas Médicas e Hospitalares (DMH)** variam conforme o plano escolhido:

| Plano | Cobertura DMH | Destino |
|-------|---------------|---------|
| Essencial | USD 30.000 | Nacional |
| Comfort | USD 60.000 | Internacional |
| Premium | USD 100.000 | Internacional |
| VIP | USD 150.000 | Internacional |

**Importante:** Para vgenais à Europa (Espaço Schengen), é obrigatório ter no mínimo EUR 30.000 de cobertura médica.

Gostaria de fazer uma cotação para algum destino específico?"""
    }
]


# ============================================================================
# FUNÇÕES DE COMPONENTES DE LAYOUT
# ============================================================================

def render_chat_messages(messages: list) -> None:
    """Renderiza mensagens do chat."""
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def render_mock_processing() -> None:
    """Renderiza um exemplo de processamento (sem executar realmente)."""
    with st.chat_message("assistant"):
        with st.spinner("🔍 Processando consulta..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Simular passos do pipeline
            steps = [
                ("🎯 Identificando intenção...", 0.2),
                ("📚 Buscando documentos...", 0.4),
                ("📋 Classificando informações...", 0.6),
                ("🔍 Analisando...", 0.8),
                ("✅ Resposta gerada!", 1.0),
            ]
            
            import time
            for status, progress in steps:
                progress_bar.progress(progress)
                status_text.info(status)
                time.sleep(0.5)
            
            status_text.success("✅ Resposta gerada!")
            st.markdown("*Esta é uma resposta de demonstração do layout.*")


def render_info_cards() -> None:
    """Renderiza cards informativos para demonstração."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(
            f"""
            <div class="info-card">
                <h4 style="color: {PRIMARY_COLOR}; margin: 0 0 10px 0;">📊 Métricas</h4>
                <p style="margin: 0;">Consultas hoje: <strong>142</strong></p>
                <p style="margin: 0;">Tempo médio: <strong>2.3s</strong></p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            f"""
            <div class="info-card">
                <h4 style="color: {PRIMARY_COLOR}; margin: 0 0 10px 0;">📚 Base de Conhecimento</h4>
                <p style="margin: 0;">Documentos: <strong>15</strong></p>
                <p style="margin: 0;">Última atualização: <strong>Hoje</strong></p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col3:
        st.markdown(
            f"""
            <div class="info-card">
                <h4 style="color: {PRIMARY_COLOR}; margin: 0 0 10px 0;">🤖 Sistema</h4>
                <p style="margin: 0;">Status: <strong style="color: green;">Online</strong></p>
                <p style="margin: 0;">Agentes ativos: <strong>5</strong></p>
            </div>
            """,
            unsafe_allow_html=True
        )


def render_example_response() -> None:
    """Renderiza uma resposta de exemplo em formato de documento."""
    st.markdown(
        f"""
        <div class="report-paper">
            <div class="doc-title">Resumo do Produto Acme Parcerias</div>
            
            <span class="section-title">Seguro Viagem</span>
            <p>O Seguro Viagem Acme Parcerias oferece proteção completa para viajantes nacionais 
            e internacionais, com coberturas que incluem despesas médicas, extravio de 
            bagagem e cancelamento de viagem.</p>
            
            <span class="section-title">Seguro Dental</span>
            <p>O Seguro Dental Acme Parcerias proporciona acesso a uma ampla rede de dentistas 
            credenciados, com coberturas para procedimentos preventivos, restauradores 
            e emergenciais.</p>
            
            <span class="section-title">Diferenciais</span>
            <ul>
                <li>Atendimento 24 horas em português</li>
                <li>Rede credenciada global</li>
                <li>App para acompanhamento</li>
                <li>Reembolso facilitado</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_button_examples() -> None:
    """Renderiza exemplos de botões."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔍 Pesquisar"):
            st.toast("Botão Pesquisar clicado!")
    
    with col2:
        if st.button("📋 Consultar"):
            st.toast("Botão Consultar clicado!")
    
    with col3:
        if st.button("🗑️ Limpar"):
            st.toast("Botão Limpar clicado!")
    
    with col4:
        st.download_button(
            label="📥 Download",
            data="Exemplo de conteúdo para download",
            file_name="exemplo.txt",
            mime="text/plain"
        )


def render_sidebar() -> None:
    """Renderiza a sidebar de configurações."""
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        st.subheader("🎨 Visualização")
        show_metrics = st.checkbox("Mostrar métricas", value=True)
        show_example_doc = st.checkbox("Mostrar documento exemplo", value=True)
        show_buttons = st.checkbox("Mostrar botões", value=True)
        
        st.divider()
        
        st.subheader("💬 Chat Demo")
        show_mock_messages = st.checkbox("Mostrar mensagens mock", value=True)
        simulate_processing = st.checkbox("Simular processamento", value=False)
        
        st.divider()
        
        st.info("🔧 Este é o modo de teste de layout. Nenhuma LLM está conectada.")
        
        if st.button("🗑️ Resetar Visualização"):
            st.rerun()
        
        return {
            "show_metrics": show_metrics,
            "show_example_doc": show_example_doc,
            "show_buttons": show_buttons,
            "show_mock_messages": show_mock_messages,
            "simulate_processing": simulate_processing
        }


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def build_layout_test_page() -> None:
    """
    Função principal - Entry point para testes de layout.
    
    Renderiza todos os componentes visuais sem conexão com backend/LLM.
    """
    # Configurar página (DEVE ser primeiro)
    init_page_config("Agente Acme Parcerias - Teste de Layout")
    
    # Aplicar estilos Acme
    apply_app_style()
    
    # Renderizar sidebar e obter configurações
    config = render_sidebar()
    
    # Header institucional
    build_institutional_header(
        "Agente Acme Parcerias",
        "Assistente virtual conversacional para dúvidas sobre produtos de viagem e dental"
    )
    
    # Banner de modo de teste
    st.markdown(
        f"""
        <div style="background-color: #FFF3CD; border: 1px solid #FFECB5; 
                    border-radius: 8px; padding: 12px 20px; margin-bottom: 20px;
                    display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 20px;">🎨</span>
            <span style="color: #856404; font-weight: 500;">
                Modo de Teste de Layout - Visualização sem conexão com LLM
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Seção de métricas
    if config["show_metrics"]:
        st.subheader("📊 Cards Informativos")
        render_info_cards()
        st.divider()
    
    # Seção de botões
    if config["show_buttons"]:
        st.subheader("🔘 Exemplos de Botões")
        render_button_examples()
        st.divider()
    
    # Seção de documento exemplo
    if config["show_example_doc"]:
        st.subheader("📄 Documento Exemplo")
        render_example_response()
        st.divider()
    
    # Seção de chat
    st.subheader("💬 Interface de Chat")
    
    if config["show_mock_messages"]:
        render_chat_messages(MOCK_MESSAGES)
    
    if config["simulate_processing"]:
        render_mock_processing()
    
    # Input do chat (apenas visual, não processa)
    if user_input := st.chat_input("Digite sua consulta (modo demonstração)..."):
        with st.chat_message("user"):
            st.markdown(user_input)
        with st.chat_message("assistant"):
            st.info("🎨 Esta é uma resposta de demonstração. O sistema está em modo de teste de layout.")
    
    # Footer institucional
    build_footer(
        "Sistema de Assistência Virtual - Modo de Teste",
        "Grupo Acme Seguros"
    )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    build_layout_test_page()
