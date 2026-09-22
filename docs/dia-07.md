# Dia 7 — guia do Nicolas para acompanhar sem notebook

Projeto: AskData — Airflow + Docker, grupo de estudos IA PUCRS.

## O que está preparado

- Ambiente Python 3.12 e dependências instalados nesta máquina.
- Ingestão de PDF/Markdown em `src/ingestion.py`.
- Prévia e auditoria em `inspecionar_chunks.py`.
- Teste offline do Chroma em `test_chroma_setup.py`.
- Oito testes automatizados aprovados.
- Corpus real validado offline: quatro PDFs, 38 páginas, 168 chunks.
- Chave configurada localmente pelo usuário e `check_setup.py` aprovado.
- **Ingestão real concluída:** 168 embeddings Gemini persistidos no Chroma;
  auditoria aprovada e reexecução com zero pendências.
- Houve HTTP 429 após 96 chunks. A retomada com espera concluiu os 72 restantes
  sem reenviar os lotes salvos; o intervalo entre lotes foi ajustado para 12 segundos.
- O motor de respostas e a interface continuam reservados aos dias 8 e 9.

Estes resultados são da preparação local; palestra, dinâmica do trio, quiz e
formulário ainda devem ser realizados. O usuário responde seu próprio formulário.

## Antes de sair de casa

1. Garantir que os arquivos desta preparação estejam disponíveis ao trio no GitHub
   ou em uma cópia compartilhada. Alterações só locais não chegam aos colegas.
2. Abrir este roteiro no celular e salvar para consulta offline, se necessário.
3. Combinar com Luca ou Manuel o uso de um notebook para a prática. Nicolas pode
   conduzir a explicação e acompanhar a execução; combinar qualquer ajuste na
   rotação de piloto com o trio/monitor.
4. Cada pessoa usa sua própria chave. Não enviar `.env`, `.venv` ou `chroma_db`.
   Quem executar a ingestão precisará de internet e de chave com acesso ao modelo.

## A ideia em uma frase

Hoje vamos transformar os PDFs em uma base pesquisável, mantendo o endereço de
origem de cada trecho para permitir respostas com citações na próxima aula.

`PDF → texto por página → chunks → embeddings → Chroma local`

| Conceito | O que significa no nosso projeto |
| --- | --- |
| Ingestão | Ler os documentos e prepará-los para busca. |
| Chunk | Um trecho de até 700 caracteres, sem atravessar páginas. |
| Overlap | Repetir até 100 caracteres entre trechos vizinhos da mesma página. |
| Embedding | Um vetor numérico que representa aspectos do significado do texto. |
| Chroma | Banco que guarda texto, vetores e metadados para futuras buscas. |
| Metadados | Arquivo, página, número do chunk e posições do trecho no texto extraído. |
| Persistência | Os dados ficam salvos em disco e podem ser usados em outra execução. |

O modelo de embeddings organiza a busca. O modelo de geração escreverá a resposta
no Dia 8. São funções diferentes: hoje usamos `gemini-embedding-001`; a geração
continua planejada com `gemini-3.5-flash-lite`.

## Chunking na régua: exemplo para explicar ao trio

Contando os caracteres a partir de 1:

- Primeiro trecho: caracteres 1 a 700.
- Segundo trecho: caracteres 601 a 1300.
- Repetição: caracteres 601 a 700, totalizando 100.
- O avanço é de 600 caracteres: `700 - 100`.

No Python, usamos posições a partir de zero e final exclusivo: `texto[0:700]`
e `texto[600:1300]`. São caracteres, não tokens. A divisão reinicia a cada página.
Se chegamos ao fim da página, paramos; não criamos outro trecho contendo só a
parte que já apareceu no anterior.

Na página 1 de `01-airflow-docker.pdf`, a sobreposição real entre os dois primeiros
chunks é o seguinte texto de 100 caracteres (há uma quebra de linha):

```python
'g and exploration. However, adapting it for use in real-world situations\ncan be complicated and the '
```

