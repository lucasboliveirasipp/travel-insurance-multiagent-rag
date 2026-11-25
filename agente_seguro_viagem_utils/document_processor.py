"""Processador de documentos para preparação e limpeza de texto."""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """Limpa e normaliza texto extraído.
    
    Args:
        text: Texto bruto
        
    Returns:
        Texto limpo e normalizado
    """
    if not text:
        return ""
    
    # Remover múltiplos espaços em branco
    text = re.sub(r'\s+', ' ', text)
    
    # Remover quebras de linha excessivas
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remover caracteres de controle
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    return text.strip()


def split_into_chunks(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Divide texto em chunks para processamento.
    
    Args:
        text: Texto a dividir
        chunk_size: Tamanho máximo do chunk em caracteres
        overlap: Sobreposição entre chunks
        
    Returns:
        Lista de chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Tentar quebrar em quebra de linha ou espaço
        if end < len(text):
            # Procurar última quebra de linha antes do fim
            last_newline = text.rfind('\n', start, end)
            if last_newline > start:
                end = last_newline
            else:
                # Procurar último espaço
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks


def extract_sections(text: str) -> Dict[str, str]:
    """Extrai seções do texto baseado em títulos.
    
    Args:
        text: Texto completo
        
    Returns:
        Dicionário com seções identificadas
    """
    sections = {}
    current_section = "introdução"
    current_content = []
    
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Detectar títulos (linhas em maiúsculas ou com formatação especial)
        if (len(line) < 100 and 
            (line.isupper() or 
             line.startswith('#') or
             re.match(r'^\d+\.\s+[A-Z]', line))):
            # Salvar seção anterior
            if current_content:
                sections[current_section] = '\n'.join(current_content)
            
            # Nova seção
            current_section = line.lower().replace('#', '').strip()
            current_content = []
        else:
            current_content.append(line)
    
    # Salvar última seção
    if current_content:
        sections[current_section] = '\n'.join(current_content)
    
    return sections

