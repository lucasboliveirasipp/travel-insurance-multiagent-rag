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
from pathlib import Path

# Configurar path para imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from PyPDF2 import PdfReader
import pandas as pd
import docx
from langchain_text_splitters import TokenTextSplitter, CharacterTextSplitter
from langchain_community.document_loaders import UnstructuredExcelLoader
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_openai import AzureOpenAIEmbeddings
from openpyxl import load_workbook
import openai
from tqdm import tqdm
import time
import requests
import json
from glob import glob
from typing import List

from config import (
    AZURE_EMBEDDINGS_ENDPOINT,
    AZURE_EMBEDDINGS_KEY,
    AZURE_EMBEDDINGS_DEPLOYMENT,
    AZURE_EMBEDDINGS_API_VERSION,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_KEY
)

# Configurar variaveis de ambiente para compatibilidade
os.environ["OPENAI_API_KEY"] = AZURE_OPENAI_KEY
os.environ["AZURE_OPENAI_ENDPOINT"] = AZURE_OPENAI_ENDPOINT


def create_index_v2(index_name: str, semantic_name: str, columns: list):
    """
    Cria um índice no serviço Azure Cognitive Search.

    Args:
        index_name (str): O nome do índice a ser criado.
        semantic_name (str): O nome semântico do índice.
        columns (list): Uma lista de dicionários contendo as informações das colunas a serem criadas.

    Returns:
        dict: Um dicionário contendo o template da requisição de criação do índice.

    """
    relative_path = os.path.join("template_index.json")
    base_dir = os.path.dirname(os.path.abspath(__file__))  # Diretório do script
    file_path = os.path.join(base_dir, relative_path)

    with open(file_path, "r") as file:
        createIndexTemplate = json.load(file)

    createIndexTemplate["name"] = index_name
    createIndexTemplate["semantic"]["configurations"][0]["name"] = semantic_name

    createIndexTemplate["fields"].extend(
        [
            {
                "name": "content",
                "type": "Edm.String",
                "searchable": True,
                "retrievable": True,
                "analyzer": "pt-Br.lucene",
            },
            {
                "name": "contentVector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "retrievable": True,
                "dimensions": 1536,
                "vectorSearchProfile": "vector-profile-1700855443968",
            },
        ]
    )

    for column in columns:
        createIndexTemplate["fields"].append(column)

    headers = {
        "Content-Type": "application/json",
        "api-key": os.getenv("AZURE_OPENAI_API_KEY", ""),
    }

    response = requests.put(
        f"{os.getenv('AZURE_SEARCH_ENDPOINT', '').rstrip('/')}/indexes/{index_name}?api-version=2023-10-01-Preview&allowIndexDowntime=true",
        headers=headers,
        json=createIndexTemplate,
    )
    print(response.json())

    return createIndexTemplate


def chunk_embedding(text):
    """Retorna a incorporação (embedding) de um texto utilizando a API de Embedding da OpenAI.

    Args:
        text (str): O texto a ser incorporado.

    Returns:
        embeddings (list): Uma lista contendo a incorporação do texto.

    Raises:
        Exception: Caso ocorra algum erro na solicitação da API.

    Example:
        >>> text = "Este é um exemplo de texto."
        >>> chunk_embedding(text)
        [0.1234, 0.5678, 0.9012, ...]
    """

    embedding: AzureOpenAIEmbeddings = AzureOpenAIEmbeddings(
        azure_deployment=AZURE_EMBEDDINGS_DEPLOYMENT,
        azure_endpoint=AZURE_EMBEDDINGS_ENDPOINT,
        api_version=AZURE_EMBEDDINGS_API_VERSION,
        api_key=AZURE_EMBEDDINGS_KEY,
    )

    return embedding.embed_documents([text])[0]


