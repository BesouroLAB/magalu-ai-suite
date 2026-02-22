import streamlit as st
import os
import sys
import csv
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.agent import RoteiristaAgent

load_dotenv()

import streamlit as st
import os
import sys
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.agent import RoteiristaAgent

load_dotenv()

# --- Configuração Geral e Injeção de CSS (Dark Mode Design) ---
st.set_page_config(page_title="Gerador da Lu", page_icon="🛍️", layout="wide", initial_sidebar_state="expanded")

DARK_MODE_CSS = """
<style>
    /* Tema Escuro estilo Dashboard Premium */
    :root {
        --bg-main: #0B0E14;
        --bg-card: #151A23;
        --mglu-blue: #0086ff;
        --mglu-purple: #8142FF;
        --text-primary: #f0f0f0;
        --text-muted: #8b92a5;
    }
    
    /* Força Dark Mode global na div block-container */
    .stApp > header {
        background-color: transparent;
    }
    .stApp {
        background-color: var(--bg-main) !important;
        color: var(--text-primary) !important;
    }

    /* Títulos e Textos globais */
    h1, h2, h3, p, span, div {
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif;
    }
    
    .stMarkdown, .stText {
        color: var(--text-muted) !important;
    }
    
    /* Inputs e textareas escuros */
    .stTextArea > div > div > textarea, .stTextInput > div > div > input {
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid #2A3241 !important;
        border-radius: 8px;
    }
    .stTextArea > div > div > textarea:focus, .stTextInput > div > div > input:focus {
        border-color: var(--mglu-blue) !important;
        box-shadow: 0 0 0 1px var(--mglu-blue) !important;
    }
    
    /* Botões Principais */
    .stButton > button {
        background-color: var(--mglu-purple) !important; /* Roxo do print */
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stButton > button:hover {
        background-color: #6a35d6 !important;
        transform: scale(1.02) !important;
    }
    
    /* Expander e Abas / fundo dos cards */
    .streamlit-expanderHeader {
        background-color: var(--bg-card) !important;
        border-radius: 8px;
        font-weight: bold;
        color: var(--mglu-blue) !important;
        border: 1px solid #2A3241;
    }
    .streamlit-expanderContent {
        background-color: transparent !important;
        border: 1px solid #2A3241;
        border-top: none;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: var(--bg-card) !important;
        border-right: 1px solid #2A3241;
    }
    
    .block-container {
        padding-top: 2rem;
    }
</style>
"""
st.markdown(DARK_MODE_CSS, unsafe_allow_html=True)


# --- SIDEBAR (Configuração) ---
with st.sidebar:
    st.image("https://logopng.com.br/logos/magazine-luiza-22.png", width=150)
    st.markdown("### ⚙️ Configurações API")
    
    api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    supabase_url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")
    
    if not api_key:
        api_key_input = st.text_input("🔑 Cole sua chave Gemini:", type="password")
        if st.button("Salvar Chave Gemini"):
            with open('.env', 'a', encoding='utf-8') as f:
                f.write(f"\nGEMINI_API_KEY={api_key_input}")
            os.environ["GEMINI_API_KEY"] = api_key_input
            st.success("Salva! Pressione F5.")
            st.stop()
        st.stop()
    else:
        st.success("🟢 API Gemini Conectada")
        os.environ["GEMINI_API_KEY"] = api_key

    if not supabase_url or not supabase_key:
        st.divider()
        st.error("🔴 Supabase Não Conectado")
        supa_url_input = st.text_input("🔗 Supabase URL:")
        supa_key_input = st.text_input("🔑 Supabase API Key:", type="password")
        if st.button("Conectar Nuvem"):
            with open('.env', 'a', encoding='utf-8') as f:
                f.write(f"\nSUPABASE_URL={supa_url_input}")
                f.write(f"\nSUPABASE_KEY={supa_key_input}")
            st.success("Banco salvo! Pressione F5.")
            st.stop()
    else:
        st.success("🟢 Nuvem Conectada (Supabase)")
        
        # Inicia cliente Supabase se estiver conectado
        try:
            supabase: Client = create_client(supabase_url, supabase_key)
            st.session_state['supabase_client'] = supabase
        except Exception as e:
            st.error(f"Erro ao conectar supabase: {e}")

    st.divider()
    st.markdown("### 📋 Como Usar:")
    st.caption("1. Cole as fichas técnicas no painel esquerdo.")
    st.caption("2. Para gerar vários produtos, clique em '➕ Adicionar Produto'.")
    st.caption("3. Na mesa de trabalho à direita, edite, copie ou aprove os textos gerados.")

st.title("Gerador de Roteiros da Lu")
st.markdown("<span style='color: #0086ff; font-weight: bold; font-size: 14px; margin-left: 10px'>V4.0 SÉRIE 4</span>", unsafe_allow_html=True)

# Layout de Dashboard (Duas Colunas)
col_left, col_right = st.columns([1.2, 2.5], gap="medium")

