import base64
from datetime import datetime
from pathlib import Path
import streamlit as st

# Diretórios base
_THIS_FILE = Path(__file__).resolve()
_BASE_DIR = None

# Tenta encontrar a pasta 'assets' ou 'icons' subindo os diretórios
for _p in _THIS_FILE.parents:
    if (_p / "agente_seguro_viagem_assets").exists():
        _BASE_DIR = _p
        _ASSETS_DIR = _BASE_DIR / "agente_seguro_viagem_assets"
        break
    if (_p / "icons").exists():
        _BASE_DIR = _p
        _ASSETS_DIR = _BASE_DIR / "icons"
        break

if _BASE_DIR is None:
    _BASE_DIR = _THIS_FILE.parent.parent 
    _ASSETS_DIR = _BASE_DIR / "agente_seguro_viagem_assets"

# Cores
THEME_PRIMARY = "#1E3A8A"
THEME_SECONDARY = "#0F766E"
THEME_TEXT = "#010307"
THEME_MUTED = "#718096"
THEME_BG_SOFT = "#F7FAFC"
THEME_BORDER_SOFT = "#EDF2F7"
THEME_WHITE = "#FFFFFF"
THEME_RADIUS_MD = "12px"

def init_page_config(title: str = "Agente Acme"):
    """
    Configuração inicial da página Streamlit.
    """
    if st.session_state.get("_bs_page_configured", False):
        return

    # Tenta carregar ícone
    icon_path = _ASSETS_DIR / "icone.png"
    if not icon_path.exists():
        icon_path = _ASSETS_DIR / "header_logo.png"

    config_kwargs = {
        "page_title": title,
        "layout": "wide",
        "initial_sidebar_state": "expanded",
    }

    if icon_path.exists():
        config_kwargs["page_icon"] = str(icon_path)

    try:
        st.set_page_config(**config_kwargs)
    except Exception:
        pass
    finally:
        st.session_state["_bs_page_configured"] = True

