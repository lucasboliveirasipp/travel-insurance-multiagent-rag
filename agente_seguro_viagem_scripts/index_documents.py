"""Script para indexação prévia de documentos.

Este script deve ser executado uma vez para indexar todos os documentos
antes de usar o sistema. A indexação não deve ser feita durante a execução
do pipeline para evitar latência desnecessária.

Uso:
    python scripts/index_documents.py                              # Indexar pasta files/
    python scripts/index_documents.py --directory "pasta/"         # Indexar diretório específico
    python scripts/index_documents.py --file book.pdf              # Indexar arquivo específico
    python scripts/index_documents.py --delete                     # Deletar índice padrão (config.py)
    python scripts/index_documents.py --delete nome-do-indice      # Deletar índice específico
    
Reindexação completa:
    python scripts/index_documents.py --delete && python scripts/index_documents.py --directory "base de dados para indexar/"
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Configurar path para imports
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from config import FILES_DIR, AZURE_AI_SEARCH_INDEX_NAME
from agente_seguro_viagem_utils.vector_store import index_pdf_pages
from agente_seguro_viagem_utils.pdf_extractor import extract_pdf
from agente_seguro_viagem_utils.indexing_service import index_documents_from_directory, delete_index

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def index_single_file(file_path: str) -> bool:
    """Indexa um único arquivo PDF.
    
    Args:
        file_path: Caminho para o arquivo PDF
        
    Returns:
        True se indexado com sucesso
    """
    logger.info("=" * 60)
    logger.info(f"INDEXANDO ARQUIVO: {file_path}")
    logger.info("=" * 60)
    
    try:
        if not os.path.exists(file_path):
            logger.error(f"❌ Arquivo não encontrado: {file_path}")
            return False
        
        if not file_path.lower().endswith('.pdf'):
            logger.error(f"❌ Arquivo deve ser PDF: {file_path}")
            return False
        
        # Extrair PDF
        logger.info("📄 Extraindo texto do PDF...")
        extracted_data = extract_pdf(file_path=file_path)
        
        if not extracted_data or not extracted_data.get("pages"):
            logger.error("❌ Nenhuma página extraída do PDF")
            return False
        
        # Indexar páginas
        logger.info(f"📚 Indexando {len(extracted_data['pages'])} páginas...")
        indexed_count = index_pdf_pages(extracted_data)
        
        if indexed_count > 0:
            logger.info(f"✅ {indexed_count} páginas indexadas com sucesso")
            return True
        else:
            logger.error("❌ Nenhuma página foi indexada")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao indexar arquivo: {e}", exc_info=True)
        return False


def index_directory(directory_path: str, index_name: str = "book-parcerias") -> bool:
    """Indexa todos os documentos de um diretório.
    
    Args:
        directory_path: Caminho para o diretório
        index_name: Nome do índice
        
    Returns:
        True se indexação bem-sucedida
    """
    logger.info("=" * 60)
    logger.info(f"INDEXANDO DIRETÓRIO: {directory_path}")
    logger.info("=" * 60)
    
    try:
        if not os.path.exists(directory_path):
            logger.error(f"❌ Diretório não encontrado: {directory_path}")
            return False
        
        # Usar serviço de indexação em massa
        return index_documents_from_directory(
            directory_path=directory_path,
            index_name=index_name,
            token_chunks=1024,
            overlap_percentage=0.2,
            batch_size=10,
            delay_seconds=0.6
        )
        
    except Exception as e:
        logger.error(f"❌ Erro ao indexar diretório: {e}", exc_info=True)
        return False


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Indexa documentos para busca vetorial (execução prévia)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Indexar diretório padrão (files/)
  python scripts/index_documents.py
  
  # Indexar diretório específico
  python scripts/index_documents.py --directory "base de dados para indexar/"
  
  # Indexar um arquivo específico
  python scripts/index_documents.py --file book.pdf
  
  # Deletar índice padrão (definido em config.py)
  python scripts/index_documents.py --delete
  
  # Deletar índice específico
  python scripts/index_documents.py --delete meu-indice
  
  # Reindexação completa (deletar e reindexar)
  python scripts/index_documents.py --delete && python scripts/index_documents.py -d "base de dados para indexar/"
        """
    )
    
    parser.add_argument(
        "--directory",
        "-d",
        type=str,
        default=None,
        help="Diretório com documentos para indexar (padrão: files/)"
    )
    
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        default=None,
        help="Arquivo PDF específico para indexar"
    )
    
    parser.add_argument(
        "--index-name",
        "-i",
        type=str,
        default="book-parcerias",
        help="Nome do índice (padrão: book-parcerias)"
    )
    
    parser.add_argument(
        "--delete",
        "-D",
        type=str,
        nargs="?",
        const="default",
        default=None,
        help=f"Deletar índice. Sem argumento usa o padrão do config.py ({AZURE_AI_SEARCH_INDEX_NAME})"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("SCRIPT DE INDEXAÇÃO PRÉVIA")
    logger.info("=" * 60)
    logger.info("⚠️ IMPORTANTE: Execute este script ANTES de usar o sistema")
    logger.info("⚠️ A indexação durante a execução foi removida para melhor performance")
    logger.info("=" * 60)
    
    success = False
    
    # Processar deleção de índice
    if args.delete:
        if args.delete == "default":
            index_to_delete = AZURE_AI_SEARCH_INDEX_NAME
        else:
            index_to_delete = args.delete
        
        success = delete_index(index_to_delete)
        
        if success:
            logger.info(f"✅ Índice '{index_to_delete}' deletado")
        else:
            logger.error(f"❌ Falha ao deletar índice '{index_to_delete}'")
        
        return 0 if success else 1
    
    if args.file:
        # Indexar arquivo único
        success = index_single_file(args.file)
    else:
        # Indexar diretório
        directory = args.directory or FILES_DIR
        success = index_directory(directory, args.index_name)
    
    if success:
        logger.info("=" * 60)
        logger.info("✅ INDEXAÇÃO CONCLUÍDA COM SUCESSO")
        logger.info("=" * 60)
        logger.info("Agora você pode usar o sistema normalmente.")
        logger.info("Os documentos já estão indexados e prontos para busca.")
        return 0
    else:
        logger.error("=" * 60)
        logger.error("❌ INDEXAÇÃO FALHOU")
        logger.error("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

