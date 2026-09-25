import streamlit as st
import os
import time
from base64 import b64encode
from pathlib import Path
from rag_engine import RAGEngine
import json


THEME_OPTIONS = ("Essencial", "Evidências", "Estudo guiado")
THEME_DETAILS = {
    "Essencial": {
        "number": "01",
        "title": "Assistente de documentação técnica",
        "description": "Respostas objetivas, sempre ligadas aos documentos da base.",
        "accent": "#5dd6df",
        "accent_dark": "#254556",
    },
    "Evidências": {
        "number": "02",
        "title": "Resposta com fontes à vista",
        "description": "Leia a resposta e confira os trechos que a sustentam.",
        "accent": "#5dd6df",
        "accent_dark": "#254556",
    },
    "Estudo guiado": {
        "number": "03",
        "title": "Aprenda Airflow e Docker por perguntas",
        "description": "Comece por um conceito e avance com fontes da documentação.",
        "accent": "#ff8c61",
        "accent_dark": "#4e3733",
    },
}


def svg_data_uri(filename):
    asset = Path(__file__).resolve().parent / "assets" / filename
    encoded = b64encode(asset.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"

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
except Exception:
    st.error("Não foi possível iniciar a base de conhecimento. Verifique sua GEMINI_API_KEY na .env local e o índice Chroma.")
    st.stop()


def submit_question(question, top_k):
    st.session_state.messages.append({"role": "user", "content": question, "fontes": []})
    try:
        start = time.perf_counter()
        result = engine.responder_pergunta(question, top_k=top_k)
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["resposta"],
            "fontes": result["fontes"],
            "latencia": time.perf_counter() - start,
        })
    except (ValueError, RuntimeError) as exc:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Não foi possível processar a pergunta: {exc}",
            "fontes": [],
            "erro": True,
        })
    except Exception:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Não foi possível processar a pergunta. Confira a configuração local e tente novamente.",
            "fontes": [],
            "erro": True,
        })


def render_sources(sources, theme):
    if not sources:
        return

    if theme == "Evidências":
        st.markdown("#### Evidências")
        for index, source in enumerate(sources, 1):
            with st.container(border=True):
                st.caption(f"F{index} · {source['arquivo']} · pág. {source['pagina']}")
                st.write(source["texto"])
        return

    first = sources[0]
    if theme == "Essencial":
        st.caption(f"Fonte 1 · {first['arquivo']} · pág. {first['pagina']}")
    else:
        st.info(f"[F1] Confira a página {first['pagina']} de {first['arquivo']}.")

    with st.expander("Ver fontes e trechos recuperados"):
        for index, source in enumerate(sources, 1):
            st.markdown(f"**F{index} · {source['arquivo']} · pág. {source['pagina']}**")
            st.write(source["texto"])


