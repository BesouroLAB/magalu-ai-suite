import streamlit as st
import os
import sys
import csv
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Garante que a raiz do projeto esteja no path (necessário para Streamlit Cloud)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent import RoteiristaAgent

load_dotenv()

# Configuração da página
st.set_page_config(page_title="Roteirista Magalu AI", page_icon="🎬", layout="wide")

st.title("🎬 Roteirista Magalu AI")
st.markdown("Crie roteiros de vídeos de produtos no padrão Breno em segundos.")

# --- Configuração da API Key ---
api_key = os.environ.get("GEMINI_API_KEY")

# Tenta ler dos secrets do Streamlit Cloud como fallback
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

# --- Abas de Entrada ---
st.subheader("📋 Dados do Produto")

tab_manual, tab_url = st.tabs(["✍️ Colar Ficha Técnica (Recomendado)", "🔗 Tentar via URL (Beta)"])

with tab_manual:
    st.markdown("Cole abaixo o **nome do produto**, a **descrição do fabricante** e a **ficha técnica** copiados do site do Magalu:")
    product_data_manual = st.text_area(
        "Ficha Técnica do Produto:",
        height=250,
        placeholder="Ex:\nTÍTULO: Fogão Consul 4 Bocas CFO4TAR\nDESCRIÇÃO: Fogão com acendimento automático...\nFICHA TÉCNICA:\n- Bocas: 4\n- Forno: 58 litros\n- Cor: Branco\n..."
    )
    btn_manual = st.button("🚀 Gerar Roteiro Mágico", key="btn_manual")

with tab_url:
    st.markdown("⚠️ O site do Magalu usa proteção anti-bot. Se não funcionar, use a aba **Colar Ficha Técnica**.")
    url_input = st.text_input("🔗 Cole o link do produto Magalu:")
    btn_url = st.button("🚀 Tentar Gerar via URL", key="btn_url")

# --- Processamento ---
scraped_text = None

if btn_manual and product_data_manual:
    scraped_text = product_data_manual

if btn_url and url_input:
    with st.spinner("Tentando extrair dados do site..."):
        try:
            from src.scraper import scrape_magalu_product
            result = scrape_magalu_product(url_input)
            if "Título não encontrado" in result or "Erro ao raspar" in result:
                st.warning("⚠️ O Magalu bloqueou a extração automática. Copie a ficha técnica do produto e cole na aba 'Colar Ficha Técnica'.")
            else:
                scraped_text = result
                with st.expander("Ver dados extraídos"):
                    st.text(result)
        except Exception as e:
            st.error(f"Erro no scraping: {e}")
            st.info("💡 Use a aba 'Colar Ficha Técnica' como alternativa.")

if scraped_text:
    try:
        with st.spinner("🧠 O Cérebro está pensando... (Gemini 2.5 Flash)"):
            agent = RoteiristaAgent()
            roteiro_gerado = agent.gerar_roteiro(scraped_text)
            st.session_state['roteiro_original'] = roteiro_gerado
            st.session_state['dados_produto'] = scraped_text
    except Exception as e:
        st.error(f"Erro ao conectar com a IA: {e}")

# --- Edição e Feedback Loop ---
if 'roteiro_original' in st.session_state:
    st.divider()
    st.subheader("📝 Revisão do Editor (Human-in-the-loop)")
    edited_text = st.text_area(
        "Faça os ajustes finais abaixo antes de aprovar:",
        value=st.session_state['roteiro_original'],
        height=400
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Aprovar e Salvar no Log"):
            log_file = "feedback_log.csv"
            file_exists = os.path.isfile(log_file)

            with open(log_file, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Data", "Dados_Produto", "Roteiro_Gerado_IA", "Roteiro_Aprovado_Humano"])

                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    st.session_state.get('dados_produto', ''),
                    st.session_state['roteiro_original'],
                    edited_text
                ])

            st.success("🎉 Roteiro aprovado e salvo no banco de dados de aprendizado!")

            try:
                df = pd.read_csv(log_file)
                st.dataframe(df.tail(3))
            except Exception:
                pass

    with col2:
        if st.button("🔄 Gerar Novo Roteiro"):
            del st.session_state['roteiro_original']
            st.rerun()
