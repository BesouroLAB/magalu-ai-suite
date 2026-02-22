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

# --- Configuração Geral e Injeção de CSS (Design Magalu) ---
st.set_page_config(page_title="Roteirista Magalu", page_icon="🛍️", layout="wide", initial_sidebar_state="expanded")

MAGALU_CSS = """
<style>
    /* Cores Magalu: Azul #0086ff, Fundo leve, Fontes limpas */
    :root {
        --mglu-blue: #0086ff;
        --mglu-dark: #333333;
    }
    
    /* Botões Principais */
    .stButton > button {
        background-color: var(--mglu-blue);
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    .stButton > button:hover {
        background-color: #006bce;
        transform: scale(1.02);
    }
    
    /* Headers e Títulos */
    h1, h2, h3 {
        color: var(--mglu-dark) !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Expander (Abas de cada roteiro) */
    .streamlit-expanderHeader {
        background-color: #f7f9fa;
        border-radius: 8px;
        font-weight: bold;
        color: var(--mglu-blue);
    }
    
    /* Limpar topo */
    .block-container {
        padding-top: 2rem;
    }
</style>
"""
st.markdown(MAGALU_CSS, unsafe_allow_html=True)

# --- Gestão de Estado (Workflow) ---
if 'step' not in st.session_state:
    st.session_state['step'] = 'input'

def reset_workflow():
    st.session_state['step'] = 'input'
    if 'roteiros' in st.session_state:
        del st.session_state['roteiros']


# --- SIDEBAR (Configuração e Sujeira fora do caminho) ---
with st.sidebar:
    st.image("https://logopng.com.br/logos/magazine-luiza-22.png", width=150)
    st.title("⚙️ Configurações")
    
    api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    
    if not api_key:
        st.error("🔴 API Key não encontrada!")
        api_key_input = st.text_input("Cole sua chave Gemini:", type="password")
        if st.button("Salvar Chave"):
            with open('.env', 'w', encoding='utf-8') as f:
                f.write(f"GEMINI_API_KEY={api_key_input}\n")
            os.environ["GEMINI_API_KEY"] = api_key_input
            st.success("Salva! Pressione F5.")
            st.stop()
        st.stop()
    else:
        st.success("🟢 API Conectada (Gemini 2.5 Flash)")
        os.environ["GEMINI_API_KEY"] = api_key

    st.divider()
    st.markdown("### 📋 Como Usar:")
    st.caption("1. Cole as fichas técnicas na tela principal.")
    st.caption("2. Para colar vários produtos, separe-os pulando uma linha e digitando `---`")
    st.caption("3. Clique em Gerar, revise e aprove!")

    if st.session_state['step'] == 'review':
        st.divider()
        st.button("🔙 Voltar para Colar Novo Produto", on_click=reset_workflow, use_container_width=True)


# --- MAIN AREA: Passo 1 (Ingestão de Fichas) ---
if st.session_state['step'] == 'input':
    st.title("🎬 Roteirista Magalu AI")
    st.markdown("Transforme **fichas técnicas** em **roteiros aprovados pelo Breno** instantaneamente.")
    
    SEPARADOR = "---"
    
    fichas_input = st.text_area(
        "✍️ Cole as Fichas Técnicas aqui:",
        height=350,
        placeholder="TÍTULO: Smart TV 55 LG\nDESCRIÇÃO: Assistir TV nunca foi tão incrível...\nFICHA TÉCNICA:\n- OLED\n- 4K\n\n---\n\nTÍTULO: Geladeira Brastemp 400L\n..."
    )
    
    if st.button("🚀 Gerar Roteiro(s) Mágico(s)", use_container_width=True):
        if not fichas_input.strip():
            st.warning("⚠️ Cole pelo menos uma ficha técnica antes de gerar.")
        else:
            fichas_raw = fichas_input.split(SEPARADOR)
            fichas = [f.strip() for f in fichas_raw if f.strip()]
            
            with st.spinner(f"🧠 A Lu está escrevendo {len(fichas)} roteiro(s)..."):
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
                    st.session_state['step'] = 'review'
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro na geração: {e}")

# --- MAIN AREA: Passo 2 (Foco na Revisão) ---
elif st.session_state['step'] == 'review':
    st.title("📝 Revisão do Editor")
    st.markdown("Faça os ajustes finais, aprove copie o texto bruto para o seu doc final.")
    
    for idx, item in enumerate(st.session_state['roteiros']):
        linhas = item['ficha'].split('\n')
        titulo_curto = linhas[0][:60] if linhas else f"Produto {idx+1}"

        with st.expander(f"📦 {titulo_curto}", expanded=True):
            tab_view, tab_edit = st.tabs(["👁️ Visualização Renderizada", "✏️ Editor de Texto Bruto (Para Copiar)"])

            with tab_view:
                st.markdown(item['roteiro_original'])

            with tab_edit:
                edited = st.text_area(
                    "Ajuste as vírgulas, conectivos ou tom aqui:",
                    value=item['roteiro_original'],
                    height=300,
                    key=f"editor_{idx}"
                )
                st.info("💡 Dica: Copie o texto acima direto para o Word. Os `**` vão virar negrito automático se você usar colar sem formatação, ou em editores Markdown.")

            col1, col2, col3 = st.columns([1, 1, 1])

            with col1:
                if st.button("✅ Aprovar no Bano de Dados", key=f"approve_{idx}", use_container_width=True):
                    log_file = "feedback_log.csv"
                    file_exists = os.path.isfile(log_file)
                    with open(log_file, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        if not file_exists:
                            writer.writerow(["Data", "Ficha_Tecnica", "Roteiro_Gerado_IA", "Roteiro_Aprovado_Humano"])
                        edited_val = st.session_state.get(f"editor_{idx}", item['roteiro_original'])
                        writer.writerow([
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            item['ficha'],
                            item['roteiro_original'],
                            edited_val
                        ])
                    st.success("🎉 Roteiro injetado no cérebro da IA para aprendizado!")

            with col2:
                if st.button("📋 Exibir Código de Cópia", key=f"copy_{idx}", use_container_width=True):
                    edited_val = st.session_state.get(f"editor_{idx}", item['roteiro_original'])
                    st.code(edited_val, language="markdown")

            with col3:
                if st.button("🔄 A IA Alucinou? Gerar de Novo", key=f"regen_{idx}", use_container_width=True):
                    with st.spinner("Refazendo roteiro..."):
                        agent = RoteiristaAgent()
                        novo = agent.gerar_roteiro(item['ficha'])
                        st.session_state['roteiros'][idx]['roteiro_original'] = novo
                        st.rerun()

    st.divider()
    if st.button("✅ Terminei de Revisar! Limpar Tudo e Voltar", type="primary", use_container_width=True):
        reset_workflow()
        st.rerun()
