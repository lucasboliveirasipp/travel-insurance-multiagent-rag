# Carrega variáveis do arquivo .env mais próximo (pasta do projeto)
def _carregar_env():
    from pathlib import Path
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for pasta in Path(__file__).resolve().parents:
        if (pasta / ".env").exists():
            load_dotenv(pasta / ".env")
            break


_carregar_env()

import os
import sys
import time
from glob import glob
from uuid import uuid4

# Configurar proxy corporativo
proxy_host = os.getenv("HTTP_PROXY_HOST", "")
proxy_port = os.getenv("HTTP_PROXY_PORT", "80")
if proxy_host:  # proxy opcional (defina HTTP_PROXY_HOST no .env)
    os.environ['HTTP_PROXY'] = f'http://{proxy_host}:{proxy_port}'
if proxy_host:  # proxy opcional (defina HTTP_PROXY_HOST no .env)
    os.environ['HTTPS_PROXY'] = f'http://{proxy_host}:{proxy_port}'

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import Docx2txtLoader
from langchain_openai import AzureOpenAIEmbeddings
import requests

# Importações opcionais
try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    DOC_INTELLIGENCE_AVAILABLE = True
except ImportError:
    DOC_INTELLIGENCE_AVAILABLE = False
    print("⚠️ Azure Document Intelligence não disponível")

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    print("⚠️ PyPDF2 não disponível")

# ============================================================================
# CONFIGURAÇÕES AZURE - Hardcoded
# ============================================================================

# Azure AI Search
AZURE_AI_SEARCH_ENDPOINT = os.getenv("AZURE_AI_SEARCH_ENDPOINT", "")
AZURE_AI_SEARCH_KEY = os.getenv("AZURE_AI_SEARCH_KEY", "")
AZURE_AI_SEARCH_INDEX_NAME = "book-parcerias-index"

# Azure Embeddings - TEMPORÁRIO até 04/02/2026
AZURE_EMBEDDINGS_ENDPOINT = os.getenv("AZURE_EMBEDDINGS_ENDPOINT", "")
AZURE_EMBEDDINGS_KEY = os.getenv("AZURE_EMBEDDINGS_KEY", "")
AZURE_EMBEDDINGS_DEPLOYMENT = "text-embedding-ada-002"
AZURE_EMBEDDINGS_API_VERSION = "2023-05-15"

# Azure Document Intelligence - Para processamento avançado de PDFs
AZURE_DOC_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOC_INTELLIGENCE_ENDPOINT", "")
AZURE_DOC_INTELLIGENCE_KEY = os.getenv("AZURE_DOC_INTELLIGENCE_KEY", "")

# Inicializar embeddings
try:
    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=AZURE_EMBEDDINGS_DEPLOYMENT,
        azure_endpoint=AZURE_EMBEDDINGS_ENDPOINT,
        api_version=AZURE_EMBEDDINGS_API_VERSION,
        api_key=AZURE_EMBEDDINGS_KEY
    )
    print(f"✅ Embeddings configurados: {AZURE_EMBEDDINGS_DEPLOYMENT}")
except Exception as e:
    print(f"❌ Erro ao configurar embeddings: {e}")
    sys.exit(1)

# 2. Variáveis
PASTA_ARQUIVOS = "./data/"
INDEX_NAME = AZURE_AI_SEARCH_INDEX_NAME

# 3. Funções de leitura
def read_pdf_with_pypdf2(file_path: str) -> str:
    """
    Lê PDF usando PyPDF2 (método básico).
    Usado como fallback quando Azure Document Intelligence não está disponível.
    """
    if not PYPDF2_AVAILABLE:
        return ""
    
    try:
        reader = PdfReader(file_path)
        texto_completo = []
        
        for i, page in enumerate(reader.pages):
            texto = page.extract_text()
            if texto and texto.strip():
                texto_completo.append(f"\n--- Página {i+1} ---\n{texto}")
        
        resultado = "\n".join(texto_completo)
        print(f"   ✅ Extraído com PyPDF2: {len(resultado)} caracteres")
        return resultado
    except Exception as e:
        print(f"   ⚠️ Erro ao ler PDF com PyPDF2 ({os.path.basename(file_path)}): {e}")
        return ""