def create_index(index_name: str, semantic_name: str, personalize_cols=[]):
    """
    Cria um índice no serviço Azure Cognitive Search.

    Args:
        index_name (str): O nome do índice a ser criado.
        semantic_name (str): O nome semântico do índice.

    Returns:
        dict: Um dicionário contendo a o template da requisição de criação do índice.

    """
    relative_path = os.path.join("template_index.json")
    base_dir = os.path.dirname(os.path.abspath(__file__))  # Diretório do script
    file_path = os.path.join(base_dir, relative_path)

    with open(file_path, "r") as file:
        createIndexTemplate = json.load(file)

    createIndexTemplate["name"] = index_name
    createIndexTemplate["semantic"]["configurations"][0]["name"] = semantic_name

    if len(personalize_cols) > 1:
        for col in personalize_cols:
            createIndexTemplate["fields"].extend(
                [
                    {
                        "name": col,
                        "type": "Edm.String",
                        "searchable": True,
                        "retrievable": True,
                        "analyzer": "pt-Br.lucene",
                    },
                    {
                        "name": f"{col}Vector",
                        "type": "Collection(Edm.Single)",
                        "searchable": True,
                        "retrievable": True,
                        "dimensions": 1536,
                        "vectorSearchProfile": "vector-profile-1700855443968",
                    },
                ]
            )
    else:
        createIndexTemplate["fields"].extend(
            [
                {
                    "name": "content",
                    "type": "Edm.String",
                    "searchable": True,
                    "retrievable": True,
                    "analyzer": "pt-Br.lucene",
                },
                {
                    "name": "contentVector",
                    "type": "Collection(Edm.Single)",
                    "searchable": True,
                    "retrievable": True,
                    "dimensions": 1536,
                    "vectorSearchProfile": "vector-profile-1700855443968",
                },
            ]
        )

    createIndexTemplate["fields"].extend(
        [
            {
                "name": "filepathField",
                "type": "Edm.String",
                "searchable": True,
                "retrievable": True,
            }
        ]
    )

    headers = {
        "Content-Type": "application/json",
        "api-key": os.getenv("AZURE_OPENAI_API_KEY", ""),
    }

    response = requests.put(
        f"{os.getenv('AZURE_SEARCH_ENDPOINT', '').rstrip('/')}/indexes/{index_name}?api-version=2023-10-01-Preview&allowIndexDowntime=true",
        headers=headers,
        json=createIndexTemplate,
    )
    print(response.json())

    return createIndexTemplate


def uploadToIndex(index, template):
    headers = {
        "Content-Type": "application/json",
        "api-key": os.getenv("AZURE_OPENAI_API_KEY", ""),
    }

    print("Indexando documentos...")
    try:
        response = requests.post(
            url=f"{os.getenv('AZURE_SEARCH_ENDPOINT', '').rstrip('/')}/indexes/{index}/docs/index?api-version=2023-10-01-Preview",
            headers=headers,
            json=template,
        )
        print(response.json())
    except Exception as e:
        print(e)


def vectorize_and_upload(dataframe: pd.DataFrame, index: str):
    """Vetoriza e faz o upload dos documentos em um índice de pesquisa.

    Args:
        dataframe (pd.DataFrame): DataFrame contendo os dados dos documentos.
        index (str): Nome do índice de pesquisa.

    Returns:
        dict: template dos dados que foram indexados - print da Resposta da API de indexação.

    """
    template = {"value": []}
    batch_count = 0

    print("Vetorizando documentos...")
    for i in tqdm(range(len(dataframe))):
        template["value"].append(
            {
                "id": str(i),
                "content": str(dataframe.loc[i, "text"]),
                "contentVector": chunk_embedding(dataframe.loc[i, "text"]),
                "filepathField": dataframe.loc[i, "file"],
            }
        )
        batch_count += 1
        time.sleep(1.0)
        if batch_count >= 100:
            uploadToIndex(index, template)
            batch_count = 0
            template = {"value": []}

    uploadToIndex(index, template)

    return template


def split_text(text: str, tokenChunks: int, overlapPercentage: float) -> List[str]:
    # Calcula o tamanho de sobreposição em número de tokens
    overlapSize = round(tokenChunks * overlapPercentage)
    text_length = len(text)
    res = []

    # Inicializa o índice inicial para a catação do texto
    start = 0

    while start < text_length:
        # Define o final do chunk
        end = start + tokenChunks

        # Aplica a lógica de slice no texto
        chunk = text[start:end]
        res.append(chunk)

        # Atualiza o índice inicial para o próximo chunk, garantindo sobreposição
        start += tokenChunks - overlapSize

        # Se o final do chunk ultrapassar o tamanho do texto, sai do loop
        if end >= text_length:
            break

    return res


