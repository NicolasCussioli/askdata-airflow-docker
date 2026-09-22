"""Dia 7: PDF/Markdown -> chunks com origem -> Gemini -> Chroma local.

Use --dry-run para extrair sem chave, API ou banco vetorial.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
EMBEDDING_MODEL = 'gemini-embedding-001'
EMBEDDING_DIMENSION = 3072
COLLECTION_NAME = 'askdata_knowledge'


def extrair_texto_pdf(caminho_pdf):
    """Mantém o número original da página, começando em 1."""
    from pypdf import PdfReader
    caminho = Path(caminho_pdf)
    paginas = []
    for numero, pagina in enumerate(PdfReader(caminho).pages, 1):
        texto = (pagina.extract_text() or '').strip()
        if not texto:
            raise ValueError(f'{caminho.name}, página {numero}: sem texto; revisar OCR.')
        paginas.append({'texto': texto, 'arquivo': caminho.name, 'pagina': numero})
    return paginas


def extrair_texto_markdown(caminho_md):
    """Markdown não tem paginação física; página 1 é uma convenção."""
    caminho = Path(caminho_md)
    texto = caminho.read_text(encoding='utf-8').strip()
    if not texto:
        raise ValueError(f'{caminho.name}: documento vazio.')
    return [{'texto': texto, 'arquivo': caminho.name, 'pagina': 1}]


def carregar_documentos(pasta):
    arquivos = sorted(p for p in Path(pasta).glob('*')
                      if p.suffix.lower() in ('.pdf', '.md') and p.is_file())
    if not arquivos:
        raise ValueError('Nenhum PDF ou Markdown encontrado na pasta de dados.')
    paginas = []
    for arquivo in arquivos:
        extrair = extrair_texto_pdf if arquivo.suffix.lower() == '.pdf' else extrair_texto_markdown
        paginas.extend(extrair(arquivo))
    return paginas


def criar_chunks(documentos_paginas, chunk_size=700, chunk_overlap=100):
    """Corta por caracteres dentro de cada página, sem uma cauda redundante."""
    if chunk_size <= 0 or not 0 <= chunk_overlap < chunk_size:
        raise ValueError('Use tamanho > 0 e 0 <= sobreposição < tamanho.')
    chunks = []
    for item in documentos_paginas:
        texto = item['texto']
        if not texto.strip():
            continue
        inicio, indice = 0, 1
        while inicio < len(texto):
            fim = min(inicio + chunk_size, len(texto))
            trecho = texto[inicio:fim]
            if trecho.strip():
                chunks.append({
                    'id': f"{item['arquivo']}_p{item['pagina']}_c{indice}",
                    'texto': trecho, 'arquivo': item['arquivo'],
                    'pagina': item['pagina'], 'chunk_idx': indice,
                    'inicio': inicio, 'fim': fim,
                })
            if fim == len(texto):
                break
            inicio += chunk_size - chunk_overlap
            indice += 1
    return chunks


def contrato_indice(chunks, chunk_size, chunk_overlap):
    """Impede misturar corpus, modelos ou parâmetros em uma mesma coleção."""
    assinatura = hashlib.sha256(json.dumps(chunks, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return {
        'corpus_sha256': assinatura, 'embedding_model': EMBEDDING_MODEL,
        'embedding_dimension': EMBEDDING_DIMENSION, 'task_type': 'RETRIEVAL_DOCUMENT',
        'chunk_size': chunk_size, 'chunk_overlap': chunk_overlap,
        'expected_chunks': len(chunks), 'schema_version': 1,
    }


def cliente_chroma(path_db):
    import chromadb
    from chromadb.config import Settings
    return chromadb.PersistentClient(path=str(path_db), settings=Settings(anonymized_telemetry=False))


def criar_gerador_embeddings():
    from dotenv import load_dotenv
    from google import genai
    from google.genai import errors, types
    load_dotenv(ROOT / '.env', override=False)
    chave = os.getenv('GEMINI_API_KEY', '').strip()
    if not chave:
        raise ValueError('GEMINI_API_KEY ausente. Preencha a .env local ou use --dry-run.')
    if os.getenv('EMBEDDING_MODEL', EMBEDDING_MODEL) != EMBEDDING_MODEL:
        raise ValueError('EMBEDDING_MODEL deve ser gemini-embedding-001 neste projeto.')
    client = genai.Client(api_key=chave, http_options=types.HttpOptions(timeout=60000))

    def gerar(textos):
        # Nunca imprimir mensagens brutas do SDK, que podem incluir detalhes sensíveis.
        for tentativa in range(3):
            try:
                resposta = client.models.embed_content(
                    model=EMBEDDING_MODEL, contents=textos,
                    config=types.EmbedContentConfig(
                        task_type='RETRIEVAL_DOCUMENT', output_dimensionality=EMBEDDING_DIMENSION),
                )
                return [embedding.values for embedding in (resposta.embeddings or [])]
            except errors.APIError as exc:
                if exc.code in (429, 500, 502, 503, 504) and tentativa < 2:
                    espera = 20 * (tentativa + 1)
                    print(f'API HTTP {int(exc.code)}; nova tentativa em {espera}s.', flush=True)
                    time.sleep(espera)
                    continue
                codigo = str(exc.code) if isinstance(exc.code, int) else 'indisponível'
                raise RuntimeError(f'API de embeddings: HTTP {codigo}. Confira chave, cota e rede; '
                                   'execute novamente para retomar os lotes salvos.') from None
            except Exception:
                raise RuntimeError('Falha na chamada de embeddings. Confira a conexão e tente novamente.') from None
    return client, gerar


def indexar_no_chromadb(chunks, gerar_embeddings, path_db=ROOT / 'chroma_db',
                       collection_name=COLLECTION_NAME, chunk_size=700, chunk_overlap=100,
                       batch_size=16, batch_delay=12):
    """Grava por lotes e retoma uma execução interrompida sem repetir lotes salvos."""
    if not chunks or batch_size <= 0 or batch_delay < 0:
        raise ValueError('A indexação exige chunks, lote positivo e intervalo não negativo.')
    contrato = contrato_indice(chunks, chunk_size, chunk_overlap)
    client = cliente_chroma(path_db)
    collection = client.get_or_create_collection(
        name=collection_name, embedding_function=None,
        metadata={**contrato, 'index_complete': False},
        configuration={'hnsw': {'space': 'cosine'}},
    )
    if any((collection.metadata or {}).get(k) != v for k, v in contrato.items()):
        raise ValueError('A coleção pertence a outro corpus/configuração. Use --collection com '
                         'um nome novo para reconstruir sem apagar o índice anterior.')
    ids_atuais = set(collection.get(include=[])['ids'])
    ids_esperados = {chunk['id'] for chunk in chunks}
    if len(ids_esperados) != len(chunks) or not ids_atuais <= ids_esperados:
        raise ValueError('IDs duplicados ou inesperados; confira os documentos e a coleção.')
    pendentes = [chunk for chunk in chunks if chunk['id'] not in ids_atuais]
    collection.modify(metadata={**contrato, 'index_complete': False})
    print(f'Já salvos: {len(ids_atuais)}; pendentes: {len(pendentes)}.')
    for inicio in range(0, len(pendentes), batch_size):
        if inicio:
            time.sleep(batch_delay)
        lote = pendentes[inicio:inicio + batch_size]
        vetores = gerar_embeddings([chunk['texto'] for chunk in lote])
        if len(vetores) != len(lote) or any(
            vetor is None or len(vetor) != EMBEDDING_DIMENSION
            or not all(math.isfinite(v) for v in vetor) or not any(vetor)
            for vetor in vetores
        ):
            raise ValueError('Resposta de embeddings inválida; o lote não foi salvo.')
        collection.upsert(
            ids=[chunk['id'] for chunk in lote], embeddings=vetores,
            documents=[chunk['texto'] for chunk in lote],
            metadatas=[{k: v for k, v in chunk.items() if k not in ('id', 'texto')} for chunk in lote],
        )
        print(f'Salvos: {collection.count()}/{len(chunks)} chunks.', flush=True)
    if collection.count() != len(chunks):
        raise ValueError('Contagem final diverge do esperado; execute a auditoria.')
    collection.modify(metadata={**contrato, 'index_complete': True})
    return collection.count()


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Não chama API nem abre Chroma.')
    parser.add_argument('--chunk-size', type=int, default=700)
    parser.add_argument('--chunk-overlap', type=int, default=100)
    parser.add_argument('--collection', default=COLLECTION_NAME)
    args = parser.parse_args()
    client = None
    try:
        paginas = carregar_documentos(ROOT / 'data')
        chunks = criar_chunks(paginas, args.chunk_size, args.chunk_overlap)
        print(f'{len({p["arquivo"] for p in paginas})} arquivos; {len(paginas)} páginas/unidades; {len(chunks)} chunks.')
        if args.dry_run:
            print('Prévia offline concluída. Nenhum embedding gerado e nenhum banco alterado.')
            return 0
        client, gerar = criar_gerador_embeddings()
        indexar_no_chromadb(chunks, gerar, collection_name=args.collection,
                           chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
        print('Indexação concluída. Execute inspecionar_chunks.py para auditar.')
        return 0
    except (ValueError, RuntimeError) as exc:
        print(f'FALHA: {exc}')
        return 1
    except Exception as exc:
        print(f'FALHA de leitura/persistência ({type(exc).__name__}). Confira arquivos e permissões.')
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == '__main__':
    sys.exit(main())
