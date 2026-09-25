# AskData — roteiro para o Demo Day (25/09/2026)

Público: DataLakers, Navi Hub e colegas. O [roteiro da sprint](https://github.com/eduardo-de-bastiani/grupo-de-estudos-ia/blob/main/sprint_1_fundamentos_rag/dia_10_demo_day_pitch_sprint1.md)
prevê **10 minutos de apresentação e demonstração, seguidos de 5 minutos de perguntas**.
Cronometrem uma vez com o trio e escolham quem assume cada parte; a divisão abaixo
é uma sugestão.

## 0:00–2:00 — Problema e promessa (Nicolas)

> “Quem está aprendendo Airflow e Docker encontra respostas espalhadas entre
> documentação de DAGs, tarefas, Docker Compose e integrações. A dificuldade não
> é apenas achar um texto: é saber se a orientação responde à dúvida e de qual
> página ela veio. Criamos o AskData para estudar esse material com perguntas
> em português e fontes verificáveis.”

> “Nossa base atual reúne 11 PDFs e 84 páginas de documentação oficial exportada
> localmente. São cópias de estudo com paginação própria, não PDFs oficiais
> distribuídos pelos projetos. O escopo é aprendizado sobre Airflow e Docker;
> quando a base não sustenta uma resposta, esperamos uma recusa.”

Mostre a tela inicial e diga em uma frase qual pergunta o usuário pode fazer.
Não gaste tempo navegando por menus neste começo.

## 2:00–5:00 — O que construímos e como funciona (Luca)

> “Primeiro extraímos texto de cada página com `pypdf`. Dividimos em 292 trechos
> de até 700 caracteres, com 100 caracteres de sobreposição. Cada trecho guarda
> nome do arquivo e número da página. O `gemini-embedding-001` transforma esses
> trechos em vetores, que ficam no Chroma local.”

> “Quando chega uma pergunta, geramos outro vetor, recuperamos os três trechos
> mais próximos e enviamos esse contexto ao `gemini-3.5-flash-lite`. A resposta
> em português aponta as fontes. O Streamlit exibe o chat e permite abrir os
> trechos para conferir o que o modelo usou.”

Mostre uma única figura ou fale o fluxo sem abrir código:

`11 PDFs → páginas → 292 trechos com origem → embeddings → Chroma`

`Pergunta → busca top-3 → trechos com arquivo/página → resposta citada`

Explique duas escolhas: a sobreposição tenta preservar contexto quando uma frase
é cortada; guardar página torna a resposta verificável. “Mais próximo” não quer
dizer “verdadeiro”.

> “Auditamos os 292 trechos no banco atual. Em quatro perguntas com páginas
> esperadas, a busca colocou uma dessas páginas entre os três primeiros
> resultados nas quatro. Isso mede a recuperação nesse pequeno conjunto;
> não é uma taxa de precisão de respostas nem prova ausência de alucinações.”

## 5:00–9:00 — Demonstração ao vivo (Manuel)

Antes de começar, deixe o Streamlit aberto com a base atual e o navegador em
tamanho legível. Use as perguntas ensaiadas, uma por vez.

1. Pergunte: **“Onde colocar os arquivos de DAG no ambiente Docker do Airflow?”**
   Aguarde a resposta e abra a fonte. No ensaio com a base de 11 PDFs, o sistema
   respondeu `./dags` e apontou `01-airflow-docker.pdf`, página 2. Diga:
   “A pessoa pode verificar exatamente de onde veio essa orientação.”
2. Mostre o trecho e a página; depois feche o painel. Se houver tempo, mostre
   rapidamente o controle de `top_k` ou um dos temas visuais. Não faça uma visita
   guiada por todos os componentes.
3. Pergunte: **“Como otimizar uma consulta específica no Snowflake?”** No ensaio,
   o sistema respondeu que não encontrou isso nos documentos. Diga:
   “Ele ainda recupera trechos próximos, mas o modelo deve reconhecer quando
   eles não bastam para responder.”

Não afirme que o sistema nunca alucina. O exemplo de recusa é uma demonstração,
não garantia universal. Se a API estiver indisponível, mostre o resultado do
ensaio e explique que o Chroma é local, mas geração e embeddings dependem da API.

## 9:00–10:00 — Aprendizados e encerramento (trio)

> “Nosso desafio mais concreto foi a evolução da base. Começamos com quatro PDFs
> e 168 trechos; quando incluímos mais sete PDFs, o índice antigo não podia ser
> misturado com o novo sem perder consistência. Criamos e auditamos uma coleção
> nova com 292 trechos, preservando a antiga. Também aprendemos a retomar lotes
> quando a API limita chamadas.”

> “O resultado é um assistente de estudo que torna as fontes visíveis. O próximo
> passo seria ampliar o gabarito de perguntas, revisar manualmente as respostas
> e melhorar a segmentação dos textos com base nesses erros reais.”

Termine por volta de 9:30 para absorver uma espera inesperada da demo e passar
às perguntas. Cada integrante deve conseguir resumir o fluxo completo em 20 segundos.

## Perguntas prováveis nos 5 minutos de Q&A

| Pergunta | Resposta objetiva |
| --- | --- |
| Por que RAG em vez de perguntar direto ao Gemini? | Para colocar a documentação do projeto no contexto e mostrar páginas verificáveis. Ainda precisamos validar cada resposta. |
| Como sabem que a busca funciona? | Auditamos 292 chunks. Quatro perguntas com gabarito recuperaram ao menos uma página esperada no top 3. A amostra é pequena. |
| Por que 700 caracteres e 100 de overlap? | Foi o ponto inicial da atividade. O overlap ajuda a manter contexto; vimos cortes de frases e ainda podemos comparar outras divisões. |
| A pontuação do Chroma mede confiança? | Não. É distância entre vetores; uma distância menor indica proximidade, não certeza factual. |
| Por que não responder Snowflake? | A base documenta Airflow e Docker, não otimização de uma consulta Snowflake específica. Responder sem evidência seria inventar. |
| O app roda Airflow ou Docker? | Hoje é um assistente **sobre** a documentação de Airflow e Docker. O próprio app usa Streamlit, Chroma local e Gemini; não orquestra DAGs nem está containerizado. |
| Onde fica a chave? | Em `.env` local, ignorado pelo Git. Cada integrante usa a própria chave; o banco Chroma também é local. |
| Os PDFs são oficiais? | São exportações locais de páginas de documentação oficial, com texto preservado e layout adaptado; a paginação citada é a dessas cópias. |
| O que faria para uso em produção? | Testes maiores de recuperação e fidelidade, atualização controlada do corpus, observabilidade, controle de acesso e limites de custo. Não afirmamos que o protótipo já está pronto para produção. |

## Preparação de 15 minutos antes da apresentação

- Confirmar quem leva o notebook, energia, internet e acesso ao projetor.
- Abrir o repositório na raiz e iniciar o app com
  `.\.venv\Scripts\python.exe -m streamlit run src/app.py`.
- Conferir que o app consulta a coleção atual: `inspecionar_chunks.py` deve
  mostrar 292 trechos dos 11 PDFs. A coleção antiga de 168 está preservada.
- Fazer uma rodada das duas perguntas acima. A API pode mudar de disponibilidade;
  não depender de uma pergunta inédita para a demo principal.
- Deixar uma captura local dos dois resultados como plano B, sem mostrar `.env`,
  chaves, terminal com segredos ou informações pessoais.
- Ensaiar com cronômetro e combinar sinais discretos para troca de fala.
- Manter a pergunta respondida e a fonte abertas antes de entregar a palavra
  a quem vai explicar o trecho.

## Coisas que causam boa impressão

- Abrir com uma dor concreta e mostrar a solução em menos de dois minutos.
- Mostrar uma fonte real, não apenas uma resposta bonita.
- Distinguir o que foi **medido** do que ainda depende de revisão humana.
- Assumir limites com naturalidade e explicar o próximo experimento para melhorá-los.
- Dividir a fala entre os três e responder perguntas de forma breve e verificável.

O pitch de um minuto no README continua útil como versão curta caso o tempo seja
reduzido. O teste cruzado com outro trio e os formulários são atividades das
pessoas participantes; não devem ser declarados concluídos sem terem ocorrido.
