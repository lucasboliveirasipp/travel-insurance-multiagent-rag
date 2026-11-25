"""Extrator de PDFs usando Azure Form Recognizer e OCR.

Implementa extração de texto e estrutura de PDFs com fallback para
bibliotecas Python quando Azure não está disponível.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import io

# Configurar path para imports
current_dir = Path(__file__).parent
if str(current_dir.parent) not in sys.path:
    sys.path.insert(0, str(current_dir.parent))

from config import (
    form_recognizer_client,
    form_recognizer_available,
    computer_vision_client,
    computer_vision_available,
    MAX_FILE_SIZE_MB
)
from agente_seguro_viagem_utils.cache_manager import get_cache_manager, get_file_hash, get_cache_key

logger = logging.getLogger(__name__)

# Importações lazy para fallback
FALLBACK_AVAILABLE = False
try:
    import PyPDF2
    import pdfplumber
    FALLBACK_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Bibliotecas de fallback não disponíveis")


def extract_with_form_recognizer(file_data: bytes, file_name: str) -> Dict[str, Any]:
    """Extrai texto usando Azure Form Recognizer.
    
    Args:
        file_data: Bytes do arquivo PDF
        file_name: Nome do arquivo
        
    Returns:
        Dicionário com texto extraído e metadados
    """
    if not form_recognizer_available or not form_recognizer_client:
        raise ValueError("Azure Form Recognizer não disponível")
    
    try:
        logger.info(f"📄 Extraindo com Form Recognizer: {file_name}")
        
        # Verificar cache
        cache = get_cache_manager()
        file_hash = get_file_hash(file_data)
        cache_key = get_cache_key("form_recognizer", file_hash)
        
        if cache:
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info("✅ Resultado encontrado no cache")
                return cached_result
        
        # Extrair com Form Recognizer
        poller = form_recognizer_client.begin_analyze_document(
            model_id="prebuilt-read",
            document=file_data
        )
        result = poller.result()
        
        # Processar resultado
        extracted_text = ""
        pages = []
        
        for page in result.pages:
            page_text = ""
            for line in page.lines:
                page_text += line.content + "\n"
            pages.append({
                "page_number": page.page_number,
                "text": page_text.strip()
            })
            extracted_text += page_text + "\n\n"
        
        result_dict = {
            "text": extracted_text.strip(),
            "pages": pages,
            "total_pages": len(pages),
            "extraction_method": "azure_form_recognizer",
            "file_name": file_name,
            "file_hash": file_hash
        }
        
        # Armazenar no cache
        if cache:
            cache.set(cache_key, result_dict, cache_type="extraction")
        
        logger.info(f"✅ Extração concluída: {len(pages)} páginas")
        return result_dict
        
    except Exception as e:
        logger.error(f"❌ Erro no Form Recognizer: {e}", exc_info=True)
        raise


def extract_with_computer_vision(file_data: bytes, file_name: str) -> Dict[str, Any]:
    """Extrai texto usando Azure Computer Vision OCR.
    
    Args:
        file_data: Bytes do arquivo PDF/imagem
        file_name: Nome do arquivo
        
    Returns:
        Dicionário com texto extraído e metadados
    """
    if not computer_vision_available or not computer_vision_client:
        raise ValueError("Azure Computer Vision não disponível")
    
    try:
        logger.info(f"📄 Extraindo com Computer Vision: {file_name}")
        
        # Verificar cache
        cache = get_cache_manager()
        file_hash = get_file_hash(file_data)
        cache_key = get_cache_key("computer_vision", file_hash)
        
        if cache:
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info("✅ Resultado encontrado no cache")
                return cached_result
        
        # Extrair com Computer Vision
        result = computer_vision_client.read_in_stream(
            io.BytesIO(file_data),
            raw=True
        )
        
        # Aguardar conclusão
        from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
        import time
        
        operation_id = result.headers["Operation-Location"].split("/")[-1]
        while True:
            read_result = computer_vision_client.get_read_result(operation_id)
            if read_result.status not in ['notStarted', 'running']:
                break
            time.sleep(1)
        
        # Processar resultado
        extracted_text = ""
        pages = []
        
        if read_result.status == OperationStatusCodes.succeeded:
            for page_result in read_result.analyze_result.read_results:
                page_text = ""
                for line in page_result.lines:
                    page_text += line.text + "\n"
                pages.append({
                    "page_number": page_result.page_number,
                    "text": page_text.strip()
                })
                extracted_text += page_text + "\n\n"
        
        result_dict = {
            "text": extracted_text.strip(),
            "pages": pages,
            "total_pages": len(pages),
            "extraction_method": "azure_computer_vision",
            "file_name": file_name,
            "file_hash": file_hash
        }
        
        # Armazenar no cache
        if cache:
            cache.set(cache_key, result_dict, cache_type="extraction")
        
        logger.info(f"✅ Extração concluída: {len(pages)} páginas")
        return result_dict
        
    except Exception as e:
        logger.error(f"❌ Erro no Computer Vision: {e}", exc_info=True)
        raise


def extract_with_pypdf2(file_data: bytes, file_name: str) -> Dict[str, Any]:
    """Extrai texto usando PyPDF2 (fallback).
    
    Args:
        file_data: Bytes do arquivo PDF
        file_name: Nome do arquivo
        
    Returns:
        Dicionário com texto extraído e metadados
    """
    if not FALLBACK_AVAILABLE:
        raise ValueError("PyPDF2 não disponível")
    
    try:
        logger.info(f"📄 Extraindo com PyPDF2 (fallback): {file_name}")
        
        pdf_file = io.BytesIO(file_data)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        extracted_text = ""
        pages = []
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            page_text = page.extract_text()
            pages.append({
                "page_number": page_num,
                "text": page_text.strip()
            })
            extracted_text += page_text + "\n\n"
        
        result_dict = {
            "text": extracted_text.strip(),
            "pages": pages,
            "total_pages": len(pages),
            "extraction_method": "pypdf2_fallback",
            "file_name": file_name
        }
        
        logger.info(f"✅ Extração concluída: {len(pages)} páginas")
        return result_dict
        
    except Exception as e:
        logger.error(f"❌ Erro no PyPDF2: {e}", exc_info=True)
        raise


def extract_with_pdfplumber(file_data: bytes, file_name: str) -> Dict[str, Any]:
    """Extrai texto usando pdfplumber (fallback melhorado).
    
    Args:
        file_data: Bytes do arquivo PDF
        file_name: Nome do arquivo
        
    Returns:
        Dicionário com texto extraído e metadados
    """
    if not FALLBACK_AVAILABLE:
        raise ValueError("pdfplumber não disponível")
    
    try:
        logger.info(f"📄 Extraindo com pdfplumber (fallback): {file_name}")
        
        pdf_file = io.BytesIO(file_data)
        pdf = pdfplumber.open(pdf_file)
        
        extracted_text = ""
        pages = []
        
        for page_num, page in enumerate(pdf.pages, 1):
            page_text = page.extract_text() or ""
            pages.append({
                "page_number": page_num,
                "text": page_text.strip()
            })
            extracted_text += page_text + "\n\n"
        
        pdf.close()
        
        result_dict = {
            "text": extracted_text.strip(),
            "pages": pages,
            "total_pages": len(pages),
            "extraction_method": "pdfplumber_fallback",
            "file_name": file_name
        }
        
        logger.info(f"✅ Extração concluída: {len(pages)} páginas")
        return result_dict
        
    except Exception as e:
        logger.error(f"❌ Erro no pdfplumber: {e}", exc_info=True)
        raise


def extract_pdf(file_path: Optional[str] = None, file_data: Optional[bytes] = None) -> Dict[str, Any]:
    """Extrai texto de PDF com fallback automático.
    
    Tenta usar Azure Form Recognizer primeiro, depois Computer Vision,
    e por fim bibliotecas Python como fallback.
    
    Args:
        file_path: Caminho do arquivo (opcional)
        file_data: Bytes do arquivo (opcional)
        
    Returns:
        Dicionário com texto extraído e metadados
        
    Raises:
        ValueError: Se nem arquivo nem dados fornecidos
        Exception: Se todas as tentativas de extração falharem
    """
    logger.info("=" * 60)
    logger.info("INICIANDO EXTRAÇÃO DE PDF")
    logger.info("=" * 60)
    
    # Validar entrada
    if file_path:
        file_name = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            file_data = f.read()
    elif file_data:
        file_name = "uploaded_file.pdf"
    else:
        raise ValueError("Forneça file_path ou file_data")
    
    # Validar tamanho
    file_size_mb = len(file_data) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"Arquivo muito grande: {file_size_mb:.2f}MB (máximo: {MAX_FILE_SIZE_MB}MB)")
    
    logger.info(f"📄 Arquivo: {file_name} ({file_size_mb:.2f}MB)")
    
    # Tentar extração com fallback
    extraction_methods = [
        ("Azure Form Recognizer", extract_with_form_recognizer),
        ("Azure Computer Vision", extract_with_computer_vision),
        ("pdfplumber", extract_with_pdfplumber),
        ("PyPDF2", extract_with_pypdf2),
    ]
    
    last_error = None
    for method_name, extract_func in extraction_methods:
        try:
            result = extract_func(file_data, file_name)
            
            # Validar qualidade da extração
            extracted_text = result.get("text", "")
            if not extracted_text or len(extracted_text.strip()) < 10:
                logger.warning(f"⚠️ {method_name} retornou texto vazio ou muito curto")
                # Tentar próximo método se não for o último
                if method_name != extraction_methods[-1][0]:
                    last_error = ValueError("Texto extraído vazio ou muito curto")
                    continue
            
            # Validar número de páginas
            total_pages = result.get("total_pages", 0)
            if total_pages == 0:
                logger.warning(f"⚠️ {method_name} não extraiu páginas")
                if method_name != extraction_methods[-1][0]:
                    last_error = ValueError("Nenhuma página extraída")
                    continue
            
            logger.info(f"✅ Extração bem-sucedida com {method_name} ({total_pages} páginas, {len(extracted_text)} caracteres)")
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ {method_name} falhou: {e}")
            last_error = e
            continue
    
    # Se todas as tentativas falharam
    logger.error("❌ Todas as tentativas de extração falharam")
    raise Exception(f"Falha na extração: {last_error}")

