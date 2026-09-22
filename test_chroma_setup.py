"""Teste offline de persistência e distância de cosseno; não usa Gemini."""
from src.ingestion import ROOT, cliente_chroma


def main():
    # Banco separado: vetores artificiais jamais entram no índice de documentos.
    client = cliente_chroma(ROOT / 'chroma_db' / '_smoke_test')
    collection = client.get_or_create_collection(
        'teste_configuracao', embedding_function=None,
        configuration={'hnsw': {'space': 'cosine'}},
    )
    collection.upsert(
        ids=['doc_1', 'doc_2'], documents=['Exemplo Airflow', 'Exemplo Docker'],
        embeddings=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        metadatas=[{'arquivo': 'exemplo_a.pdf', 'pagina': 1},
                   {'arquivo': 'exemplo_b.pdf', 'pagina': 2}],
    )
    reaberta = cliente_chroma(ROOT / 'chroma_db' / '_smoke_test').get_collection(
        'teste_configuracao', embedding_function=None)
    assert reaberta.count() == 2, 'A contagem deve permanecer em 2 ao repetir o teste.'
    resultado = reaberta.query(query_embeddings=[[1.0, 0.0, 0.0]], n_results=2)
    assert resultado['ids'][0] == ['doc_1', 'doc_2']
    assert abs(resultado['distances'][0][0]) < 1e-6
    assert abs(resultado['distances'][0][1] - 1) < 1e-6
    print('APROVADO: Chroma local, upsert, reabertura e cosseno. Vetores artificiais; sem API.')


if __name__ == '__main__':
    main()