def get_markdown_with_azure(file_path: str) -> str:
    """
    Usa a IA da Azure para ler o PDF.
    Ideal para PDFs que vieram de PPTs, pois preserva a estrutura visual (tabelas, colunas).
    Se não disponível, usa PyPDF2 como fallback.
    """
    # Tentar Azure Document Intelligence primeiro
    if DOC_INTELLIGENCE_AVAILABLE and AZURE_DOC_INTELLIGENCE_ENDPOINT and AZURE_DOC_INTELLIGENCE_KEY:
        try:
            client = DocumentIntelligenceClient(
                endpoint=AZURE_DOC_INTELLIGENCE_ENDPOINT,
                credential=AzureKeyCredential(AZURE_DOC_INTELLIGENCE_KEY)
            )
            with open(file_path, "rb") as f:
                poller = client.begin_analyze_document(
                    "prebuilt-layout",
                    body=f,
                    output_content_format="markdown"
                )
                result = poller.result()
            print(f"   ✅ Extraído com Azure Document Intelligence")
            return result.content
        except Exception as e:
            print(f"   ⚠️ Erro no Azure Document Intelligence: {e}")
            print(f"   🔄 Tentando fallback com PyPDF2...")
    
    # Fallback para PyPDF2
    if not DOC_INTELLIGENCE_AVAILABLE or not AZURE_DOC_INTELLIGENCE_ENDPOINT:
        print(f"   ℹ️ Azure Document Intelligence não configurado, usando PyPDF2...")
    
    return read_pdf_with_pypdf2(file_path)

def read_word_file(file_path: str) -> str:
    """Lê arquivos Word simples."""
    try:
        loader = Docx2txtLoader(file_path)
        docs = loader.load()
        return "\n".join([d.page_content for d in docs])
    except Exception as e:
        print(f"⚠️ Erro ao ler Word ({os.path.basename(file_path)}): {e}")
        return ""

def upload_documents_to_index(documents: list, index_name: str) -> bool:
    """
    Envia documentos diretamente para o índice usando API REST.
    Usa apenas campos que existem no schema: id, content, contentVector, filepathField.
    """
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_AI_SEARCH_KEY,
    }
    
    url = f"{AZURE_AI_SEARCH_ENDPOINT}/indexes/{index_name}/docs/index?api-version=2023-11-01"
    
    payload = {"value": documents}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code in [200, 201]:
            return True
        else:
            print(f"   ❌ Erro na API: {response.status_code} - {response.text[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ Erro ao enviar: {e}")
        return False


# 4. Função Principal
def ingest_files():
    print(f"🚀 Iniciando ingestão no índice: {INDEX_NAME}")

    if not os.path.exists(PASTA_ARQUIVOS):
        print(f"🔴 Pasta '{PASTA_ARQUIVOS}' não encontrada. Crie a pasta e coloque os arquivos.")
        return

    # Busca apenas .pdf e .docx (já que os pptx viraram pdf)
    arquivos = glob(os.path.join(PASTA_ARQUIVOS, "*.pdf")) + \
               glob(os.path.join(PASTA_ARQUIVOS, "*.docx"))
    
    print(f"\n📦 Total de arquivos encontrados: {len(arquivos)}")

    if len(arquivos) == 0:
        print("⚠️ Nenhum arquivo encontrado. Coloque os PDFs na pasta 'data'.")
        return

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=4000,
        chunk_overlap=400
    )

    doc_id_counter = 0

    for i, caminho in enumerate(arquivos):
        nome = os.path.basename(caminho)
        print(f"\n[{i+1}/{len(arquivos)}] 📄 Processando: {nome}")

        texto = ""
        # Roteamento simples: PDF vai pra Azure, DOCX vai pro loader local
        if nome.endswith(".pdf"):
            texto = get_markdown_with_azure(caminho)
        elif nome.endswith(".docx"):
            texto = read_word_file(caminho)

        if not texto:
            print(f"⚠️ Pulei {nome} (Texto vazio ou erro).")
            continue

        chunks = text_splitter.split_text(texto)
        print(f"   ✂️ Gerou {len(chunks)} partes. Gerando embeddings e enviando...")

        # Preparar documentos com apenas os campos que existem no índice
        batch = []
        batch_size = 10  # Reduzido para evitar timeout
        
        for chunk_idx, chunk_text in enumerate(chunks):
            # Gerar embedding para o chunk
            try:
                embedding = embeddings.embed_query(chunk_text)
            except Exception as e:
                print(f"   ⚠️ Erro ao gerar embedding para chunk {chunk_idx}: {e}")
                continue
            
            # Criar documento usando APENAS campos do schema
            doc = {
                "id": str(doc_id_counter),
                "content": chunk_text,
                "contentVector": embedding,
                "filepathField": nome
            }
            
            batch.append(doc)
            doc_id_counter += 1
            
            # Enviar batch quando atingir o tamanho ou for o último chunk
            if len(batch) >= batch_size or chunk_idx == len(chunks) - 1:
                if upload_documents_to_index(batch, INDEX_NAME):
                    print(f"   📤 Lote de {len(batch)} documento(s) enviado.")
                batch = []
                time.sleep(0.5)

    print("\n🏁 Ingestão finalizada com sucesso!")

if __name__ == "__main__":
    ingest_files()