def extract_and_split_docs_v2(
    filesPath: str, indexName: str, *, tokenChunks: int, overlapPercentage: float = 0.1
) -> List[dict]:
    """
    Extrai textos de arquivos PDFs e .xlsx e os divide em partes.

    Argumentos:
        filesPath (str): O caminho para os arquivos PDFs e .xlsx.
        indexName (str): Nome do índice para criação.
        tokenChunks (int): Tamanho desejado de cada pedaço de texto, em número de tokens.
        overlapPercentage (float): Porcentagem de overlap entre os chunks.

    Retorna:
        List[dict]: Lista de dicionários com os textos divididos e metadados.
    """
    chunks = []
    documentos_processados = 0

    # Verifica se é diretório ou arquivo
    if os.path.isdir(filesPath):
        files = [os.path.join(filesPath, f) for f in os.listdir(filesPath)]
    else:
        files = [filesPath]

    for file in files:
        if file.lower().endswith(".pdf") and os.path.isfile(file):
            try:
                reader = PdfReader(file)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if not text:
                        continue
                    texts = split_text(text, tokenChunks, overlapPercentage)
                    for chunk in texts:
                        chunks.append(
                            {
                                "filepathField": os.path.basename(file),
                                "pagina": f"Pagina {i+1}",
                                "content": chunk,
                            }
                        )
                documentos_processados += 1
            except Exception as e:
                print(f"Erro ao processar {file}: {e}")

        elif file.lower().endswith(".txt") and os.path.isfile(file):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    text = f.read()
                if not text.strip():
                    continue
                texts = split_text(text, tokenChunks, overlapPercentage)
                for chunk in texts:
                    chunks.append(
                        {"filepathField": os.path.basename(file), "content": chunk}
                    )
                documentos_processados += 1
            except Exception as e:
                print(f"Erro ao processar {file}: {e}")

        # elif file.lower().endswith(".xlsx"):
        #     loader = ExcelLoader(file)
        #     data = loader.load_and_split()
        #     for chunk in data:
        #         chunks.append({
        #             "filepathField": os.path.basename(file),
        #             "content": chunk
        #         })
        #     documentos_processados += 1

    # Define colunas para o índice
    columns = []
    for chunk in chunks:
        for key in chunk.keys():
            if key == "content":
                continue
            columns.append(
                {
                    "name": key,
                    "type": "Edm.String",
                    "searchable": True,
                    "retrievable": True,
                }
            )
        break  # Apenas uma vez

    print(columns)
    create_index_v2(indexName + "-index", "semantic-" + indexName, columns)

    return chunks


def vectorize_and_upload_v2(chunks, index):
    """
    Vetoriza e envia documentos para o VectorDB para indexação.

    Args:
        chunks (list or dict): Lista de trechos de texto a serem vetorizados ou dicionário com campo 'content'.
        index (str): Nome do índice no VectorDB para onde os documentos serão enviados.

    Returns:
        dict: Resposta da requisição de envio para o VectorDB em formato JSON.
    """
    index_name = f"{index}-index"

    template = {"value": []}

    print("Vetorizando documentos...")
    batch_count = 0
    if isinstance(chunks, list) and all(
        isinstance(item, dict) and "content" in item for item in chunks
    ):
        for i, chunk in tqdm(enumerate(chunks)):
            document = {
                "id": str(i),
                "content": str(chunk["content"]),
                "contentVector": chunk_embedding(chunk["content"]),
            }
            for key, value in chunk.items():
                if key != "content":
                    document[key] = str(value)
            template["value"].append(document)
            batch_count += 1
            time.sleep(0.6)
            if batch_count >= 10:
                uploadToIndex(index_name, template)
                batch_count = 0
                template = {"value": []}

    elif isinstance(chunks, list):
        for i in tqdm(range(len(chunks))):
            template["value"].append(
                {
                    "id": str(i),
                    "content": str(chunks[i]),
                    "contentVector": chunk_embedding(chunks[i]),
                }
            )
            batch_count += 1
            time.sleep(0.3)
            if batch_count >= 100:
                uploadToIndex(index_name, template)
                batch_count = 0
                template = {"value": []}
    else:
        raise ValueError(
            "O argumento 'chunks' deve ser uma lista ou um dicionário com campo 'content'."
        )

    headers = {
        "Content-Type": "application/json",
        "api-key": os.getenv("AZURE_OPENAI_API_KEY", ""),
    }

    print("Indexando documentos...")
    response = requests.post(
        url=f"{os.getenv('AZURE_SEARCH_ENDPOINT', '').rstrip('/')}/indexes/{index_name}/docs/index?api-version=2023-11-01",
        headers=headers,
        json=template,
    )

    return response.json()