A notação `\n` representa a quebra de linha e o espaço antes da última aspa
também faz parte da sobreposição.

O começo já está no meio de uma palavra: contar caracteres não respeita frases.
O overlap ajuda a recuperar contexto, mas não garante que toda frase fique inteira.
Na dinâmica, escolham uma página, observem o corte e discutam se os 100 caracteres
preservam a ideia. Não marquem a dinâmica como feita apenas porque o script rodou.

## Resultados medidos na preparação

| Documento | Páginas | Chunks com 700/100 |
| --- | ---: | ---: |
| Airflow: ambiente Docker | 7 | 34 |
| Airflow: DAGs | 16 | 74 |
| Airflow: tarefas | 7 | 31 |
| Docker Compose | 8 | 29 |
| **Total** | **38** | **168** |

Menor chunk: 102 caracteres. Maior: 700. Média: 624,27.
147 chunks terminam sem uma das pontuações verificadas pelo script. Isso serve
para escolher exemplos para inspeção; código, títulos e listas também podem
terminar sem pontuação. Não significa que 147 chunks estejam errados.

Comparação offline no mesmo corpus:

| Tamanho / overlap | Quantidade de chunks |
| --- | ---: |
| 300 / 50 | 381 |
| 700 / 100 | 168 |
| 1200 / 200 | 103 |

Trechos menores dão mais granularidade; maiores carregam mais contexto. A contagem
sozinha não revela qual configuração responde melhor. Isso exige avaliar a busca.
O [relatório offline](dia-07-auditoria-offline.json) contém contagens por página.
O [relatório do índice real](dia-07-auditoria-chroma.json) confirma a integridade
dos chunks persistidos. A auditoria lê o banco sem chamar a API; os embeddings
foram gerados na etapa de ingestão anterior. Qualidade da busca ainda será avaliada.

## Execução no notebook do trio

Esta preparação está na branch `codex/dia-7-ingestao`. Quem já tem o clone deve
conferir `git status` antes de atualizar, preservar alterações locais e executar
`git fetch origin` seguido de `git switch codex/dia-7-ingestao`.
Quem ainda não tem pode clonar diretamente a branch:

```powershell
git clone --branch codex/dia-7-ingestao https://github.com/NicolasCussioli/askdata-airflow-docker.git
cd askdata-airflow-docker
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Preencher `GEMINI_API_KEY` no editor local. Não colar a chave no terminal, chat,
README ou prints. Os comandos abaixo usam o Python da venv diretamente, dispensando
a ativação pelo PowerShell.

### 1. Conferir sem consumir a API

```powershell
.\.venv\Scripts\python.exe test_chroma_setup.py
.\.venv\Scripts\python.exe src/ingestion.py --dry-run
.\.venv\Scripts\python.exe inspecionar_chunks.py --preview
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Esperado: teste do Chroma aprovado, 168 chunks na prévia e oito testes aprovados.
O teste do Chroma usa vetores artificiais de três dimensões em um banco separado:
ele prova inserção, reabertura e ordenação por cosseno, não compreensão dos PDFs.

### 2. Gerar os embeddings reais

```powershell
.\.venv\Scripts\python.exe check_setup.py
.\.venv\Scripts\python.exe src/ingestion.py
```

O primeiro comando verifica a presença da chave, mas não testa autenticação.
O segundo envia o texto dos chunks para a API Gemini, gera vetores de 3072 dimensões
e salva na coleção `askdata_knowledge`, em `chroma_db/`. São lotes de até 16 chunks;
o corpus atual requer 11 lotes na primeira execução, sem contar retentativas.
Há um intervalo de 12 segundos entre lotes. Em erros transitórios, o programa
aguarda 20 e depois 40 segundos antes de tentar novamente.
Uso e limites dependem da conta e da cota da API; não presumir disponibilidade.

Se houver falha, os lotes anteriores ficam salvos. Corrijam a causa e executem o
mesmo comando: o programa retoma os chunks pendentes sem repetir os já salvos.
Uma indexação parcial não deve ser considerada pronta para o Dia 8.

