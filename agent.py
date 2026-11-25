from __future__ import annotations
import sys
import os
import logging

# --- 1. configuração de caminho (path) ---
# Garantir que o diretório do agente seja o PRIMEIRO em sys.path
# (antes do streamlit e do app pai). Assim "utils", "config", "skills", etc.
# resolvem para este projeto e não para outro agente.
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir in sys.path:
    sys.path.remove(current_dir)
sys.path.insert(0, current_dir)

# Limpar módulos cacheados de outros agentes para evitar conflito.
# No ambiente Acme multi-agente, outro agente pode ter carregado
# "utils", "config", "nodes", "prompts" etc. antes. O Python cacheia em
# sys.modules e não re-importa mesmo com sys.path diferente.
_project_modules = ["agente_seguro_viagem_utils", "config", "agente_seguro_viagem_nodes", "agente_seguro_viagem_prompts", "agente_seguro_viagem_schemas"]
for _mod_name in list(sys.modules.keys()):
    for _prefix in _project_modules:
        if _mod_name == _prefix or _mod_name.startswith(f"{_prefix}."):
            del sys.modules[_mod_name]
            break

# --- 2. demais importações ---
import re
import pandas as pd
from uuid import uuid4
from typing import Dict, List, Optional

# bibliotecas externas
import streamlit as st
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

# configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Silenciar warnings do Streamlit file watcher com PyTorch (bug conhecido)
logging.getLogger("streamlit.watcher.local_sources_watcher").setLevel(logging.ERROR)

# --- SISTEMA DE FEEDBACK E LOGS ---
from db_connector import MONGO
from feedback import log_interaction, render_feedback_widget

AGENT_NAME = os.path.basename(current_dir)

# --- importação do estilo visual ---
try:
    from agente_seguro_viagem_style.streamlit_style import (
        init_page_config,
        apply_app_style,
        build_institutional_header,
        build_footer
    )
except ImportError as e:
    st.error(f"ERRO CRÍTICO: não foi possível importar 'streamlit_style'. detalhe: {e}")
    st.stop()

# --- configuração inicial ---

try:
    from graph_builder import build_graph
    graph = build_graph()
except ImportError:
    class MockGraph:
        def get_state(self, *args, **kwargs): return {}
        def stream(self, *args, **kwargs): return []
    graph = MockGraph()

