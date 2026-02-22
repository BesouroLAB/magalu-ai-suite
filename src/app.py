import streamlit as st
import os
import sys
import csv
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Garante que a raiz do projeto esteja no path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent import RoteiristaAgent

load_dotenv()

# Configuração da página
st.set_page_config(page_title="Roteirista Magalu AI", page_icon="🎬", layout="wide")

st.title("🎬 Roteirista Magalu AI")
st.markdown("Crie roteiros de vídeos de produtos no padrão Breno em segundos.")

# --- Configuração da API Key ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key
    except Exception:
        pass

if not api_key:
    st.warning("⚠️ API Key do Gemini não encontrada.")
    api_key_input = st.text_input("Cole sua GEMINI_API_KEY aqui:", type="password")
    if st.button("Salvar API Key"):
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(f"GEMINI_API_KEY={api_key_input}\n")
        os.environ["GEMINI_API_KEY"] = api_key_input
        st.success("✅ Chave salva! Recarregue a página.")
        st.stop()
    st.stop()

# --- Separador de fichas ---
SEPARADOR = "---"

# --- Entrada de Dados ---
st.subheader("📋 Fichas Técnicas dos Produtos")
st.markdown(
    f"Cole as fichas técnicas abaixo. Para gerar **vários roteiros de uma vez**, "
    f"separe cada produto com uma linha contendo apenas `{SEPARADOR}`."
)

fichas_input = st.text_area(
    "Fichas Técnicas:",
    height=350,
    placeholder=(
        "TÍTULO: Fogão Consul 4 Bocas CFO4TAR\n"
        "DESCRIÇÃO: Fogão com acendimento automático...\n"
        "FICHA TÉCNICA:\n"
        "- Bocas: 4\n"
        "- Forno: 58 litros\n"
        "---\n"
        "TÍTULO: Smart TV 55\" LG OLED\n"
        "DESCRIÇÃO: TV com resolução 4K...\n"
        "FICHA TÉCNICA:\n"
        "- Tela: 55 polegadas\n"
        "- Resolução: 4K"
    )
)

btn_gerar = st.button("🚀 Gerar Roteiro(s) Mágico(s)")

# --- Processamento ---
if btn_gerar and fichas_input.strip():
    # Separa múltiplas fichas pelo separador
    fichas_raw = fichas_input.split(SEPARADOR)
    fichas = [f.strip() for f in fichas_raw if f.strip()]

    if not fichas:
        st.error("Nenhuma ficha técnica encontrada.")
    else:
        st.info(f"🔍 {len(fichas)} produto(s) detectado(s). Gerando roteiros...")
        roteiros = []

        try:
            agent = RoteiristaAgent()

            for i, ficha in enumerate(fichas):
                with st.spinner(f"🧠 Gerando roteiro {i+1}/{len(fichas)}..."):
                    roteiro = agent.gerar_roteiro(ficha)
                    roteiros.append({
                        "ficha": ficha,
                        "roteiro_original": roteiro,
                    })

            st.session_state['roteiros'] = roteiros
            st.success(f"✅ {len(roteiros)} roteiro(s) gerado(s) com sucesso!")

        except Exception as e:
            st.error(f"Erro ao conectar com a IA: {e}")

# --- Exibição, Edição e Cópia dos Roteiros ---
if 'roteiros' in st.session_state and st.session_state['roteiros']:
    st.divider()
    st.subheader("📝 Revisão dos Roteiros (Human-in-the-loop)")

    for idx, item in enumerate(st.session_state['roteiros']):
        # Extrai nome curto do produto para o título
        linhas = item['ficha'].split('\n')
        titulo_curto = linhas[0][:60] if linhas else f"Produto {idx+1}"

        with st.expander(f"📦 {titulo_curto}", expanded=(idx == 0)):
            # Editor do roteiro
            edited = st.text_area(
                "Edite o roteiro abaixo:",
                value=item['roteiro_original'],
                height=350,
                key=f"editor_{idx}"
            )

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("✅ Aprovar e Salvar", key=f"approve_{idx}"):
                    log_file = "feedback_log.csv"
                    file_exists = os.path.isfile(log_file)

                    with open(log_file, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        if not file_exists:
                            writer.writerow(["Data", "Ficha_Tecnica", "Roteiro_Gerado_IA", "Roteiro_Aprovado_Humano"])
                        writer.writerow([
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            item['ficha'],
                            item['roteiro_original'],
                            edited
                        ])
                    st.success(f"🎉 Roteiro '{titulo_curto}' aprovado e salvo!")

            with col2:
                # Botão de copiar usando st.code (permite copiar fácil)
                if st.button("📋 Mostrar pra Copiar", key=f"copy_{idx}"):
                    st.code(edited, language=None)

            with col3:
                if st.button("🔄 Regenerar", key=f"regen_{idx}"):
                    with st.spinner("Regenerando..."):
                        try:
                            agent = RoteiristaAgent()
                            novo = agent.gerar_roteiro(item['ficha'])
                            st.session_state['roteiros'][idx]['roteiro_original'] = novo
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")

    # --- Ações em lote ---
    st.divider()
    col_batch1, col_batch2 = st.columns(2)

    with col_batch1:
        if st.button("✅ Aprovar TODOS os Roteiros"):
            log_file = "feedback_log.csv"
            file_exists = os.path.isfile(log_file)
            with open(log_file, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Data", "Ficha_Tecnica", "Roteiro_Gerado_IA", "Roteiro_Aprovado_Humano"])
                for idx, item in enumerate(st.session_state['roteiros']):
                    edited = st.session_state.get(f"editor_{idx}", item['roteiro_original'])
                    writer.writerow([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        item['ficha'],
                        item['roteiro_original'],
                        edited
                    ])
            st.success(f"🎉 {len(st.session_state['roteiros'])} roteiro(s) aprovados e salvos!")

    with col_batch2:
        if st.button("🔄 Limpar e Gerar Novos"):
            del st.session_state['roteiros']
            st.rerun()