with col_left:
    st.subheader("Novo Roteiro")
    st.markdown("<p style='font-size: 14px; color: #8b92a5'>Adicione os produtos que deseja gerar:</p>", unsafe_allow_html=True)
    
    if 'num_fichas' not in st.session_state:
        st.session_state['num_fichas'] = 1
        
    fichas_informadas = []
    
    for i in range(st.session_state['num_fichas']):
        val = st.text_area(
            f"Ficha Técnica do Produto {i+1}",
            height=200,
            key=f"ficha_input_{i}",
            placeholder="TÍTULO: Smart TV 55 LG\nDESCRIÇÃO: Assistir TV nunca foi tão incrível...\nFICHA TÉCNICA:\n- OLED\n- 4K"
        )
        fichas_informadas.append(val)
        
    col_add, col_rem = st.columns(2)
    with col_add:
        if st.button("➕ Adicionar Produto", use_container_width=True):
            st.session_state['num_fichas'] += 1
            st.rerun()
    with col_rem:
        if st.session_state['num_fichas'] > 1:
            if st.button("➖ Remover Último", use_container_width=True):
                st.session_state['num_fichas'] -= 1
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🚀 Gerar Roteiros Mágicos", use_container_width=True):
        fichas = [f.strip() for f in fichas_informadas if f.strip()]
        
        if not fichas:
            st.warning("⚠️ Cole pelo menos uma ficha técnica antes de gerar.")
        else:
            with st.spinner(f"Processando {len(fichas)} roteiro(s)..."):
                try:
                    agent = RoteiristaAgent()
                    roteiros = []
                    for ficha in fichas:
                        roteiro = agent.gerar_roteiro(ficha)
                        roteiros.append({
                            "ficha": ficha,
                            "roteiro_original": roteiro,
                        })
                    st.session_state['roteiros'] = roteiros
                except Exception as e:
                    st.error(f"Erro na geração: {e}")


with col_right:
    st.subheader("Mesa de Trabalho")
    
    if 'roteiros' in st.session_state and st.session_state['roteiros']:
        for idx, item in enumerate(st.session_state['roteiros']):
            linhas = item['ficha'].split('\n')
            titulo_curto = linhas[0][:60] if linhas else f"Produto {idx+1}"

            with st.expander(f"📦 {titulo_curto}", expanded=True):
                tab_view, tab_edit = st.tabs(["👁️ Roteiro Final (Visualização)", "✏️ Código Original (Markdown)"])

                with tab_view:
                    # Impede que o Markdown converta "traço + espaço" em bullet points (círculos)
                    roteiro_view = item['roteiro_original'].replace('\n- ', '\n\- ')
                    if roteiro_view.startswith('- '):
                        roteiro_view = '\- ' + roteiro_view[2:]
                        
                    st.markdown(f"<div style='background-color: var(--bg-card); padding: 15px; border-radius: 8px; border: 1px solid #2A3241;'>{roteiro_view}</div>", unsafe_allow_html=True)

                with tab_edit:
                    edited = st.text_area(
                        "Faça ajustes finos. O Markdown (`**`) deve ser preservado para ser copiado ao Word.",
                        value=item['roteiro_original'],
                        height=250,
                        key=f"editor_{idx}"
                    )
                    
                    st.caption("Ações Rápidas:")
                    col_actions_1, col_actions_2, col_actions_3 = st.columns(3)
                    
                    with col_actions_1:
                        if st.button("📋 Copiar (Texto Limpo)", key=f"copy_{idx}", use_container_width=True):
                            edited_val = st.session_state.get(f"editor_{idx}", item['roteiro_original'])
                            st.code(edited_val, language="markdown")
                    
                    with col_actions_2:
                        if st.button("✅ Enviar P/ Supabase", type="primary", key=f"approve_{idx}", use_container_width=True):
                            edited_val = st.session_state.get(f"editor_{idx}", item['roteiro_original'])
                            if 'supabase_client' in st.session_state:
                                sp_client = st.session_state['supabase_client']
                                try:
                                    # Usa UTC now (sem o import timezone, a string funciona pro supabase timestamp)
                                    sp_client.table("roteiros_aprovados").insert({
                                        "ficha_tecnica": item['ficha'],
                                        "roteiro_original_ia": item['roteiro_original'],
                                        "roteiro_editado_humano": edited_val
                                    }).execute()
                                    st.success("✅ Treinamento injetado na Base Nuvem!")
                                except Exception as e:
                                    st.error(f"❌ Erro ao enviar ao Supabase: {e}")
                            else:
                                st.error("Conecte o Supabase no painel lateral primeiro.")
                    
                    with col_actions_3:
                        if st.button("🔄 Refazer Roteiro", key=f"regen_{idx}", use_container_width=True):
                            with st.spinner("Regerando..."):
                                agent = RoteiristaAgent()
                                novo = agent.gerar_roteiro(item['ficha'])
                                st.session_state['roteiros'][idx]['roteiro_original'] = novo
                                st.rerun()

        if st.button("🗑️ Limpar Mesa de Trabalho", use_container_width=True):
            del st.session_state['roteiros']
            st.rerun()
    else:
        st.markdown(
            "<div style='display: flex; height: 450px; align-items: center; justify-content: center; border: 2px dashed #2A3241; border-radius: 8px; color: #8b92a5; text-align: center; padding: 20px'>"
            "Cole a ficha técnica no painel esquerdo e clique em Gerar Roteiros Mágicos.<br><br>Os roteiros aparecerão aqui prontos para edição!"
            "</div>", 
            unsafe_allow_html=True
        )