# --- 5. css local (estilo dos cards) ---
def _inject_component_styles():
    st.markdown("""
    <style>
        .status-banner {
            background-color: #FFFFFF;
            color: #2D3748;
            padding: 16px 24px;
            border-radius: 12px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            margin-bottom: 24px;
            border: 1px solid #EDF2F7;
            display: flex; align-items: center; justify-content: space-between;
            font-family: 'Segoe UI', sans-serif !important;
        }
        .status-text {
            color: #1E3A8A;
            font-weight: 700; letter-spacing: 0.5px;
            text-transform: uppercase; font-size: 0.9rem;
        }
        .status-pill {
            background-color: #1E3A8A;
            color: white !important;
            padding: 6px 16px; border-radius: 6px;
            font-weight: 600; font-size: 0.85rem;
        }
        .manual-card h3 {
            color: #1E3A8A !important;
            font-family: 'Segoe UI', sans-serif !important;
            font-weight: 700 !important;
            font-size: 1.25rem !important;
            margin-bottom: 12px !important;
        }
        .manual-card p, .manual-card li, .manual-card span {
            color: #2D3748 !important;
            font-family: 'Segoe UI', sans-serif !important;
            line-height: 1.6;
        }
        .file-item {
            display: flex; align-items: center; gap: 10px;
            padding: 8px 0; border-bottom: 1px solid #EDF2F7;
            color: #2D3748;
            font-family: 'Segoe UI', sans-serif !important;
        }
        .source-card {
            background-color: #F7FAFC;
            border-left: 4px solid #1E3A8A;
            border-radius: 8px;
            padding: 12px 16px;
            margin: 8px 0;
        }
        .source-card .source-title {
            font-weight: 600;
            color: #2D3748;
            font-size: 0.9rem;
        }
        .source-card .source-detail {
            color: #718096;
            font-size: 0.8rem;
            margin-top: 4px;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 6. componentes de interface (fontes) ---

def _escape_dollar_for_markdown(text: str) -> str:
    """
    Escapa o caractere $ no texto para evitar formatação LaTeX indesejada no st.markdown.
    Perguntas/respostas com valores como R$ 139 milhões vinham mal formatadas.
    """
    if not text:
        return text
    return text.replace("$", "\\$")

def is_generic_query(query: str) -> bool:
    """
    Detecta se a pergunta é genérica/interação social para evitar mostrar fontes.
    """
    if not query: return True
    
    query = query.lower().strip()
    
    # Lista de termos que indicam interação básica sem necessidade de documentos
    generic_terms = [
        "oi", "ola", "olá", "bom dia", "boa tarde", "boa noite",
        "tudo bem", "quem é você", "quem e voce", "o que você faz",
        "o que voce faz", "ajuda", "help", "teste",
        "sobre o que posso perguntar", "quais assuntos", "o que você sabe"
    ]
    
    # Se a query for muito curta (< 5 chars) ou contiver termos genéricos
    is_short_greeting = len(query) < 5
    is_common_phrase = any(term in query for term in generic_terms)
    
    return is_short_greeting or is_common_phrase

def _render_sources(sources: List[Dict], query: str = "") -> None:
    """
    Renderiza a lista de fontes consultadas no rodapé da mensagem.
    Filtra interações genéricas (chit-chat).
    """
    if is_generic_query(query):
        return

    if not sources: return

    unique_files = set()
    clean_list = []

    for source in sources:
        # Lógica mista (novo e antigo)
        raw_name = source.get("source")
        if not raw_name:
            raw_name = source.get("filepathField")
        if not raw_name:
            raw_name = source.get("filename") or "Desconhecido"
        
        name = os.path.basename(raw_name)

        if name and name != "Desconhecido" and name != "Documento sem nome" and name not in unique_files:
            unique_files.add(name)
            clean_list.append(name)

    if not clean_list: return

    with st.expander(f"📚 Fontes Consultadas ({len(clean_list)})", expanded=False):
        for name in clean_list:
            st.markdown(f"""
            <div class="source-card">
                <div class="source-title">📄 {name}</div>
            </div>""", unsafe_allow_html=True)

# --- 7. página do guia rápido (manual) ---
def render_manual_page():
    tab1, tab2 = st.tabs(["📍 Comece por Aqui", "📂 Base de Conhecimento"])
    
    with tab1:
        st.markdown("""
        <div class="status-banner">
            <div class="status-text">ESPECIALISTA</div>
            <div class="status-pill">Status: Online 🟢</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="manual-card">
            <h3>✅ Capacidades</h3>
            <p style="margin-bottom: 15px;">
                Atuo como seu apoiador estratégico para dúvidas sobre produtos de viagem e dental. Minha missão é varrer a complexidade técnica dos manuais 
                para entregar a <b>fundamentação técnica necessária</b>.
            </p>
            <p>
                Sou uma inteligência focada exclusivamente em consulta documental: <b>não acesso dados de apólices em tempo real e não realizo transações</b>. 
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="manual-card">
            <h3>🔍 O que perguntar?</h3>
            <ul style="padding-left: 20px;">
                <li style="margin-bottom:10px;"><b>Coberturas:</b> informações sobre coberturas de viagem e assistência dental.</li>
                <li style="margin-bottom:10px;"><b>Procedimentos:</b> regras para acionamento, prazos e carências.</li>
                <li><b>Documentação:</b> checklists obrigatórios para cada tipo de sinistro.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="manual-card" style="margin-bottom: 10px; padding-bottom: 10px;">
            <h3>💡 Exemplos de Perguntas</h3>
            <p style="font-style: italic; font-size: 0.9em; margin-bottom: 10px;">Clique no ícone de copiar no canto direito de cada pergunta:</p>
        </div>
        """, unsafe_allow_html=True)

        exemplos = [
            "Quais são as coberturas do seguro viagem internacional?",
            "Qual o prazo de carência para procedimentos dentais?",
            "Como funciona o acionamento da assistência em viagem?",
            "Quais documentos são necessários para reembolso de despesas médicas no exterior?"
        ]

        for pergunta in exemplos:
            st.code(pergunta, language="text")
        
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
        <div class="manual-card">
            <h3>🚫 Limitações</h3>
            <ul style="padding-left: 20px;">
                <li style="margin-bottom:8px;">Minhas respostas baseiam-se estritamente nos documentos ingeridos na ferramenta.</li>
                <li style="margin-bottom:8px;">Caso identifique algum manual desatualizado, contate a equipe de IA Generativa.</li>
                <li style="margin-bottom:8px;"><b>Subjetividade:</b> não analiso fotos ou áudios. Análise apenas textual.</li>
                <li><b>Ação Financeira:</b> eu sugiro e embaso, mas a decisão final é sua.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with tab2:
        st.markdown("### 📄 Documentos Disponíveis")
        st.markdown("Estes arquivos foram adicionados ao projeto e são usados pelo agente como referência.")
        
        # Lista arquivos da pasta de dados
        data_dir = os.path.join(current_dir, "base de dados para indexar")
        if os.path.exists(data_dir):
            files = [f for f in os.listdir(data_dir) if f.endswith(('.pdf', '.docx', '.xlsx'))]
            if files:
                df = pd.DataFrame({"Nome do Documento": files})
                st.dataframe(
                    df, 
                    hide_index=True, 
                    use_container_width=True, 
                    height=300
                )
            else:
                st.warning("⚠️ Nenhum documento encontrado na pasta de dados.")
        else:
            st.warning("⚠️ Pasta de dados não encontrada.")
            
# --- 8. estado do grafo ---
def _get_graph_state(thread_id: str) -> List[BaseMessage]:
    try:
        state = graph.get_state({"configurable": {"thread_id": thread_id}})
        return state.values.get("messages", []) if state and state.values else []
    except:
        return []

# --- 9. app principal (interface) ---
def build_page(is_authenticated: bool = True, *args, **kwargs) -> None:
    apply_app_style()
    _inject_component_styles()
    
    # CSS adicional para sidebar igual ao regulacao
    st.markdown("""
    <style>
        /* Logo da sidebar */
        .sidebar-logo {
            width: 60px;
            height: auto;
            margin-bottom: 20px;
        }
        
        /* Card do agente ativo */
        .agent-active-card {
            background-color: #FFFFFF;
            border: 1px solid #EDF2F7;
            border-left: 4px solid #1E3A8A;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 16px;
        }
        .agent-active-label {
            font-size: 0.7rem;
            color: #1E3A8A;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        .agent-active-name {
            font-size: 0.9rem;
            color: #2D3748;
            font-weight: 500;
        }
        
        /* Botões da sidebar */
        [data-testid="stSidebar"] .stButton > button {
            width: 100%;
            justify-content: flex-start;
            padding: 10px 16px;
            margin-bottom: 8px;
        }
        
        /* Botão Sair (amarelo) */
        .sair-btn > button {
            background-color: #F6E05E !important;
            color: #744210 !important;
            border: none !important;
        }
        .sair-btn > button:hover {
            background-color: #ECC94B !important;
        }
    </style>
    """, unsafe_allow_html=True)

    if "thread_id" not in st.session_state: st.session_state["thread_id"] = str(uuid4())
    if "current_page" not in st.session_state: st.session_state["current_page"] = "chat"
    if "edit_mode" not in st.session_state: st.session_state["edit_mode"] = False
    if "messages" not in st.session_state: st.session_state["messages"] = []
    
    if "latest_response_id" not in st.session_state: st.session_state["latest_response_id"] = None
    
    with st.sidebar:
        # Logo Acme no topo
        logo_path = os.path.join(current_dir, "agente_seguro_viagem_assets", "icone.png")
        if os.path.exists(logo_path):
            st.image(logo_path, width=60)
        
        # Card "AGENTE ATIVO"
        st.markdown(f"""
        <div class="agent-active-card">
            <div class="agent-active-label">AGENTE ATIVO</div>
            <div class="agent-active-name">{AGENT_NAME}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Botão Voltar ao Hub
        if st.button("🏠 Voltar ao Hub", type="secondary", use_container_width=True):
            # Placeholder - será gerenciado pelo portal
            pass
        
        st.markdown("---")
        
        # Navegação do agente
        if st.button("💬 Agente Acme Parcerias", type="primary" if st.session_state["current_page"] == "chat" else "secondary", use_container_width=True):
            st.session_state["current_page"] = "chat"
            st.rerun()

        if st.button("📘 Guia Rápido", type="primary" if st.session_state["current_page"] == "manual" else "secondary", use_container_width=True):
            st.session_state["current_page"] = "manual"
            st.rerun()
        
        st.markdown("---")
        
        if st.session_state["current_page"] == "chat":
            if st.button("🗑️ Limpar Conversa", type="secondary", use_container_width=True):
                st.session_state["thread_id"] = str(uuid4())
                st.session_state["edit_mode"] = False
                st.session_state["latest_response_id"] = None
                st.session_state["messages"] = []
                st.cache_data.clear()
                st.rerun()
            
            if st.session_state["messages"]:
                last_user_msg = None
                for msg in reversed(st.session_state["messages"]):
                    if msg["role"] == "user":
                        last_user_msg = msg["content"]
                        break
                
                if last_user_msg:
                    if st.button("🔄 Refazer Última", type="secondary", use_container_width=True): 
                        st.session_state["edit_mode"] = True
                        st.session_state["text_to_edit"] = last_user_msg
                        st.rerun()
        
        # Espaço flexível antes do botão Sair
        st.markdown("<br>" * 5, unsafe_allow_html=True)
        
        # Botão Sair (amarelo, no final)
        st.markdown('<div class="sair-btn">', unsafe_allow_html=True)
        if st.button("🚪 Sair", type="secondary", use_container_width=True):
            # Placeholder - será gerenciado pelo portal
            pass
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state["current_page"] == "manual":
        build_institutional_header(
            title="📘 Guia Rápido",
            subtitle="Tudo que você precisa saber: boas práticas, orientações e manual de referência",
        )
        render_manual_page()
        build_footer()
    else:
        build_institutional_header(
            title="Agente Acme Parcerias",
            subtitle="Assistente especializado no Book de Produtos Acme Parcerias - Viagem e Dental",
        )
        
        thread_id = st.session_state["thread_id"]
        config = {"configurable": {"thread_id": thread_id}}
        final_prompt = None

        # Resumo do agente quando não há mensagens
        if not st.session_state["messages"]:
            st.markdown("""
            <div class="manual-card" style="margin-bottom: 20px;">
                <h3>📚 Sobre este Agente</h3>
                <p style="margin-bottom: 12px;">
                    Sou um assistente especializado no <b>Book de Produtos Acme Parcerias</b>, sua fonte de consulta para:
                </p>
                <ul style="padding-left: 20px; margin-bottom: 12px;">
                    <li><b>Seguro Viagem:</b> coberturas, assistências, limites e procedimentos para vgenais nacionais e internacionais.</li>
                    <li><b>Assistência Dental:</b> planos, carências, rede credenciada e regras de utilização.</li>
                </ul>
                <p style="font-size: 0.9em; color: #718096;">
                    💡 <i>Dica: Pergunte sobre coberturas específicas, documentação necessária ou como acionar os serviços.</i>
                </p>
            </div>
            """, unsafe_allow_html=True)

        if st.session_state["edit_mode"]:
            st.info("📝 **Editando pergunta:**")
            with st.form("edit_form"):
                txt = st.text_area("Sua pergunta:", value=st.session_state.get("text_to_edit", ""))
                c1, c2 = st.columns([1, 4])
                if c1.form_submit_button("🚀 Reenviar", type="primary"):
                    final_prompt = txt
                    st.session_state["edit_mode"] = False
                if c2.form_submit_button("❌ Cancelar"):
                    st.session_state["edit_mode"] = False
                    st.rerun()
        else:
            if user_input := st.chat_input("Digite sua pergunta sobre produtos de viagem ou dental..."):
                final_prompt = user_input

        chat_container = st.container()
        with chat_container:
            # LOOP DO HISTÓRICO
            total_msgs = len(st.session_state["messages"])
            for i, msg in enumerate(st.session_state["messages"]):
                role = msg["role"]
                is_last_assistant = (
                    role == "assistant"
                    and i == total_msgs - 1
                )
                with st.chat_message(role):
                    st.markdown(_escape_dollar_for_markdown(msg["content"]))
                    if role == "assistant" and "sources" in msg:
                        user_q = ""
                        if i > 0 and st.session_state["messages"][i-1]["role"] == "user":
                            user_q = st.session_state["messages"][i-1]["content"]

                        _render_sources(msg.get("sources", []), query=user_q)

                # Feedback widget apenas na última resposta do assistente
                if is_last_assistant and st.session_state.get("latest_response_id"):
                    render_feedback_widget(
                        mongo_db=MONGO,
                        agent_name=AGENT_NAME,
                        thread_id=st.session_state["thread_id"],
                        response_id=st.session_state["latest_response_id"],
                    )

            if final_prompt and not st.session_state.get("edit_mode"):
                with st.chat_message("user"): 
                    st.markdown(_escape_dollar_for_markdown(final_prompt))
                
                # Adiciona mensagem do usuário ao histórico
                st.session_state["messages"].append({"role": "user", "content": final_prompt})
                
                with st.chat_message("assistant"):
                    with st.spinner("Formulando uma resposta..."):
                        try:
                            from agent_state import AgentState
                            from config_constants_viagem import LANGGRAPH_RECURSION_LIMIT
                            
                            # Estado inicial
                            initial_state: AgentState = {
                                "messages": [HumanMessage(content=final_prompt)],
                                "user_query": final_prompt,
                                "query_intent": None,
                                "requires_analysis": False,
                                "extracted_documents": {},
                                "relevant_chunks": [],
                                "classified_info": {},
                                "query_type": None,
                                "analysis_result": None,
                                "response": None,
                                "conversation_context": None,
                                "validation_status": None,
                                "next": None,
                                "error": None,
                                "metadata": {},
                                "iteration_count": 0
                            }
                            
                            config = {
                                "recursion_limit": LANGGRAPH_RECURSION_LIMIT,
                                "configurable": {"thread_id": thread_id}
                            }
                            
                            final_state = None
                            for state in graph.stream(initial_state, config, stream_mode="values"):
                                final_state = state
                            
                            if final_state and final_state.get("response"):
                                response_text = final_state["response"]
                                st.markdown(_escape_dollar_for_markdown(response_text))
                                
                                # Adiciona resposta ao histórico
                                st.session_state["messages"].append({
                                    "role": "assistant",
                                    "content": response_text,
                                    "sources": final_state.get("metadata", {}).get("sources", [])
                                })
                                
                                # Registrar interação e preparar feedback
                                response_id = log_interaction(
                                    mongo_db=MONGO,
                                    agent_name=AGENT_NAME,
                                    thread_id=thread_id,
                                    user_question=final_prompt,
                                    chatbot_response=response_text,
                                )
                                st.session_state["latest_response_id"] = response_id
                                st.rerun()
                            else:
                                error_msg = "Desculpe, não consegui gerar uma resposta. Poderia reformular sua pergunta?"
                                st.warning(error_msg)
                                st.session_state["messages"].append({
                                    "role": "assistant",
                                    "content": error_msg
                                })
                        except Exception as e:
                            logger.error(f"Erro no pipeline: {e}", exc_info=True)
                            error_msg = f"Ocorreu um erro ao processar sua pergunta: {str(e)}"
                            st.error(error_msg)
                            st.session_state["messages"].append({
                                "role": "assistant",
                                "content": error_msg
                            })
                
                if final_prompt and "edit_form" in str(st.session_state): st.rerun()


if __name__ == "__main__":
    init_page_config("Agente Acme Parcerias")
    build_page(is_authenticated=True)
