# AskData - Airflow + Docker

Assistente de estudo para encontrar respostas sobre DAGs, tarefas e execução local
de pipelines com Docker Compose, citando o documento e a página de cada evidência.

**Estado:** kickoff do dia 6. O corpus e o smoke test estão prontos; ingestão,
respostas e interface serão implementadas nos dias 7, 8 e 9.

## Corpus

| PDF | Assunto | Páginas |
| --- | --- | ---: |
| 01-airflow-docker.pdf | Ambiente local, inicialização e diagnóstico | 7 |
| 02-airflow-dags.pdf | Definição, dependências e organização de DAGs | 16 |
| 03-airflow-tasks.pdf | Ciclo de vida, estados e problemas de tarefas | 7 |
| 04-docker-compose.pdf | Serviços, health checks, volumes e logs | 8 |

Total: **38 páginas**. Fontes em inglês; perguntas e futuras respostas em português.
Os PDFs são exportações locais de páginas oficiais, **não PDFs oficiais distribuídos
pelos projetos**. Texto preservado, layout modificado, imagens omitidas e código longo
quebrado para impressão. Para copiar comandos, consulte o HTML/origem.
O roteiro pede PDFs reais; confirmar no pitch a aceitação destas exportações de
documentação real. Os originais e metadados estão em `sources/`; o índice futuro deve
ler somente `data/` para não duplicar a base.

Airflow fixado em **3.3.2**; Docker Docs registrado como snapshot de 21/09/2026.
URLs, hashes, datas e licenças estão em `sources/manifest.json`. Paginação de citação
é a destas cópias locais. Manter PDFs e manifesto juntos e não regenerar após indexar
sem reconstruir o banco. Arquivos de licença e NOTICE acompanham os documentos.

## Setup independente (Windows / Python 3.12)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Preencha GEMINI_API_KEY na sua .env, sem enviar a chave para o Git.
.\.venv\Scripts\python.exe check_setup.py
```

O teste verifica dependências, presença da chave, PDFs legíveis e limites de quantidade
e páginas. Ele **não chama a API nem comprova autenticação**. A leitura de texto é uma
triagem; a qualidade visual também precisa ser conferida. Não é preciso instalar
Airflow ou iniciar containers para concluir este kickoff de um assistente documental.

Modelos: geração `gemini-3.5-flash-lite`; embeddings `gemini-embedding-001`.
Cada participante configura sua própria chave na `.env` local.

## Pitch de aproximadamente 1 minuto

Nosso AskData vai ajudar quem está aprendendo a executar pipelines de dados com
Airflow e Docker. Hoje, uma dúvida sobre dependências, tarefas que falham ou containers
que não ficam prontos exige procurar em várias páginas de documentação. Vamos reunir
quatro documentos oficiais, exportados em 38 páginas, sobre DAGs, tarefas, ambiente
Airflow e Docker Compose. O usuário fará perguntas em português e o assistente buscará
os trechos relevantes antes de responder, mostrando arquivo e página. Isso permite
conferir de onde veio cada orientação. O escopo é estudo e execução local; a base não
pretende cobrir toda a engenharia de dados nem orientar produção fora das fontes.
Quando a documentação não responder, o assistente deverá reconhecer essa limitação.

## Perguntas para a avaliação futura

1. Onde colocar os arquivos de DAG no ambiente Docker do Airflow?
2. Como inicializar o banco antes de iniciar os serviços?
3. Como representar dependência entre duas tarefas?
4. Qual a diferença entre DAG e execução de DAG?
5. Quais estados uma tarefa pode assumir?
6. Como investigar uma tarefa que parece travada?
7. Como evitar iniciar um serviço antes de a dependência estar pronta?
8. Como acompanhar logs dos serviços do Docker Compose?
9. O quickstart Docker do Airflow é apropriado para produção?
10. Fora da base: como otimizar uma consulta específica no Snowflake?

Ainda não são resultados de teste. Nos dias 7/8, localizar evidências, definir gabarito
por arquivo/página e medir a recuperação antes de avaliar respostas geradas.

## Equipe e contrato (preencher com o trio)

| Participante | GitHub | Piloto |
| --- | --- | --- |
| Nicolas Cussioli | NicolasCussioli | A definir |
| A definir | A definir | A definir |
| A definir | A definir | A definir |

- Repositório colaborativo: https://github.com/NicolasCussioli/askdata-airflow-docker
- Comunicação: a definir.
- Rotação: um piloto por dia (7/8/9), outros dois acompanham e revisam.
- Proposta para impasses: discutir/pesquisar por 10 minutos e então chamar monitor.
- Trio parceiro e feedback do pitch: pendentes.

## Arquitetura planejada

`PDF -> texto + arquivo/página -> chunks (700/100) -> embeddings -> Chroma local`

`Pergunta -> embedding -> trechos top-k -> prompt com evidências -> resposta citada`

Os módulos em `src/` são marcadores explícitos das próximas aulas, não implementações.
Para recriar o corpus, instale `tools/requirements.txt` e execute
`python tools/coletar_documentos.py`. Isso acessa a rede e pode alterar os snapshots.

## Estrutura do Bloco 4

```text
askdata-airflow-docker/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── check_setup.py
├── data/
├── chroma_db/          # local, ignorada pelo Git
└── src/
    ├── __init__.py
    ├── ingestion.py    # Dia 7
    ├── rag_engine.py   # Dia 8
    └── app.py          # Dia 9
```

`sources/` preserva os originais, licenças e manifesto dos PDFs; `tools/` contém
o exportador. A pasta `chroma_db/` será criada pelo pipeline em cada máquina.

Para começar, aceite o convite e clone:

```powershell
git clone https://github.com/NicolasCussioli/askdata-airflow-docker.git
cd askdata-airflow-docker
```

Depois siga o setup acima. Os convites dos demais participantes ainda serão enviados.