### 3. Auditar o que foi salvo

```powershell
.\.venv\Scripts\python.exe inspecionar_chunks.py
```

Esperado: modo `chroma_persistido`, 168 chunks e nenhuma falha de integridade.
A auditoria compara IDs, textos, arquivo/página e parâmetros com a extração atual.
Depois, inspecionem os exemplos de corte. Nenhum desses testes comprova sozinho
que a futura busca encontrará a melhor evidência para cada pergunta.

### 4. Se der problema

| Mensagem/situação | Próxima ação |
| --- | --- |
| Chave ausente | Preencher a `.env` local; não enviar a chave ao grupo. |
| API indisponível | Conferir chave, cota e rede; repetir após corrigir. Há até três tentativas por lote para erros transitórios. |
| Banco/coleção ausente | Rodar ingestão real; `--preview` não cria o índice. |
| Indexação incompleta | Reexecutar a ingestão para retomar e depois auditar. |
| Corpus/configuração diferente | Usar um novo nome de coleção nos dois scripts. Não misturar os índices. |
| Página sem texto | Revisar PDF/OCR antes de prosseguir. |

Para comparar outros tamanhos sem gastar API:

```powershell
.\.venv\Scripts\python.exe inspecionar_chunks.py --preview --chunk-size 300 --chunk-overlap 50
.\.venv\Scripts\python.exe inspecionar_chunks.py --preview --chunk-size 1200 --chunk-overlap 200
```

## O que explicar quando mostrarem o código

1. `extrair_texto_pdf`: lê página por página, preservando a numeração local.
2. `criar_chunks`: avança 600 caracteres por vez e mantém a origem em cada trecho.
3. `criar_gerador_embeddings`: usa Gemini com a tarefa `RETRIEVAL_DOCUMENT`.
4. `indexar_no_chromadb`: persiste lotes, reaproveita IDs já gravados e verifica a
   assinatura do corpus antes de continuar. `upsert` insere ou atualiza pelo ID.
5. `auditar_colecao`: compara o banco com os documentos atuais para detectar
   faltas, extras ou alterações. A análise de pontuação é apenas uma heurística.

Usamos cosseno para comparar a direção dos vetores. No Chroma, menor distância
significa maior proximidade nessa métrica. No Dia 8, perguntas usarão o mesmo
modelo e dimensão com `RETRIEVAL_QUERY`; a busca será por vetores explícitos.

## Fala curta para apresentar a preparação

“Preparamos a ingestão dos quatro PDFs sobre Airflow e Docker. As 38 páginas
viraram 168 trechos de até 700 caracteres, com sobreposição de 100. Cada trecho
guarda arquivo e página para permitir citações. Validamos a extração, a persistência
local e a retomada após falha. Geramos os embeddings Gemini e auditamos os 168
trechos no Chroma. A próxima etapa será testar a recuperação de evidências e
construir as respostas com citações.”

## Checklist da aula

- [ ] Participar da conversa com o convidado e anotar insights.
- [ ] Ler as referências de chunking e Chroma indicadas no roteiro oficial.
- [ ] Fazer a dinâmica de chunking com o trio e discutir cortes reais.
- [ ] Executar teste local do Chroma.
- [ ] Gerar os embeddings Gemini e concluir a persistência.
- [ ] Auditar a coleção real e revisar exemplos de chunks.
- [ ] Sincronizar o código com os colegas, mantendo segredos e banco fora do Git.
- [ ] Responder individualmente ao quiz.
- [ ] Preencher pessoalmente o formulário diário.

## Referências

- [Roteiro oficial do Dia 7](https://github.com/eduardo-de-bastiani/grupo-de-estudos-ia/blob/main/sprint_1_fundamentos_rag/dia_07_ingestao_chunking_embeddings.md).
- [Documentação de embeddings Gemini](https://ai.google.dev/gemini-api/docs/embeddings).
- Quiz e formulário: acessar pelos links do roteiro oficial; o usuário responde.
