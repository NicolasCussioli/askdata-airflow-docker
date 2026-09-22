"""Dia 7: auditoria dos chunks extraídos (--preview) ou persistidos no Chroma."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from src.ingestion import (ROOT, COLLECTION_NAME, carregar_documentos, criar_chunks,
                           cliente_chroma, contrato_indice)


def resumir_chunks(chunks):
    if not chunks:
        raise ValueError('Nenhum chunk para auditar.')
    tamanhos = [len(c['texto']) for c in chunks]
    cortes = [c for c in chunks if not c['texto'].rstrip().endswith(('.', '!', '?', ':', '"', "'", '”', '’'))]
    por_arquivo = Counter(c['arquivo'] for c in chunks)
    por_pagina = Counter((c['arquivo'], c['pagina']) for c in chunks)
    return {
        'total_chunks': len(chunks), 'menor': min(tamanhos), 'maior': max(tamanhos),
        'media': round(sum(tamanhos) / len(tamanhos), 2),
        'chunks_sem_pontuacao_final': len(cortes),
        'por_arquivo': dict(sorted(por_arquivo.items())),
        'por_pagina': [{'arquivo': a, 'pagina': p, 'chunks': n}
                       for (a, p), n in sorted(por_pagina.items())],
        'exemplos_para_revisao': [
            {'id': c['id'], 'arquivo': c['arquivo'], 'pagina': c['pagina'],
             'final': c['texto'][-100:]} for c in cortes[:3]],
    }


def auditar_colecao(collection, esperados, contrato):
    dados = collection.get(include=['documents', 'metadatas'])
    atuais = {cid: {'id': cid, 'texto': texto, **(meta or {})}
              for cid, texto, meta in zip(dados['ids'], dados['documents'], dados['metadatas'])}
    referencia = {c['id']: c for c in esperados}
    erros = []
    if any((collection.metadata or {}).get(k) != v for k, v in contrato.items()):
        erros.append('Corpus ou configuração diverge do índice.')
    if not (collection.metadata or {}).get('index_complete'):
        erros.append('Indexação ainda incompleta.')
    faltantes = set(referencia) - set(atuais)
    extras = set(atuais) - set(referencia)
    divergentes = [cid for cid in set(atuais) & set(referencia) if atuais[cid] != referencia[cid]]
    if faltantes or extras or divergentes:
        erros.append(f'Chunks faltantes: {len(faltantes)}; extras: {len(extras)}; divergentes: {len(divergentes)}.')
    return [atuais[cid] for cid in sorted(atuais)], erros


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='store_true', help='Audita a extração sem banco nem API.')
    parser.add_argument('--collection', default=COLLECTION_NAME)
    parser.add_argument('--chunk-size', type=int, default=700)
    parser.add_argument('--chunk-overlap', type=int, default=100)
    parser.add_argument('--report', type=Path, help='Salva o diagnóstico em JSON.')
    args = parser.parse_args()
    try:
        paginas = carregar_documentos(ROOT / 'data')
        esperados = criar_chunks(paginas, args.chunk_size, args.chunk_overlap)
        chunks, erros = esperados, []
        if not args.preview:
            if not (ROOT / 'chroma_db' / 'chroma.sqlite3').exists():
                raise ValueError('Banco ausente. Execute a ingestão ou use --preview.')
            client = cliente_chroma(ROOT / 'chroma_db')
            from chromadb.errors import NotFoundError
            try:
                collection = client.get_collection(args.collection, embedding_function=None)
            except NotFoundError:
                raise ValueError('Coleção ausente. Execute a ingestão ou use --preview.') from None
            chunks, erros = auditar_colecao(
                collection, esperados, contrato_indice(esperados, args.chunk_size, args.chunk_overlap))
        # Se o índice divergir, não assumir que seus metadados ainda têm o formato esperado.
        report = {'modo': 'preview_offline' if args.preview else 'chroma_persistido',
                  'api_testada_nesta_auditoria': False, 'erros': erros,
                  'chunk_size': args.chunk_size, 'chunk_overlap': args.chunk_overlap,
                  'aprovado': not erros}
        if not erros:
            report.update(resumir_chunks(chunks))
            print(f"{report['modo']}: {report['total_chunks']} chunks; "
                  f"tamanhos {report['menor']}–{report['maior']}; média {report['media']} caracteres.")
            for arquivo, count in report['por_arquivo'].items():
                print(f'  {arquivo}: {count} chunks')
            print(f"Sem pontuação final: {report['chunks_sem_pontuacao_final']} (heurística, não prova de erro).")
            for exemplo in report['exemplos_para_revisao']:
                print(f"  {exemplo['id']}: ...{exemplo['final']!r}")
        for erro in erros:
            print('FALHA:', erro)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('Auditoria concluída. Revise os cortes com o trio; isto não mede a qualidade semântica da busca.')
        return int(bool(erros))
    except ValueError as exc:
        print(f'FALHA: {exc}')
        return 1
    except Exception as exc:
        print(f'FALHA na auditoria ({type(exc).__name__}). Confira arquivos e permissões.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
