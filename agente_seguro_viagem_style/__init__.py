"""
Módulo de estilo padrão Acme Seguros para Streamlit.

Exporta funções principais de design visual.
"""

from .streamlit_style import (
    apply_app_style,
    build_footer,
    build_institutional_header,
    init_page_config,
    get_base64_img,
    THEME_PRIMARY,
    THEME_SECONDARY,
    THEME_TEXT,
    THEME_MUTED,
    THEME_BG_SOFT,
    THEME_BORDER_SOFT,
    THEME_WHITE,
    THEME_RADIUS_MD,
)

__all__ = [
    "init_page_config",
    "apply_app_style",
    "build_institutional_header",
    "build_footer",
    "get_base64_img",
    "THEME_PRIMARY",
    "THEME_SECONDARY",
    "THEME_TEXT",
    "THEME_MUTED",
    "THEME_BG_SOFT",
    "THEME_BORDER_SOFT",
    "THEME_WHITE",
    "THEME_RADIUS_MD",
]
