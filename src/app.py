import streamlit as st
import os
import csv
import pandas as pd
from datetime import datetime
from dotenv import set_key
from src.scraper import scrape_magalu_product
from src.agent import RoteiristaAgent

# Configuração da página
st.set_page_config(page_title="Roteirista Magalu AI", page_icon="🤖", layout="wide")

st.title("🎬 Roteirista Magalu AI (MVP)")
st.markdown("Crie roteiros de vídeos de produtos aprovados pelo Breno em segundos.")

# --- Configuração da API Key via UI ---
if "GEMINI_API_KEY" not in os.environ and not st.secrets.get("GEMINI_API_KEY"):
    st.warning("⚠️ API Key do Gemini não encontrada.")
    api_key_input = st.text_input("Cole sua GEMINI_API_KEY aqui:", type="password")
    if st.button("Salvar API Key localmente"):
        # Salva no .env para reuso futuro local
        with open('.env', 'a') as f:
             f.write(f"\nGEMINI_API_KEY={api_key_input}\n")
        # Força o load para a sessão atual
        os.environ["GEMINI_API_KEY"] = api_key_input
        st.success("Chave salva! Recarregue a página.")
        st.stop()

# --- Fluxo Principal ---
url_input = st.text_input("🔗 Cole o link do produto Magalu:")

if st.button("🚀 Gerar Roteiro Mágico"):
    if not url_input:
        st.error("Por favor, insira um link válido.")
    else:
        with st.spinner("Extraindo dados do site... (Scraping)"):
            scraped_text = scrape_magalu_product(url_input)
            
            # Mostra o que foi extraído num expander (bom pra debug)
            with st.expander("Ver dados extraídos pelo Scraper"):
                st.text(scraped_text)
                
        if "Erro ao raspar" not in scraped_text:
            try:
                with st.spinner("O Cérebro está pensando... (Gemini 1.5 Pro)"):
                    agent = RoteiristaAgent()
                    roteiro_gerado = agent.gerar_roteiro(scraped_text)
                    
                    # Salva no state para a edição
                    st.session_state['roteiro_original'] = roteiro_gerado
                    st.session_state['url'] = url_input
                    
            except Exception as e:
                st.error(f"Erro ao conectar com a IA: {e}")

# --- Edição e Feedback Loop ---
if 'roteiro_original' in st.session_state:
    st.subheader("📝 Revisão do Editor (Human-in-the-loop)")
    edited_text = st.text_area(
        "Faça os ajustes finais abaixo antes de aprovar:", 
        value=st.session_state['roteiro_original'],
        height=400
    )
    
    if st.button("✅ Aprovar e Salvar no Log (Feedback Loop)"):
        # Salva em CSV
        log_file = "feedback_log.csv"
        file_exists = os.path.isfile(log_file)
        
        with open(log_file, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Data", "URL", "Roteiro_Gerado_IA", "Roteiro_Aprovado_Humano"])
            
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                st.session_state['url'],
                st.session_state['roteiro_original'],
                edited_text
            ])
            
        st.success("🎉 Roteiro aprovado e salvo no banco de dados de aprendizado!")
        
        # Mostra o log para o usuário ver crescendo
        try:
             df = pd.read_csv(log_file)
             st.dataframe(df.tail(3))
        except:
             pass