def render_message(message, theme):
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
            return

        if message.get("erro"):
            st.error(message["content"])
            return

        if theme == "Evidências" and message.get("fontes"):
            answer_column, sources_column = st.columns([2, 1], gap="medium")
            with answer_column:
                with st.container(border=True):
                    st.markdown("**Resposta do AskData**")
                    st.markdown(message["content"])
                    if "latencia" in message:
                        st.caption(f"Tempo de resposta: {message['latencia']:.2f}s")
            with sources_column:
                render_sources(message["fontes"], theme)
        else:
            with st.container(border=True):
                if theme == "Estudo guiado":
                    st.caption("CONCEITO · RESPOSTA FUNDAMENTADA")
                else:
                    st.markdown("**Resposta do AskData**")
                st.markdown(message["content"])
                if "latencia" in message:
                    st.caption(f"Tempo de resposta: {message['latencia']:.2f}s")
                render_sources(message.get("fontes", []), theme)

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.markdown(
        """
        <style>
        .askdata-brand-banner {
            position: relative;
            width: 100%;
            aspect-ratio: 460 / 276;
            overflow: hidden;
            border-radius: 10px;
            background-size: 100% 100%;
            container-type: inline-size;
            margin-bottom: 1rem;
        }
        .askdata-brand-mark {
            position: absolute;
            top: 12%;
            left: 35.65%;
            width: 28.7%;
            height: auto;
        }
        .askdata-brand-name,
        .askdata-brand-tagline {
            position: absolute;
            left: 0;
            width: 100%;
            text-align: center;
            font-family: Roboto, sans-serif;
            font-weight: 700;
        }
        .askdata-brand-name {
            top: 56.5%;
            color: #fff;
            font-size: 7.6cqw;
            line-height: 1.2;
        }
        .askdata-brand-tagline {
            top: 76.5%;
            color: #a7dfe9;
            font-size: max(10px, 2.6cqw);
            letter-spacing: .02em;
            white-space: nowrap;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="askdata-brand-banner" style="background-image: url('{svg_data_uri('askdata-banner-bg.svg')}');">
            <img class="askdata-brand-mark" src="{svg_data_uri('askdata-mark.svg')}" alt="Símbolo AskData: fluxo e contêineres">
            <span class="askdata-brand-name">AskData</span>
            <span class="askdata-brand-tagline">AIRFLOW · DOCKER · CONHECIMENTO</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
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

    with st.expander("Temas da interface", expanded=False):
        st.radio(
            "Escolha a apresentação",
            THEME_OPTIONS,
            key="tema_interface",
            label_visibility="collapsed",
        )
        st.caption("A troca de tema preserva a conversa.")

    # Perguntas frequentes
    st.sidebar.markdown("### Perguntas Frequentes")
    perguntas_exemplo = [
        "O que é airflow?",
        "O que é docker?",
        "Airflow é integrado com quais tecnologias?"
    ]
    for p in perguntas_exemplo:
        if st.sidebar.button(p, key=f"btn_{p}"):
            submit_question(p, top_k)
            st.rerun()

# --- AREA PRINCIPAL ---
theme = st.session_state.tema_interface
appearance = THEME_DETAILS[theme]
st.markdown(
    f"""
    <style>
    :root {{ --askdata-accent: {appearance['accent']}; }}
    [data-testid="stAppViewContainer"] {{ background: #12171f; }}
    [data-testid="stSidebar"] {{ background: #252932; }}
    [data-testid="stChatMessage"] {{
        background: #202a35;
        border: 1px solid #334252;
        border-radius: 10px;
    }}
    [data-testid="stChatMessage"] [data-testid="stVerticalBlockBorderWrapper"] {{
        background: #1d2631;
        border-color: #344555;
    }}
    [data-testid="stExpander"] {{ border-color: #425467; }}
    [data-testid="stSlider"] [role="group"] > [data-orientation="horizontal"] > div:first-child {{
        background: linear-gradient(to right,
            var(--askdata-accent) 0%,
            var(--askdata-accent) {(top_k - 1) * 25}%,
            #4f5a68 {(top_k - 1) * 25}%,
            #4f5a68 100%) !important;
    }}
    [data-testid="stSlider"] [role="group"] > [data-orientation="horizontal"] > div:nth-child(2) {{
        background: var(--askdata-accent) !important;
    }}
    [data-testid="stSliderThumbValue"] {{ color: var(--askdata-accent) !important; }}
    [data-testid="stRadioOption"][data-selected="true"] > div > div:first-child {{
        background: var(--askdata-accent) !important;
    }}
    [data-testid="stSidebar"] button[kind="secondary"] {{
        border-color: #45586a;
        background: #303b48;
    }}
    [class*="st-key-topic_"] button,
    [class*="st-key-next_"] button {{
        border-color: {appearance['accent_dark']};
        background: #2b3744;
    }}
    .askdata-mode-label {{
        color: var(--askdata-accent);
        font-size: .8rem;
        font-weight: 700;
        letter-spacing: .08em;
        margin-bottom: .4rem;
    }}
    </style>
    <div class="askdata-mode-label">{appearance['number']} / {theme.upper()}</div>
    """,
    unsafe_allow_html=True,
)
st.title(appearance["title"])
st.caption(appearance["description"])

if theme == "Estudo guiado":
    topics = (
        ("Airflow", "O que é Airflow?"),
        ("Docker", "O que é Docker?"),
        ("Docker Compose", "Como funciona o Docker Compose?"),
    )
    for column, (label, question) in zip(st.columns(3), topics):
        with column:
            if st.button(label, key=f"topic_{label}", width="stretch"):
                submit_question(question, top_k)
                st.rerun()

for message in st.session_state.messages:
    render_message(message, theme)

if theme == "Estudo guiado" and st.session_state.messages:
    st.markdown("**Continue explorando**")
    next_questions = (
        "Qual a diferença entre Docker e máquina virtual?",
        "Como funciona o Docker Compose?",
        "Como executar o Airflow localmente com Docker?",
    )
    for column, question in zip(st.columns(3), next_questions):
        with column:
            if st.button(question, key=f"next_{question}", width="stretch"):
                submit_question(question, top_k)
                st.rerun()

if prompt := st.chat_input("Digite sua pergunta técnica aqui..."):
    with st.spinner("Buscando no banco vetorial e formulando resposta..."):
        submit_question(prompt, top_k)
    st.rerun()