def get_base64_img(path: str):
    """Auxiliar para converter imagem em base64"""
    p = Path(path)
    if p.exists():
        with open(p, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

def apply_app_style():
    # CSS Global
    # O HTML continua colado na esquerda para evitar o bug visual
    st.markdown(
f"""
<style>
:root {{
    --theme-primary-primary: {THEME_PRIMARY};
    --theme-secondary-hover: {THEME_SECONDARY};
    --theme-text: {THEME_TEXT};
    --theme-bg-soft: {THEME_BG_SOFT};
    --theme-white: {THEME_WHITE};
    --theme-radius-md: {THEME_RADIUS_MD};
}}

.block-container {{
    padding-top: 2rem;
    max-width: 1200px;
}}

/* Estilo Base dos Cards (Guia Rápido etc) */
.report-paper, .manual-card {{
    background-color: var(--theme-white);
    color: var(--theme-text);
    border-radius: var(--theme-radius-md);
    padding: 25px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.10);
    margin-bottom: 20px;
    border: 1px solid #e0e0e0;
}}

.manual-card {{
    border-left: 5px solid var(--theme-primary-primary);
}}

/* --- COR, FONTE E TAMANHO DOS TÍTULOS --- */
div.manual-card h3, 
.manual-card h3 {{
    color: #1E3A8A !important;      /* Vermelho Exato */
    font-weight: 700 !important;    /* Negrito */
    
    /* FONTE ESPECÍFICA SOLICITADA */
    font-family: 'Segoe UI', sans-serif !important; 
    
    /* TAMANHO REDUZIDO (De 22px para 18px) */
    font-size: 18px !important;
    
    margin-bottom: 12px !important;
}}

.manual-card p, 
.manual-card li, 
.manual-card span,
.manual-card div {{
    color: #2D3748 !important;
    font-family: 'Segoe UI', sans-serif !important; /* Aplica Segoe UI no texto também para combinar */
}}

/* Títulos H1 e H2 gerais */
.doc-title {{
    font-size: 24px;
    font-weight: 700;
    color: var(--theme-primary-primary);
    margin-bottom: 20px;
    border-bottom: 2px solid #EDF2F7;
    padding-bottom: 10px;
    font-family: 'Segoe UI', sans-serif !important;
}}

/* Botões */
.stButton > button {{
    background-color: var(--theme-primary-primary) !important;
    color: white !important;
    border-radius: 8px !important;
    border: none !important;
    font-weight: 600 !important;
    font-family: 'Segoe UI', sans-serif !important;
    transition: all 0.2s ease;
}}
.stButton > button:hover {{
    background-color: var(--theme-secondary-hover) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(30, 58, 138, 0.25);
}}

/* Esconde visualizador de imagem padrão se necessário */
img[data-testid="stImage"] {{ display: none; }}
</style>
""",
        unsafe_allow_html=True,
    )
 
def build_institutional_header(title: str, subtitle: str, show_logo: bool = True):
    """
    Cabeçalho híbrido: 
    - Se show_logo=True -> Layout Centralizado (Logo acima, Texto abaixo).
    - Se show_logo=False -> Layout Centralizado (Apenas texto).
    """
    # Caminhos dos ícones
    icon_extenso_path = str(_ASSETS_DIR / "icone + nome extenso.png")
    icon_curto_path = str(_ASSETS_DIR / "icone + nome curto.png")
    icon_simples_path = str(_ASSETS_DIR / "icone.png")
    
    # Fallback para o header_logo se o icone.png não existir
    if not Path(icon_simples_path).exists() and not Path(icon_extenso_path).exists():
         icon_simples_path = str(_ASSETS_DIR / "header_logo.png")

    b64_extenso = get_base64_img(icon_extenso_path)
    b64_curto = get_base64_img(icon_curto_path)
    b64_simples = get_base64_img(icon_simples_path)

    # --- Lógica de Layout Dinâmico (AJUSTADO PARA CENTRALIZAR TUDO) ---
    # Independentemente do logo, vamos usar flex-direction: column e text-align: center
    flex_direction = "column"
    text_align = "center"
    justify_content = "center"
    gap = "15px"
    logo_margin = "0"

    st.markdown(
f"""
<style>
.header-container {{
    background: linear-gradient(135deg, {THEME_PRIMARY} 0%, {THEME_SECONDARY} 100%);
    color: white;
    padding: 30px 40px;
    border-radius: 14px;
    margin-bottom: 30px;
    box-shadow: 0 4px 15px rgba(30, 58, 138, 0.20);
    
    display: flex;
    flex-direction: {flex_direction}; 
    align-items: center; 
    justify-content: {justify_content};
    text-align: {text_align};
    gap: {gap};
}}

/* Classes dos Logos */
.logo-base {{
    height: auto;
    object-fit: contain;
    flex-shrink: 0;
    margin-bottom: {logo_margin};
}}

/* Ajustes de tamanho dos logos para o modo centralizado */
.logo-extenso {{ max-width: 500px; max-height: 180px; }}
.logo-curto {{ max-width: 400px; max-height: 150px; display: none; }}
.logo-simples {{ max-width: 120px; max-height: 120px; }}

/* Coluna de Texto */
.header-text-col {{
    display: flex;
    flex-direction: column;
}}
.header-title {{
    margin: 0;
    font-size: 2.2rem;
    font-weight: 700;
    line-height: 1.1;
    color: white !important;
}}
.header-subtitle {{
    margin-top: 8px;
    font-size: 1.1rem;
    opacity: 0.95;
    font-weight: 400;
    color: #f0f0f0 !important;
}}

/* Responsividade */
@media (max-width: 768px) {{
    .header-container {{
        padding: 20px;
        gap: 15px;
    }}
    .logo-extenso {{ display: none !important; }}
    .logo-curto {{ display: block !important; margin: 0 auto 15px auto; }}
}}
</style>
""",
        unsafe_allow_html=True,
    )

    header_html = '<div class="header-container">'
    
    if show_logo:
        # Prioridade para o logo simples (header_logo/icone) no modo centralizado, fica mais elegante
        if b64_simples:
            header_html += f'<img src="data:image/png;base64,{b64_simples}" class="logo-base logo-simples" alt="Acme">'
        elif b64_extenso:
            header_html += f'<img src="data:image/png;base64,{b64_extenso}" class="logo-base logo-extenso" style="display:block !important;" alt="Acme Seguros">'
        elif b64_curto:
            header_html += f'<img src="data:image/png;base64,{b64_curto}" class="logo-base logo-curto" style="display:block !important; margin:0 auto;" alt="Acme">'

    header_html += '<div class="header-text-col">'
    header_html += f'<h1 class="header-title">{title}</h1>'
    header_html += f'<p class="header-subtitle">{subtitle}</p>'
    header_html += '</div>'
    
    header_html += "</div>"

    st.markdown(header_html, unsafe_allow_html=True)
    
def build_footer():
    """Rodapé padrão Acme Seguros"""
    st.markdown("---")
    st.markdown(
        f"""
        <div style="text-align: center; color: {THEME_MUTED}; font-size: 12px; padding: 20px;">
            <p>Acme Seguros - {datetime.now().year}</p>
            <p>Agente de IA generativa — projeto de portfólio.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
