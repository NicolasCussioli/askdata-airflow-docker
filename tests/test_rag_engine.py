"""Dia 8: contratos do índice, recuperação e citações sem chamadas à API."""
from types import SimpleNamespace
import unittest

from src.ingestion import EMBEDDING_DIMENSION, EMBEDDING_MODEL
from src.rag_engine import (RAGEngine, RECUSA, formatar_contexto,
                            selecionar_citacoes, validar_pergunta)


class ColecaoFalsa:
    metadata = {'index_complete': True, 'embedding_model': EMBEDDING_MODEL,
                'embedding_dimension': EMBEDDING_DIMENSION,
                'task_type': 'RETRIEVAL_DOCUMENT', 'expected_chunks': 2}

    def count(self):
        return 2

    def query(self, **kwargs):
        self.consulta = kwargs
        return {'documents': [['Use ./dags para arquivos de DAG.', 'Outro trecho.']],
                'metadatas': [[{'arquivo': 'airflow.pdf', 'pagina': 2},
                               {'arquivo': 'docker.pdf', 'pagina': 4}]],
                'distances': [[0.2, 0.7]]}


class ModelosFalsos:
    def __init__(self, resposta='Coloque os arquivos em ./dags [F1].'):
        self.resposta = resposta
        self.chamadas_geracao = 0

    def embed_content(self, **kwargs):
        self.embedding_args = kwargs
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[1.0] * EMBEDDING_DIMENSION)])

    def generate_content(self, **kwargs):
        self.chamadas_geracao += 1
        self.geracao_args = kwargs
        return SimpleNamespace(text=self.resposta)


class RagTests(unittest.TestCase):
    def criar_motor(self, resposta='Coloque os arquivos em ./dags [F1].'):
        modelos = ModelosFalsos(resposta)
        colecao = ColecaoFalsa()
        return RAGEngine(client=SimpleNamespace(models=modelos), collection=colecao), modelos, colecao

    def test_embedding_da_pergunta_e_busca_explicita(self):
        motor, modelos, colecao = self.criar_motor()
        fontes = motor.recuperar_contexto('Onde ficam os DAGs?', top_k=2)
        self.assertEqual(modelos.embedding_args['config'].task_type, 'RETRIEVAL_QUERY')
        self.assertEqual(modelos.embedding_args['config'].output_dimensionality, EMBEDDING_DIMENSION)
        self.assertEqual(len(colecao.consulta['query_embeddings'][0]), EMBEDDING_DIMENSION)
        self.assertEqual(colecao.consulta['n_results'], 2)
        self.assertEqual([(f['arquivo'], f['pagina']) for f in fontes],
                         [('airflow.pdf', 2), ('docker.pdf', 4)])

    def test_resposta_citada_tem_origem(self):
        motor, modelos, _ = self.criar_motor()
        resultado = motor.responder_pergunta('Onde ficam os DAGs?')
        self.assertIn('[F1]', resultado['resposta'])
        self.assertEqual([(f['arquivo'], f['pagina']) for f in resultado['fontes']],
                         [('airflow.pdf', 2)])
        self.assertIn('<fonte id="F1" arquivo="airflow.pdf" pagina="2">',
                      modelos.geracao_args['contents'])

    def test_fonte_inventada_ou_sem_citacao_e_recusada(self):
        for resposta in ('DAGs ficam em ./dags.', 'DAGs ficam em ./dags [F9].'):
            with self.subTest(resposta=resposta):
                motor, _, _ = self.criar_motor(resposta)
                resultado = motor.responder_pergunta('Onde ficam os DAGs?')
                self.assertEqual(resultado['resposta'], RECUSA)
                self.assertEqual(resultado['fontes'], [])

    def test_recusa_modelo_nao_fabrica_fonte(self):
        motor, _, _ = self.criar_motor(RECUSA)
        resultado = motor.responder_pergunta('Qual é a população de Saturno?')
        self.assertEqual(resultado['resposta'], RECUSA)
        self.assertEqual(resultado['fontes'], [])
        self.assertEqual(len(resultado['fontes_recuperadas']), 2)

    def test_indice_incompleto_falha_antes_da_api(self):
        colecao = ColecaoFalsa()
        colecao.metadata = {**colecao.metadata, 'index_complete': False}
        with self.assertRaises(ValueError):
            RAGEngine(collection=colecao)

    def test_entrada_e_identificadores(self):
        for pergunta in ('', '  ', 'a' * 1001):
            with self.assertRaises(ValueError):
                validar_pergunta(pergunta)
        motor, _, _ = self.criar_motor()
        for top_k in (0, 11, '3'):
            with self.assertRaises(ValueError):
                motor.recuperar_contexto('DAG?', top_k)
        fontes = [{'arquivo': 'a.pdf', 'pagina': 1, 'texto': 'texto'}]
        self.assertIn('a.pdf', formatar_contexto(fontes))
        self.assertIsNone(selecionar_citacoes('Texto [F2]', fontes))


if __name__ == '__main__':
    unittest.main()
