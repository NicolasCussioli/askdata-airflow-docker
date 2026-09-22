"""Verificações offline: cortes, rastreabilidade, retomada e integridade do índice."""
import unittest
from unittest.mock import Mock
from uuid import uuid4

from src.ingestion import (ROOT, EMBEDDING_DIMENSION, carregar_documentos, criar_chunks,
                           indexar_no_chromadb, cliente_chroma, contrato_indice)
from inspecionar_chunks import auditar_colecao


def pagina(texto, numero=1):
    return {'texto': texto, 'arquivo': 'teste.pdf', 'pagina': numero}


def vetores_teste(textos):
    return [[1.0] + [0.0] * (EMBEDDING_DIMENSION - 1) for _ in textos]


class ChunkTests(unittest.TestCase):
    def test_overlap_cobertura_e_sem_cauda_duplicada(self):
        texto = ''.join(str(i % 10) for i in range(1300))
        chunks = criar_chunks([pagina(texto)])
        self.assertEqual([c['inicio'] for c in chunks], [0, 600])
        self.assertEqual(chunks[0]['texto'][-100:], chunks[1]['texto'][:100])
        self.assertEqual(chunks[0]['texto'] + chunks[1]['texto'][100:], texto)
        self.assertEqual(len(criar_chunks([pagina('x' * 700)])), 1)

    def test_parametros_invalidos(self):
        for tamanho, overlap in [(0, 0), (10, 10), (10, -1), (10, 11)]:
            with self.subTest(tamanho=tamanho, overlap=overlap), self.assertRaises(ValueError):
                criar_chunks([pagina('texto')], tamanho, overlap)

    def test_paginas_nao_se_misturam(self):
        chunks = criar_chunks([pagina('abc'), pagina('def', 7)])
        self.assertEqual([c['pagina'] for c in chunks], [1, 7])
        self.assertEqual([c['texto'] for c in chunks], ['abc', 'def'])
        self.assertEqual(criar_chunks([pagina('   ')]), [])

    def test_corpus_real_e_reconstrucao(self):
        paginas = carregar_documentos(ROOT / 'data')
        self.assertEqual(len(paginas), 38)
        self.assertEqual(len({p['arquivo'] for p in paginas}), 4)
        chunks = criar_chunks(paginas)
        self.assertEqual(len({c['id'] for c in chunks}), len(chunks))
        for p in paginas:
            partes = [c for c in chunks if (c['arquivo'], c['pagina']) == (p['arquivo'], p['pagina'])]
            self.assertTrue(partes)
            self.assertEqual(partes[0]['inicio'], 0)
            self.assertEqual(partes[-1]['fim'], len(p['texto']))
            for c in partes:
                self.assertEqual(c['texto'], p['texto'][c['inicio']:c['fim']])


class ChromaTests(unittest.TestCase):
    def setUp(self):
        # Mantido na .venv ignorada: Chroma pode manter arquivos abertos no Windows.
        self.db = ROOT / '.venv' / 'test_chroma' / uuid4().hex
        self.chunks = criar_chunks([pagina('a' * 1300)])

    def indexar(self, gerar=vetores_teste, **kwargs):
        return indexar_no_chromadb(self.chunks, gerar, self.db, batch_size=1, batch_delay=0, **kwargs)

    def colecao(self):
        return cliente_chroma(self.db).get_collection('askdata_knowledge', embedding_function=None)

    def test_reexecucao_nao_repete_api_e_audita_conteudo(self):
        self.assertEqual(self.indexar(), 2)
        gerar = Mock(side_effect=AssertionError('Não deveria chamar API novamente'))
        self.assertEqual(self.indexar(gerar), 2)
        gerar.assert_not_called()
        _, erros = auditar_colecao(self.colecao(), self.chunks, contrato_indice(self.chunks, 700, 100))
        self.assertEqual(erros, [])
        self.colecao().update(ids=[self.chunks[0]['id']], metadatas=[{'pagina': 99}])
        _, erros = auditar_colecao(self.colecao(), self.chunks, contrato_indice(self.chunks, 700, 100))
        self.assertTrue(erros)

    def test_retomada_apos_falha(self):
        gerar = Mock(side_effect=[vetores_teste(['primeiro']), RuntimeError('Falha simulada')])
        with self.assertRaises(RuntimeError):
            self.indexar(gerar)
        self.assertEqual(self.colecao().count(), 1)
        self.assertFalse(self.colecao().metadata['index_complete'])
        retomada = Mock(side_effect=vetores_teste)
        self.assertEqual(self.indexar(retomada), 2)
        retomada.assert_called_once_with([self.chunks[1]['texto']])
        self.assertTrue(self.colecao().metadata['index_complete'])

    def test_corpus_modificado_nao_mistura_indices(self):
        self.indexar()
        self.chunks[0]['texto'] = 'documento modificado'
        gerar = Mock()
        with self.assertRaises(ValueError):
            self.indexar(gerar)
        gerar.assert_not_called()
        self.assertEqual(self.colecao().count(), 2)

    def test_embedding_invalido_nao_persiste(self):
        with self.assertRaises(ValueError):
            self.indexar(lambda textos: [[0.0, 1.0]])
        self.assertEqual(self.colecao().count(), 0)
        self.assertFalse(self.colecao().metadata['index_complete'])


if __name__ == '__main__':
    unittest.main()
