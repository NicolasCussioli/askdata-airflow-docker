import streamlit as st
import os
import time
from rag_engine import RAGEngine
import json

# Configuracao da pagina
st.set_page_config(
    page_title="AskData - Base de Conhecimento Inteligente",
    layout="wide"
)

#Inicializar historico inicial
if "messages" not in st.session_state:
    st.session_state.messages = []

# Inicializar o motor RAG em cache para evitar recriacao desnecessaria
@st.cache_resource
def get_rag_engine():
    return RAGEngine()

try:
    engine = get_rag_engine()
except Exception as e:
    st.error(f"Erro ao inicializar o motor RAG: {e}. Verifique sua GEMINI_API_KEY no arquivo .env!")
    st.stop()

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=300&auto=format&fit=crop&q=60", use_container_width=True)
    st.title("Painel de Controle")
    st.markdown("**AskData** | *DataLakers & Navi Hub*")
    st.markdown("---")
    
    top_k = st.slider("Quantidade de Chunks (Top-K):", min_value=1, max_value=5, value=3)
    
    st.markdown("### Sobre a Base Indexada")
    st.caption("Esta aplicação utiliza embeddings do Google (`gemini-embedding-001`), armazenamento vetorial persistente no **ChromaDB** e geração com o **Modelo Gemini**.")
    
    if st.button("Limpar Historico de Chat"):
        st.session_state.messages = []
        st.rerun()

    # Baixar Histórico
    historico_json = json.dumps(st.session_state.messages, indent=2, ensure_ascii=False)
    st.sidebar.download_button(
    label="Exportar Historico (JSON)",
    data=historico_json,
    file_name="historico_chat.json",
    mime="application/json"
)

# --- AREA PRINCIPAL ---
st.title("AskData: Assistente de Documentacao Tecnica")
st.caption("Faça perguntas sobre a base de conhecimento. Todas as respostas são fundamentadas com citação direta dos documentos.")

# Inicializar historico na sessao
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Olá! Sou o AskData. Como posso ajudar com base nos documentos técnicos da empresa?", "fontes": []}
    ]

# Renderizar historico de mensagens
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("fontes"):
            with st.expander("Ver Fontes e Chunks Recuperados"):
                for idx, f in enumerate(msg["fontes"], 1):
                    st.markdown(f"**Fonte {idx}:** `{f['arquivo']}` (Pág. {f['pagina']}) — *distancia: {f['distancia']:.2%}*")
                    st.info(f['texto'])

# Input do usuario
if prompt := st.chat_input("Digite sua pergunta técnica aqui..."):
    # 1. Adicionar mensagem do usuario na tela
    st.session_state.messages.append({"role": "user", "content": prompt, "fontes": []})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Gerar resposta com o motor RAG
    with st.chat_message("assistant"):
        with st.spinner("Buscando no banco vetorial e formulando resposta..."):
            try:
                inicio = time.perf_counter()
                resultado = engine.responder_pergunta(prompt, top_k=top_k)
                latencia = time.perf_counter() - inicio
                st.caption(f"Tempo de resposta: {latencia:.2f}s")

                resposta_texto = resultado["resposta"]
                fontes = resultado["fontes"]
                
                st.markdown(resposta_texto)
                
                if fontes:
                    with st.expander("Ver Fontes e Chunks Recuperados"):
                        for idx, f in enumerate(fontes, 1):
                            st.markdown(f"**Fonte {idx}:** `{f['arquivo']}` (Pág. {f['pagina']}) — *distancia: {f['distancia']:.2%}*")
                            st.info(f['texto'])
                
                # Salvar no historico da sessao
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": resposta_texto,
                    "fontes": fontes
                })
            except Exception as err:
                st.error(f"Erro ao processar a pergunta: {err}")