def extract_and_split_docs(filesPath: str, tokenChunks: int):
    """
    Extrai e divide os documentos em pedaços de tokens.

    Parâmetros:
    - filesPath: str - O caminho do diretório onde os arquivos estão localizados.
    - tokenChunks: int - O número de tokens em cada pedaço.

    Retorna:
    - df: DataFrame - Um DataFrame contendo os pedaços de texto extraídos dos documentos.

    """
    documentos_processados = 0
    df = pd.DataFrame(columns=["text", "file"])

    # PDFS
    pdfPath = glob(f"{filesPath}*pdf")
    # output = ''

    for file in pdfPath:
        reader = PdfReader(file)
        count = len(reader.pages)
        for i in range(count):
            page = reader.pages[i]
            # output += page.extract_text()
            df = df.append(
                {"text": page.extract_text(), "file": file + f" Page: {i}"},
                ignore_index=True,
            )
            documentos_processados += 1

    # DOCX
    docsPath = glob(f"{filesPath}*docx")
    if len(docsPath) > 0:
        for doc in len(docsPath):
            try:
                file = docx.Document(docsPath[doc])
                # output += '\n'.join([p.text for p in file.paragraphs])
                df = df.append(
                    {
                        "text": "\n".join([p.text for p in file.paragraphs]),
                        "file": docsPath[doc] + f" Page: {doc}",
                    },
                    ignore_index=True,
                )
                documentos_processados += 1
            except:
                print("* Falha no documento. *")

    # XLSX
    xlsxPath = glob(f"{filesPath}*xlsx")
    if len(xlsxPath) > 0:
        for xlsx in xlsxPath:
            try:
                file = pd.read_excel(xlsx)
                for index, _ in file.iterrows():
                    df = df.append(
                        {
                            "text": " ".join(file.iloc[index].to_string().split())
                            + "\n\n",
                            "file": xlsx,
                        },
                        ignore_index=True,
                    )
                documentos_processados += 1
            except:
                print("falha em carregar o doc")

    print(
        f"Documentos processados: {documentos_processados} de {len(pdfPath)+len(docsPath)+len(xlsxPath)}"
    )
    text_splitter = TokenTextSplitter(
        chunk_size=tokenChunks, chunk_overlap=round(tokenChunks / 10)
    )

    df["text"] = (
        df["text"]
        .reset_index(drop=True)
        .apply(lambda x: text_splitter.split_text(str(x)))
    )
    df = df.explode("text")

    return df


def delete_index():
    headers = {
        "Content-Type": "application/json",
        "api-key": os.getenv("AZURE_OPENAI_API_KEY", ""),
    }

    response = requests.delete(
        f"{os.getenv('AZURE_SEARCH_ENDPOINT', '').rstrip('/')}/indexes/teste-apagar-index?api-version=2023-10-01-Preview",
        headers=headers,
    )


# NOTA: Para indexar documentos, use o script:
# python scripts/index_documents.py --directory "base de dados para indexar/"
#
# Exemplo de uso direto (se necessário):
# if __name__ == "__main__":
#     chunks = extract_and_split_docs_v2(
#         "base de dados para indexar/",
#         indexName="book-parcerias",
#         tokenChunks=1024,
#         overlapPercentage=0.2,
#     )
#     template = vectorize_and_upload_v2(chunks, "book-parcerias")
