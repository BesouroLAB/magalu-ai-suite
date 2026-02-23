import streamlit as st
import os
import sys
import pandas as pd
from datetime import datetime
import pytz
from dotenv import load_dotenv
from supabase import create_client, Client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.agent import RoteiristaAgent
from src.scraper import scrape_with_gemini, parse_codes
from src.exporter import export_roteiro_docx, format_for_display, export_all_roteiros_zip
from src.jsonld_generator import export_jsonld_string, wrap_in_script_tag

load_dotenv()

# --- CONFIGURAÇÃO GERAL ---
st.set_page_config(page_title="Magalu AI Suite", page_icon="🛍️", layout="wide", initial_sidebar_state="expanded")

DARK_MODE_CSS = """
<style>
    /* Tema Escuro Magalu Premium */
    :root {
        --bg-main: #020710; /* Azul quase preto */
        --bg-card: #050e1d; /* Azul ultra escuro */
        --mglu-blue: #0086ff; /* Azul Magalu Principal */
        --text-primary: #f0f0f0;
        --text-muted: #8b92a5;
    }
    
    .stApp > header { background-color: transparent; }
    .stApp { background-color: var(--bg-main) !important; color: var(--text-primary) !important; }

    h1 { font-size: 1.8rem !important; font-weight: 700 !important; color: #ffffff !important; letter-spacing: 0.5px; margin-bottom: 0.5rem !important; }
    h2 { font-size: 1.4rem !important; font-weight: 600 !important; color: #e0e6f0 !important; margin-bottom: 0.4rem !important; }
    h3 { font-size: 1.15rem !important; font-weight: 600 !important; color: #b0bdd0 !important; margin-bottom: 0.3rem !important; }
    h4 { font-size: 1.0rem !important; font-weight: 500 !important; color: var(--mglu-blue) !important; margin-bottom: 0.2rem !important; }
    p, span, div, label { color: var(--text-primary) !important; font-family: 'Inter', sans-serif; font-size: 0.92rem !important; }
    .stMarkdown, .stText { color: var(--text-muted) !important; font-size: 0.9rem !important; }
    
    .stTextArea > div > div > textarea, .stTextInput > div > div > input, .stSelectbox > div > div > div {
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid #0a1b33 !important;
        border-radius: 8px;
        font-size: 0.9rem !important;
    }
    .stTextArea > div > div > textarea:focus, .stTextInput > div > div > input:focus {
        border-color: var(--mglu-blue) !important;
        box-shadow: 0 0 0 1px var(--mglu-blue) !important;
    }
    
    .stButton > button[data-baseweb="button"] {
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    /* Botões Primários (Global) */
    button[kind="primary"], .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button, .stFormSubmitButton > button {
        background-color: var(--mglu-blue) !important;
        color: white !important;
        border: none !important;
        box-shadow: none !important;
    }
    button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] > button:hover, .stFormSubmitButton > button:hover {
        background-color: #0066cc !important;
        transform: scale(1.02) !important;
    }
    
    /* Botões Secundários */
    button[kind="secondary"] {
        background-color: #001f4d !important;
        color: var(--text-primary) !important;
        border: 1px solid #003380 !important;
    }
    button[kind="secondary"]:hover {
        background-color: #003380 !important;
        border-color: var(--mglu-blue) !important;
    }
    
    .streamlit-expanderHeader {
        background-color: var(--bg-card) !important;
        border-radius: 8px;
        font-weight: bold;
        color: var(--mglu-blue) !important;
        border: 1px solid #0a1b33;
    }
    .streamlit-expanderContent {
        background-color: transparent !important;
        border: 1px solid #0a1b33;
        border-top: none;
    }
    
    [data-testid="stSidebar"] {
        background-color: var(--bg-card) !important;
        border-right: 1px solid #0a1b33;
    }
    
    /* Transparência progressiva na logo (fade suave em todas as bordas) */
    [data-testid="stSidebar"] [data-testid="stImage"] img {
        -webkit-mask-image: linear-gradient(to bottom, transparent 0%, black 15%, black 35%, transparent 100%),
                            linear-gradient(to right, transparent 0%, black 10%, black 90%, transparent 100%);
        -webkit-mask-composite: source-in;
        mask-image: linear-gradient(to bottom, transparent 0%, black 15%, black 35%, transparent 100%),
                    linear-gradient(to right, transparent 0%, black 10%, black 90%, transparent 100%);
        mask-composite: intersect;
    }
    
    .block-container { padding-top: 2rem; }
</style>
"""
st.markdown(DARK_MODE_CSS, unsafe_allow_html=True)


# --- LOGIN GATE ---
def check_login():
    """Tela de login com persistência simples."""
    auth_file = os.path.join(os.path.dirname(__file__), ".auth_token")
    
    # 1. Tenta recuperar sessão salva
    if 'authenticated' not in st.session_state:
        if os.path.exists(auth_file):
            try:
                with open(auth_file, "r") as f:
                    saved_token = f.read().strip()
                # Token simples: concatenamos usuario:senha (não é o mais seguro, mas atende ao uso individual)
                valid_user = os.environ.get("APP_USER", "admin").strip()
                valid_pwd = os.environ.get("APP_PASSWORD", "admin").strip()
                if saved_token == f"{valid_user}:{valid_pwd}":
                    st.session_state['authenticated'] = True
            except:
                pass

    if st.session_state.get('authenticated'):
        return True
    
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        st.markdown("")
        st.markdown("")
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <span style="color: #0086ff; font-weight: 800; font-size: 20px; letter-spacing: 3px;">MAGALU</span><br>
            <span style="color: white; font-weight: 300; font-size: 42px; letter-spacing: 1px;">AI Suite</span>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            user = st.text_input("Usuário:", placeholder="admin")
            pwd = st.text_input("Senha:", type="password", placeholder="••••••")
            remember = st.checkbox("Lembrar de mim", value=True)
            submitted = st.form_submit_button("🔐 Entrar", use_container_width=True, type="primary")
            
            if submitted:
                valid_user = os.environ.get("APP_USER", "admin").strip()
                valid_pwd = os.environ.get("APP_PASSWORD", "admin").strip()
                
                if user.strip() == valid_user and pwd.strip() == valid_pwd:
                    st.session_state['authenticated'] = True
                    if remember:
                        with open(auth_file, "w") as f:
                            f.write(f"{valid_user}:{valid_pwd}")
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos.")
        
        st.caption("Acesso restrito à equipe de conteúdo Magalu.")
    return False

if not check_login():
    st.stop()


# --- FUNÇÕES SUPABASE E AUXILIARES ---
def init_supabase():
    url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")
    if url and key:
        return create_client(url, key)
    return None

def convert_to_sp_time(utc_datetime_str):
    """Converte string UTC do Supabase para o fuso de São Paulo formatado."""
    if not utc_datetime_str:
        return ""
    try:
        # Tenta interpretar o formato ISO do Supabase
        dt_utc = pd.to_datetime(utc_datetime_str)
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.tz_localize('UTC')
        dt_sp = dt_utc.tz_convert('America/Sao_Paulo')
        return dt_sp.strftime('%d/%m/%Y %H:%M:%S')
    except Exception:
        return utc_datetime_str

def salvar_feedback(sp_client, cat_id, ficha, roteiro_ia, roteiro_final, avaliacao):
    if not sp_client:
        st.error("Supabase não conectado.")
        return False
    try:
        data = {
            "categoria_id": cat_id,
            "ficha_tecnica": ficha,
            "roteiro_original_ia": roteiro_ia,
            "roteiro_final_humano": roteiro_final,
            "avaliacao": avaliacao,
            "comentarios": ""
        }
        res = sp_client.table("feedback_roteiros").insert(data).execute()
        if hasattr(res, 'data') and len(res.data) > 0:
            msg = "✅ Salvo como Aprovado!" if avaliacao == 1 else "✅ Salvo como Reprovado!" if avaliacao == -1 else "✅ Edição Salva!"
            st.success(msg)
            return True
        else:
            st.error("⚠️ Falha ao salvar no Supabase (verifique RLS).")
            return False
    except Exception as e:
        st.error(f"❌ Erro: {e}")
        return False

def salvar_ouro(sp_client, cat_id, titulo, roteiro_perfeito):
    if not sp_client:
        st.error("Supabase não conectado.")
        return False
    try:
        data = {
            "categoria_id": cat_id,
            "titulo_produto": titulo,
            "roteiro_perfeito": roteiro_perfeito
        }
        res = sp_client.table("roteiros_ouro").insert(data).execute()
        if hasattr(res, 'data') and len(res.data) > 0:
            st.success("🏆 Salvo como Roteiro Ouro (Referência Premium)!")
            return True
        else:
            st.error("⚠️ Falha ao salvar no Supabase (verifique RLS).")
            return False
    except Exception as e:
        st.error(f"❌ Erro: {e}")
        return False

def salvar_persona(sp_client, pilar, texto_ia, texto_humano, lexico, erro):
    if not sp_client:
        st.error("Supabase não conectado.")
        return False
    try:
        data = {
            "pilar_persona": pilar,
            "texto_gerado_ia": texto_ia,
            "texto_corrigido_humano": texto_humano,
            "lexico_sugerido": lexico,
            "erro_cometido": erro
        }
        res = sp_client.table("treinamento_persona_lu").insert(data).execute()
        if hasattr(res, 'data') and len(res.data) > 0:
            st.success("💃 Feedback de Persona enviado para a base!")
            return True
        else:
            st.error("⚠️ Falha ao salvar no Supabase (verifique RLS).")
            return False
    except Exception as e:
        st.error(f"❌ Erro: {e}")
        return False

def salvar_fonetica(sp_client, termo_err, termo_cor, exemplo_rot):
    if not sp_client:
        st.error("Supabase não conectado.")
        return False
    try:
        data = {
            "termo_errado": termo_err,
            "termo_corrigido": termo_cor,
            "exemplo_no_roteiro": exemplo_rot
        }
        res = sp_client.table("treinamento_fonetica").insert(data).execute()
        if hasattr(res, 'data') and len(res.data) > 0:
            st.success("🗣️ Nova regra de Fonética cadastrada!")
            return True
        else:
            st.error("⚠️ Falha ao salvar no Supabase (verifique RLS).")
            return False
    except Exception as e:
        st.error(f"❌ Erro: {e}")
        return False

def salvar_estrutura(sp_client, tipo, texto):
    if not sp_client:
        st.error("Supabase não conectado.")
        return False
    try:
        data = {
            "tipo_estrutura": tipo,
            "texto_ouro": texto
        }
        res = sp_client.table("treinamento_estruturas").insert(data).execute()
        if hasattr(res, 'data') and len(res.data) > 0:
            st.success(f"💬 {tipo} cadastrada com sucesso!")
            return True
        else:
            st.error("⚠️ Falha ao salvar no Supabase (verifique RLS).")
            return False
    except Exception as e:
        st.error(f"❌ Erro: {e}")
        return False


with st.sidebar:
    # --- Verificação de Status (antes de renderizar) ---
    api_key_env = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    supabase_client = init_supabase()
    if supabase_client:
        st.session_state['supabase_client'] = supabase_client
    
    gemini_status = "Ativo" if api_key_env else "Inativo"
    supa_status = "Ativo" if supabase_client else "Inativo"
    
    status_color_gem = "#10b981" if api_key_env else "#4b5563"
    status_color_supa = "#10b981" if supabase_client else "#4b5563"

    # --- LOGO & BRANDING ---
    LOGO_URL = "https://hvlnltccuekptytwgfrl.supabase.co/storage/v1/object/sign/media/logo_ml_ai_suite.png?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV8xMzdkZWExZi0yODU5LTQ1NTAtYWY3ZS0xZTdlY2M1NjE4ZGUiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJtZWRpYS9sb2dvX21sX2FpX3N1aXRlLnBuZyIsImlhdCI6MTc3MTgxNDM3NywiZXhwIjoxODAzMzUwMzc3fQ.TNDhROj8HLpGqwkC71zA2sv_gWRxPNUleJkM2NPvloI"
    try:
        st.image(LOGO_URL, use_container_width=True)
    except Exception:
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; width: 220px; line-height: 1.1; margin-bottom: 4px;">
            <span style="color: #0086ff; font-weight: 800; font-size: 18px; letter-spacing: 3px;">MAGALU</span>
            <span style="color: white; font-weight: 300; font-size: 36px; letter-spacing: 1px;">AI Suite</span>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown(f"""
        <div style='font-size: 11px; color: #8b92a5; margin-bottom: 25px; margin-top: 5px;'>
            V1.5 &nbsp;&nbsp;|&nbsp;&nbsp; 
            <span style='color: {status_color_gem}'>● Gemini</span> &nbsp; 
            <span style='color: {status_color_supa}'>● Supabase</span>
        </div>
    """, unsafe_allow_html=True)
    
    # --- MENU DE NAVEGAÇÃO ---
    page = st.radio(
        "Módulo do Sistema:", 
        ["Criar Roteiros", "Histórico", "Treinar IA", "Dashboard"],
        label_visibility="collapsed"
    )
    
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.divider()
    
    # --- CONFIGURAÇÕES API (SEMPRE EDITÁVEL) ---
    with st.expander("⚙️ Configurações", expanded=False):
        st.caption("Editar Chaves e Conexão")
        
        # Gemini Key
        gemini_placeholder = "••••••••" + api_key_env[-4:] if api_key_env and len(api_key_env) > 4 else ""
        api_key_input = st.text_input(
            f"🔑 Chave Gemini ({gemini_status}):", 
            type="password", 
            placeholder=gemini_placeholder if api_key_env else "Cole sua chave aqui"
        )
        if st.button("Salvar Chave Gemini", key="save_gemini"):
            if api_key_input.strip():
                with open('.env', 'a', encoding='utf-8') as f:
                    f.write(f"\nGEMINI_API_KEY={api_key_input}")
                os.environ["GEMINI_API_KEY"] = api_key_input
                st.success("Salva! F5.")
                st.stop()

        st.markdown("---")
        
        # Supabase
        supa_url_env = os.environ.get("SUPABASE_URL", "")
        supa_url_placeholder = supa_url_env[:30] + "..." if supa_url_env and len(supa_url_env) > 30 else ""
        supa_url_input = st.text_input(
            f"🔗 URL Supabase ({supa_status}):", 
            placeholder=supa_url_placeholder if supa_url_env else "https://xxx.supabase.co"
        )
        supa_key_input = st.text_input("🔑 API Key Supabase:", type="password", placeholder="Cole para atualizar")
        if st.button("Salvar Conexão Supabase"):
            if supa_url_input.strip() and supa_key_input.strip():
                with open('.env', 'a', encoding='utf-8') as f:
                    f.write(f"\nSUPABASE_URL={supa_url_input}")
                    f.write(f"\nSUPABASE_KEY={supa_key_input}")
                st.success("Salvo! F5.")
                st.stop()



# --- APLICAÇÃO PRINCIPAL ---
# (O título foi movido para a sidebar conforme solicitado)


# --- PÁGINA 1: CRIAR ROTEIROS ---
if page == "Criar Roteiros":
    
    # --- COMMAND CENTER (INPUTS) ---
    expander_input = st.expander("📝 Command Center (Entradas de Dados)", expanded=True if 'roteiros' not in st.session_state else False)
    
    with expander_input:
        # Categoria padrão
        cat_selecionada_id = 1

        # Modo de entrada: Código do Produto ou Ficha Manual
        modo_entrada = st.toggle("Modo Manual (colar ficha técnica)", value=False)

        if not modo_entrada:
            # --- MODO CÓDIGO DE PRODUTO (PADRÃO) ---
            with st.container():
                st.markdown("### 1. Escopo de Trabalho")
                
                # Seletor de Modo de Trabalho
                modos_trabalho = {
                    "NW (NewWeb)": "Descrição completa, Ficha e Foto (Padrão)",
                    "SOCIAL (Reels/TikTok)": "Em breve: Foco em ganchos virais e retenção",
                    "3D (NewWeb 3D)": "Em breve: Foco técnico em shaders e texturas 360",
                    "Review (NwReview)": "Em breve: Foco em prós e contras pro apresentador"
                }
                
                modo_selecionado = st.radio(
                    "Selecione o Formato do Roteiro:",
                    list(modos_trabalho.keys()),
                    captions=list(modos_trabalho.values()),
                    index=0,
                    horizontal=True
                )

                st.markdown("<br>", unsafe_allow_html=True)

                st.markdown("<p style='font-size: 14px; color: #8b92a5'>Digite os códigos dos produtos Magalu (um por linha ou separados por vírgula). Máximo de 15 por vez.</p>", unsafe_allow_html=True)
                
                codigos_raw = st.text_area(
                    "Códigos dos Produtos",
                    height=100,
                    placeholder="Ex:\n240304700\n240305700",
                    key="codigos_input"
                )
                st.caption("Pressione *Ctrl+Enter* para enviar ou use o botão abaixo. (Máximo: 15 códigos por lote).")
            
            st.caption("💡 O código fica na URL do produto: magazineluiza.com.br/.../p/**240304700**/...")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Regra de Bloqueio para Modos Futuros
            geracao_bloqueada = modo_selecionado != "NW (NewWeb)"

            if st.button("🚀 Iniciar Geração Magalu", use_container_width=True, type="primary", disabled=geracao_bloqueada):
                if geracao_bloqueada:
                    st.warning("🚧 Este formato de roteiro ainda está em desenvolvimento. Selecione 'NW (NewWeb)' para continuar.")
                    st.stop()
                elif len(codigos_raw.strip()) < 3:
                    st.warning("⚠️ Digite pelo menos um código de produto.")
                    st.stop()

                codigos = parse_codes(codigos_raw) if codigos_raw else []
                
                if not codigos:
                    st.warning("⚠️ Digite pelo menos um código de produto.")
                elif len(codigos) > 15:
                    st.warning("⚠️ Limite excedido: Por favor, insira no máximo 15 códigos por vez (Rate Limit da API).")
                elif not api_key_env:
                    st.warning("⚠️ Forneça uma chave da API do Gemini no painel.")
                else:
                    try:
                        agent = RoteiristaAgent(supabase_client=st.session_state.get('supabase_client'))
                        roteiros = []
                        
                        progress = st.progress(0, text="Iniciando extração...")
                        
                        for i, code in enumerate(codigos):
                            import time
                            
                            progress.progress(
                                (i) / len(codigos),
                                text=f"🔍 [{code}] Buscando página na Magalu... ({i+1}/{len(codigos)})"
                            )
                            
                            # 1. Gemini extrai dados do produto via URL
                            ficha_extraida = scrape_with_gemini(code)
                            
                            progress.progress(
                                (i + 0.5) / len(codigos),
                                text=f"✍️ [{code}] Analisando contexto e escrevendo roteiro... ({i+1}/{len(codigos)})"
                            )
                            
                            # 2. Gera o roteiro com os dados extraídos
                            roteiro = agent.gerar_roteiro(ficha_extraida, modo_trabalho=modo_selecionado)
                            roteiros.append({
                                "ficha": ficha_extraida,
                                "roteiro_original": roteiro,
                                "categoria_id": cat_selecionada_id,
                                "codigo": code
                            })
                            
                            # Auto-log no histórico (silencioso)
                            try:
                                sp_hist = st.session_state.get('supabase_client')
                                if sp_hist:
                                    ficha_text = ficha_extraida.get('text', '') if isinstance(ficha_extraida, dict) else str(ficha_extraida)
                                    sp_hist.table("historico_roteiros").insert({
                                        "codigo_produto": code,
                                        "modo_trabalho": modo_selecionado,
                                        "roteiro_gerado": roteiro,
                                        "ficha_extraida": ficha_text[:5000]
                                    }).execute()
                            except Exception:
                                pass  # Não bloqueia a geração se o log falhar
                            
                            # Delay para evitar 429 Too Many Requests
                            if i < len(codigos) - 1:
                                progress.progress((i + 0.8) / len(codigos), text=f"⏳ [{code}] Cota de segurança... Aguardando 3s.")
                                time.sleep(3)
                        
                        progress.progress(1.0, text="✅ Lote Concluído com Sucesso!")
                        st.session_state['roteiros'] = roteiros
                        st.rerun() # Força o rerun para fechar o expander
                        
                    except Exception as e:
                        st.error(f"Erro na geração: {e}")
        else:
            # --- MODO MANUAL (FALLBACK) ---
            st.markdown("<p style='font-size: 14px; color: #8b92a5'>Cole as fichas técnicas dos produtos:</p>", unsafe_allow_html=True)
            
            if 'num_fichas' not in st.session_state:
                st.session_state['num_fichas'] = 1
                
            fichas_informadas = []
            
            for i in range(st.session_state['num_fichas']):
                val = st.text_area(
                    f"Ficha Técnica do Produto {i+1}",
                    height=100,
                    key=f"ficha_input_{i}",
                    placeholder=""
                )
                fichas_informadas.append(val)
                
            col_add, col_rem = st.columns(2)
            with col_add:
                if st.button("➕ Adicionar", use_container_width=True, type="secondary"):
                    st.session_state['num_fichas'] += 1
                    st.rerun()
            with col_rem:
                if st.session_state['num_fichas'] > 1:
                    if st.button("➖ Remover", use_container_width=True, type="secondary"):
                        st.session_state['num_fichas'] -= 1
                        st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("🚀 Gerar Roteiros Mágicos", use_container_width=True, type="primary", key="btn_manual"):
                fichas = [f.strip() for f in fichas_informadas if f.strip()]
                
                if not fichas:
                    st.warning("⚠️ Cole pelo menos uma ficha técnica antes de gerar.")
                elif not api_key:
                    st.warning("⚠️ Forneça uma chave da API do Gemini no painel.")
                else:
                    with st.spinner(f"Processando {len(fichas)} roteiro(s)..."):
                        try:
                            agent = RoteiristaAgent(supabase_client=st.session_state.get('supabase_client'))
                            roteiros = []
                            for ficha in fichas:
                                roteiro = agent.gerar_roteiro(ficha)
                                roteiros.append({
                                    "ficha": ficha,
                                    "roteiro_original": roteiro,
                                    "categoria_id": cat_selecionada_id
                                })
                            st.session_state['roteiros'] = roteiros
                            st.rerun() # Força o rerun para fechar o expander
                        except Exception as e:
                            st.error(f"Erro na geração: {e}")

    # --- MESA DE TRABALHO (FULL WIDTH) ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🖥️ Mesa de Trabalho")
        
    if 'roteiros' in st.session_state and st.session_state['roteiros']:
        # Controle de Mês para Exportação
        meses_disponiveis = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
        mes_atual = meses_disponiveis[datetime.now().month - 1]
        
        # Layout do cabeçalho da mesa de trabalho
        col_btn, col_mes = st.columns([3, 1])
        with col_mes:
            mes_selecionado = st.selectbox("Mês de Ref. (Exportação)", meses_disponiveis, index=meses_disponiveis.index(mes_atual))
        
        with col_btn:
            # Botão para baixar todos os roteiros em um ZIP
            zip_bytes, zip_filename = export_all_roteiros_zip(st.session_state['roteiros'], selected_month=mes_selecionado)
            st.download_button(
                label="📦 BAIXAR TODOS (ZIP)",
                data=zip_bytes,
                file_name=zip_filename,
                mime="application/zip",
                use_container_width=True,
                type="primary",
                help="Baixa todos os roteiros da lista abaixo em um único arquivo compactado."
            )
        
        st.divider()
        
        st.divider()
        
        # Tags de Navegação (Canva Selection)
        if 'roteiro_ativo_idx' not in st.session_state:
            st.session_state['roteiro_ativo_idx'] = 0
            
        opcoes_tags = []
        for i, item in enumerate(st.session_state['roteiros']):
            codigo = item.get("codigo", "")
            ficha_raw = item.get('ficha', '')
            ficha_str = ficha_raw.get('text', str(ficha_raw)) if isinstance(ficha_raw, dict) else str(ficha_raw)
            linhas_ficha = ficha_str.split('\n')
            nome_curto = linhas_ficha[0][:20] + "..." if linhas_ficha and len(linhas_ficha[0]) > 20 else (linhas_ficha[0] if linhas_ficha else f"Item {i+1}")
            opcoes_tags.append(f"{i+1:02d} - 📦 {codigo} {nome_curto}")
            
        st.markdown("### 🗂️ Selecione o Roteiro para Edição")
        try:
            # st.pills está disponível no Streamlit 1.34+ (pode usar radio horizontal se falhar)
            selecionado = st.pills("Roteiros Gerados", opcoes_tags, default=opcoes_tags[st.session_state['roteiro_ativo_idx']])
        except AttributeError:
            selecionado = st.radio("Roteiros Gerados", opcoes_tags, index=st.session_state['roteiro_ativo_idx'], horizontal=True)
            
        if selecionado:
            idx = opcoes_tags.index(selecionado)
            st.session_state['roteiro_ativo_idx'] = idx
        else:
            idx = st.session_state['roteiro_ativo_idx']
            
        item = st.session_state['roteiros'][idx]
        ficha_raw = item.get('ficha', '')
        ficha_str = ficha_raw.get('text', str(ficha_raw)) if isinstance(ficha_raw, dict) else str(ficha_raw)
        linhas = ficha_str.split('\n')
        titulo_curto = linhas[0][:60] if linhas else f"Produto {idx+1}"
        cat_id_roteiro = item.get("categoria_id", cat_selecionada_id)
        codigo_produto = item.get("codigo", "")

        # O Canva do Roteiro Ativo
        with st.container(border=True):
            st.markdown(f"#### 🖌️ Canva: {codigo_produto} - {titulo_curto}")
            
            # Apenas uma saída editável em tela cheia (sem redundâncias)
            st.caption("✏️ **Editor Final do Roteiro (Markdown)** - Esta é a versão final que será salva e exportada.")
            edited_val = st.text_area(
                "Editor",
                value=st.session_state.get(f"editor_{idx}", item['roteiro_original']),
                height=450,
                key=f"editor_{idx}",
                label_visibility="collapsed"
            )
            sp_cli = st.session_state.get('supabase_client', None)
                
            # Barra de Controle do Roteiro Específico
            st.markdown("<br>", unsafe_allow_html=True)
            
            col_act1, col_act2 = st.columns([1, 2])
            
            with col_act1:
                docx_edited_bytes, docx_edited_fn = export_roteiro_docx(
                    edited_val,
                    code=codigo_produto,
                    product_name=titulo_curto,
                    selected_month=mes_selecionado
                )
                st.download_button(
                    label="📥 Baixar DOCX Deste Roteiro",
                    data=docx_edited_bytes,
                    file_name=docx_edited_fn,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"export_edit_{idx}",
                    use_container_width=True,
                    type="secondary"
                )
                
            with col_act2:
                # Ações Rápidas (Treinamento Pesado foi pro Hub)
                c1, c2, c3, c4 = st.columns(4)
                
                with c1:
                    if st.button("📋 Copiar Texto", key=f"copy_{idx}", use_container_width=True):
                        st.code(edited_val, language="markdown")
                        
                with c2:
                    if st.button("👍 Bom", key=f"bom_{idx}", use_container_width=True):
                        salvar_feedback(sp_cli, cat_id_roteiro, item['ficha'], item['roteiro_original'], edited_val, 1)

                with c3:
                    if st.button("👎 Ruim", key=f"ruim_{idx}", use_container_width=True):
                        salvar_feedback(sp_cli, cat_id_roteiro, item['ficha'], item['roteiro_original'], edited_val, -1)
                
                with c4:
                    if st.button("🏆 Ouro", key=f"ouro_{idx}", use_container_width=True, type="primary"):
                        salvar_ouro(sp_cli, cat_id_roteiro, titulo_curto, edited_val)

        if st.button("🗑️ Limpar Mesa de Trabalho", use_container_width=True, type="secondary"):
            del st.session_state['roteiros']
            st.rerun()
    else:
        st.markdown(
            """
            <div style='display: flex; height: 300px; align-items: center; justify-content: center; border: 2px dashed #2A3241; border-radius: 8px; color: #8b92a5; text-align: center; padding: 20px'>
            Cole os códigos no Inseridor (Command Center) acima e clique em Gerar.<br><br>
            Os roteiros aparecerão aqui prontos para calibração, treino da IA ou envio para Ouro!
            </div>
            """, 
            unsafe_allow_html=True
        )



# --- PÁGINA 2: TREINAR IA ---
elif page == "Treinar IA":
    st.subheader("🧠 Hub de Treinamento da IA")
    st.markdown("Acompanhe o aprendizado da IA, calibre configurações, insira Regras Fonéticas, Aberturas e CTAs para o Agente usar nos próximos roteiros.")
    
    if 'supabase_client' not in st.session_state:
        st.warning("Conecte o Supabase no painel lateral para visualizar e treinar a IA.")
    else:
        sp_client = st.session_state['supabase_client']
        
        # --- CARREGAMENTO GLOBAL DE DADOS PARA O HUB ---
        try:
            res_fb = sp_client.table("feedback_roteiros").select("*").execute()
            res_est = sp_client.table("treinamento_estruturas").select("*").execute()
            res_fon = sp_client.table("treinamento_fonetica").select("*").execute()
            res_ouro = sp_client.table("roteiros_ouro").select("*").execute()
            res_cats = sp_client.table("categorias").select("*").execute()
            
            df_fb = pd.DataFrame(res_fb.data if hasattr(res_fb, 'data') else [])
            df_est = pd.DataFrame(res_est.data if hasattr(res_est, 'data') else [])
            df_fon = pd.DataFrame(res_fon.data if hasattr(res_fon, 'data') else [])
            df_ouro = pd.DataFrame(res_ouro.data if hasattr(res_ouro, 'data') else [])
            df_cats = pd.DataFrame(res_cats.data if hasattr(res_cats, 'data') else [])
            
            # --- CONVERSÃO DE FUSO HORÁRIO GLOBAL (UTC -> SÃO PAULO) ---
            for df in [df_fb, df_est, df_fon, df_ouro, df_cats]:
                if not df.empty and 'criado_em' in df.columns:
                    df['criado_em'] = df['criado_em'].apply(convert_to_sp_time)
                    
        except Exception as e:
            st.error(f"Erro ao carregar dados do hub: {e}")
            df_fb = df_est = df_fon = df_ouro = df_cats = pd.DataFrame()

        tab_fb, tab_est, tab_fon, tab_ouro, tab_cat = st.tabs(["⚖️ Calibração", "💬 Estruturas", "🗣️ Fonética", "🏆 Roteiros Ouro", "📂 Categorias"])
        
        with tab_cat:
            st.markdown("### 📂 Gestão de Categorias e Tom de Voz")
            st.caption("A IA usa o 'Tom de Voz' de cada categoria para adaptar a linguagem do roteiro.")
            
            with st.form("form_nova_cat", clear_on_submit=True):
                c_nome = st.text_input("Nome da Categoria (Ex: Eletrodomésticos, Beleza)")
                c_tom = st.text_area("Tom de Voz / Diretrizes", placeholder="Ex: Linguagem alegre, empolgada, focada em praticidade do dia a dia...")
                if st.form_submit_button("➕ Cadastrar Nova Categoria", type="primary"):
                    if c_nome.strip() and c_tom.strip():
                        sp_client.table("categorias").insert({"nome": c_nome, "tom_de_voz": c_tom}).execute()
                        st.success(f"Categoria '{c_nome}' criada com sucesso!")
                        st.rerun()
                    else:
                        st.warning("Preencha nome e tom de voz.")
            
            st.divider()
            if not df_cats.empty:
                cols_to_show = ['id', 'nome', 'tom_de_voz']
                if 'criado_em' in df_cats.columns:
                    cols_to_show.append('criado_em')
                st.dataframe(df_cats[cols_to_show], use_container_width=True)
            else:
                st.info("Nenhuma categoria encontrada.")
        
        with tab_fb:
            st.markdown("### ⚖️ Calibração: IA vs Aprovado")
            st.caption("Compare o que a IA gerou com o que o Breno aprovou. Cada registro alimenta o aprendizado contínuo.")
            
            # --- FORMULÁRIO DE ENTRADA ---
            with st.form("form_calibracao", clear_on_submit=True):
                col_ia, col_breno = st.columns(2)
                with col_ia:
                    st.markdown("**🤖 ANTES (Roteiro da IA)**")
                    roteiro_ia_input = st.text_area("Cole aqui o roteiro original gerado pela IA:", height=200, key="calib_ia")
                with col_breno:
                    st.markdown("**✅ DEPOIS (Aprovado pelo Breno)**")
                    roteiro_breno_input = st.text_area("Cole aqui a versão final aprovada pelo Breno:", height=200, key="calib_breno")
                
                avaliacao_input = st.select_slider("Avaliação geral do roteiro original da IA:", options=["Ruim", "Regular", "Bom", "Ótimo"], value="Bom")
                
                submitted = st.form_submit_button("⚖️ Registrar Comparação", type="primary", use_container_width=True)
                if submitted:
                    if roteiro_ia_input.strip() and roteiro_breno_input.strip():
                        try:
                            # 1. Gera a memória com a IA
                            memoria = ""
                            try:
                                api_key_env = os.environ.get("GEMINI_API_KEY")
                                if api_key_env:
                                    ag = RoteiristaAgent(supabase_client=sp_client)
                                    with st.spinner("🧠 IA auto-avaliando o erro..."):
                                        memoria = ag.gerar_memoria_calibracao(roteiro_ia_input, roteiro_breno_input)
                            except Exception as e:
                                memoria = "Erro interno ao avaliar."

                            # 2. Mapeia a avaliação string para int para o Supabase
                            avaliacao_map = {
                                "Ruim": -1,
                                "Regular": 0,
                                "Bom": 1,
                                "Ótimo": 2
                            }
                            avaliacao_int = avaliacao_map.get(avaliacao_input, 0)
                            
                            # 3. Salva no banco
                            data = {
                                "roteiro_original_ia": roteiro_ia_input,
                                "roteiro_final_humano": roteiro_breno_input,
                                "avaliacao": avaliacao_int,
                                "comentarios": memoria
                            }
                            sp_client.table("feedback_roteiros").insert(data).execute()
                            st.success(f"✅ Comparação registrada! Memória gerada: '{memoria}'")
                            
                            # Rerun para atualizar a tabela
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                    else:
                        st.warning("Preencha ambos os campos (IA e Breno).")
            
            st.divider()
            st.markdown("#### 📋 Histórico de Calibrações")
            if not df_fb.empty:
                # Mostra a coluna comentarios como "Memória da IA"
                df_view = df_fb[['criado_em', 'avaliacao', 'comentarios']].copy()
                df_view.rename(columns={'comentarios': 'Memória da IA (Lição Aprendida)'}, inplace=True)
                st.dataframe(df_view, use_container_width=True)
            else:
                st.info("Nenhum feedback registrado ainda.")
                
        with tab_est:
            st.markdown("### 💬 Aberturas e Fechamentos (""Hooks & CTAs"")")
            st.caption("Armazena ganchos criativos e chamadas para ação Aprovadas para a IA usar como inspiração.")
            
            col_est1, col_est2 = st.columns([1, 2])
            with col_est1:
                t_tipo = st.selectbox("Tipo de Estrutura:", ["Abertura (Gancho)", "Fechamento (CTA)"])
            with col_est2:
                t_texto = st.text_area("Texto Ouro (Aprovado):")
                
            if st.button("Salvar Estrutura", type="primary"):
                if t_texto.strip():
                    salvar_estrutura(sp_client, t_tipo, t_texto)
                else:
                    st.warning("Preencha o texto da estrutura.")
                    
            st.divider()
            if not df_est.empty:
                st.dataframe(df_est[['criado_em', 'tipo_estrutura', 'texto_ouro']].sort_values(by='criado_em', ascending=False), use_container_width=True)
            else:
                st.info("Nenhuma estrutura cadastrada ainda.")
                
        with tab_fon:
            st.markdown("### 🗣️ Treinar Fonética")
            st.caption("Ensine a IA a escrever termos técnicos da forma que devem ser lidos ou ignore termos que não precisam de fonética.")
            
            t_err = st.text_input("Como a IA escreveu:", placeholder="Ex: cinco gê", key="hub_te")
            t_cor = st.text_input("Como deveria ser pelo humano:", placeholder="Ex: 5G", key="hub_tc")
            
            st.markdown("<p style='font-size: 0.85rem; color: #8b92a5; margin-top: -10px;'><b>Obs.:</b> 5G é um termo comum que não precisa de fonética, assim como USB ou HDMI</p>", unsafe_allow_html=True)
            
            if st.button("📥 Registrar Regra de Pronúncia", key="hub_btn_fon", use_container_width=True, type="primary"):
                if t_err.strip() and t_cor.strip():
                    salvar_fonetica(sp_client, t_err, t_cor, "Regra de fonética/exceção")
                else:
                    st.warning("Preencha ambos os campos.")
            
            st.divider()
            if not df_fon.empty:
                st.dataframe(df_fon[['termo_errado', 'termo_corrigido', 'criado_em']], use_container_width=True)
            else:
                st.info("Nenhuma regra fonética cadastrada.")
        
        with tab_ouro:
            st.markdown("### 🏆 Hall da Fama (Roteiros Ouro)")
            st.caption("Roteiros finalizados e aprovados. Alimentam o Few-Shot da IA e podem ser exportados como JSON-LD.")
            
            with st.form("form_roteiro_ouro", clear_on_submit=True):
                col_sku, col_prod = st.columns([1, 2])
                with col_sku:
                    t_sku = st.text_input("Código do Produto (SKU):", placeholder="Ex: 240304700")
                with col_prod:
                    t_prod = st.text_input("Título do Produto:")
                t_rot = st.text_area("Roteiro Finalizado (Aprovado):")
                if st.form_submit_button("🏆 Cadastrar Roteiro Ouro", type="primary"):
                    if t_prod.strip() and t_rot.strip():
                        data_ouro = {
                            "categoria_id": 1,
                            "titulo_produto": t_prod,
                            "roteiro_perfeito": t_rot,
                        }
                        if t_sku.strip():
                            data_ouro["codigo_produto"] = t_sku.strip()
                        sp_client.table("roteiros_ouro").insert(data_ouro).execute()
                        st.success(f"Roteiro Ouro '{t_prod}' cadastrado!")
                        st.rerun()
                    else:
                        st.warning("Preencha pelo menos o título e o roteiro.")
            
            st.divider()
            if not df_ouro.empty:
                # Tabela de visualização
                cols_ouro = ['titulo_produto', 'roteiro_perfeito']
                if 'codigo_produto' in df_ouro.columns:
                    cols_ouro.insert(0, 'codigo_produto')
                st.dataframe(df_ouro[cols_ouro], use_container_width=True)
                
                # --- EXPORTAÇÃO JSON-LD ---
                st.divider()
                st.markdown("#### 🌐 Exportar JSON-LD (Schema.org)")
                st.caption("Gere dados estruturados prontos para SEO e integração com sistemas externos.")
                
                # Busca nomes das categorias para o mapeamento
                cats_dict_ouro = {}
                try:
                    res_cats_ouro = sp_client.table("categorias").select("id, nome").execute()
                    if hasattr(res_cats_ouro, 'data') and res_cats_ouro.data:
                        cats_dict_ouro = {c['id']: c['nome'] for c in res_cats_ouro.data}
                except Exception:
                    pass
                
                # Seletor de qual roteiro exportar
                opcoes_ouro = [f"{r.get('codigo_produto', '???')} - {r.get('titulo_produto', 'Sem Título')[:40]}" for _, r in df_ouro.iterrows()]
                sel_ouro = st.selectbox("Selecione o Roteiro Ouro:", opcoes_ouro)
                
                if sel_ouro:
                    idx_ouro = opcoes_ouro.index(sel_ouro)
                    roteiro_sel = df_ouro.iloc[idx_ouro].to_dict()
                    cat_name = cats_dict_ouro.get(roteiro_sel.get('categoria_id'), 'Genérico')
                    
                    col_prod_ld, col_cw_ld = st.columns(2)
                    with col_prod_ld:
                        jsonld_product = export_jsonld_string(roteiro_sel, cat_name, "Product")
                        st.download_button(
                            "📦 Baixar JSON-LD (Product)",
                            data=jsonld_product,
                            file_name=f"jsonld_product_{roteiro_sel.get('codigo_produto', 'roteiro')}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                    with col_cw_ld:
                        jsonld_cw = export_jsonld_string(roteiro_sel, cat_name, "CreativeWork")
                        st.download_button(
                            "🎨 Baixar JSON-LD (CreativeWork)",
                            data=jsonld_cw,
                            file_name=f"jsonld_creative_{roteiro_sel.get('codigo_produto', 'roteiro')}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                    
                    with st.expander("👁️ Pré-visualizar JSON-LD (Product)"):
                        st.code(jsonld_product, language="json")
            else:
                st.info("Nenhum roteiro ouro cadastrado ainda.")

# --- PÁGINA 1.5: HISTÓRICO ---
elif page == "Histórico":
    st.subheader("🕒 Histórico de Roteiros")
    st.markdown("Confira todos os roteiros gerados automaticamente pelo sistema. Tudo o que você cria fica salvo aqui para consulta rápida.")
    
    if 'supabase_client' not in st.session_state:
        st.warning("Conecte o Supabase no painel lateral para visualizar o histórico.")
    else:
        sp_client = st.session_state['supabase_client']
        try:
            with st.spinner("Carregando histórico..."):
                res_hist = sp_client.table("historico_roteiros").select("*").order('criado_em', desc=True).execute()
                
            if res_hist.data:
                df_hist = pd.DataFrame(res_hist.data)
                
                if not df_hist.empty and 'criado_em' in df_hist.columns:
                    df_hist['criado_em'] = df_hist['criado_em'].apply(convert_to_sp_time)
                
                total_registros = len(df_hist)
                
                # --- BARRA DE FILTROS ---
                col_search, col_modo = st.columns([3, 1])
                with col_search:
                    search = st.text_input("🔍 Filtrar por código ou palavra-chave:", placeholder="Ex: 240304700, Geladeira", label_visibility="collapsed")
                with col_modo:
                    modos_unicos = ["Todos"] + sorted(df_hist['modo_trabalho'].dropna().unique().tolist()) if 'modo_trabalho' in df_hist.columns else ["Todos"]
                    modo_filtro = st.selectbox("Modo", modos_unicos, label_visibility="collapsed")
                
                # Filtro por texto (múltiplos termos com OR)
                if search:
                    import re
                    termos = [t.strip() for t in re.split(r'[,\s]+', search) if t.strip()]
                    if termos:
                        mask = pd.Series(False, index=df_hist.index)
                        for termo in termos:
                            mask = mask | (
                                df_hist['codigo_produto'].str.contains(termo, case=False, na=False) |
                                df_hist['roteiro_gerado'].str.contains(termo, case=False, na=False)
                            )
                        df_hist = df_hist[mask]
                
                # Filtro por Modo de Trabalho
                if modo_filtro != "Todos" and 'modo_trabalho' in df_hist.columns:
                    df_hist = df_hist[df_hist['modo_trabalho'] == modo_filtro]
                
                # Métricas de resultado
                filtrados = len(df_hist)
                col_m1, col_m2 = st.columns(2)
                col_m1.metric("Total de Roteiros", total_registros)
                col_m2.metric("Exibindo", filtrados, delta=f"{filtrados - total_registros}" if filtrados < total_registros else None)
                
                # Define o index da tabela para começar do 01, 02...
                df_hist.reset_index(drop=True, inplace=True)
                df_hist.index = [f"{i+1:02d}" for i in range(len(df_hist))]

                st.dataframe(
                    df_hist[['criado_em', 'codigo_produto', 'modo_trabalho', 'roteiro_gerado']], 
                    use_container_width=True,
                    height=600
                )
            else:
                st.info("Nenhum roteiro gerado ainda. Vá em 'Criar Roteiros' para começar!")
        except Exception as e:
            st.error(f"Erro ao carregar histórico: {e}")

# --- PÁGINA 3: DASHBOARD ---
elif page == "Dashboard":
    st.subheader("📊 Métricas de Desempenho da IA")
    
    if 'supabase_client' not in st.session_state:
        st.warning("Conecte o Supabase no painel lateral para visualizar os dados.")
    else:
        sp_client = st.session_state['supabase_client']
        
        # Carrega dados do banco
        try:
            res_fb = sp_client.table("feedback_roteiros").select("*").execute()
            res_ouro = sp_client.table("roteiros_ouro").select("*").execute()
            res_pers = sp_client.table("treinamento_persona_lu").select("*").execute()
            res_fon = sp_client.table("treinamento_fonetica").select("*").execute()
            res_cats = sp_client.table("categorias").select("*").execute()
            res_est = sp_client.table("treinamento_estruturas").select("*").execute()
            
            fb_data = res_fb.data if hasattr(res_fb, 'data') else []
            ouro_data = res_ouro.data if hasattr(res_ouro, 'data') else []
            pers_data = res_pers.data if hasattr(res_pers, 'data') else []
            fon_data = res_fon.data if hasattr(res_fon, 'data') else []
            est_data = res_est.data if hasattr(res_est, 'data') else []
            cats_dict = {c['id']: c['nome'] for c in res_cats.data} if hasattr(res_cats, 'data') else {}
            
            df_fb = pd.DataFrame(fb_data)
            df_ouro = pd.DataFrame(ouro_data)
            df_pers = pd.DataFrame(pers_data)
            df_fon = pd.DataFrame(fon_data)
            df_est = pd.DataFrame(est_data)
            
            # --- CONVERSÃO DE FUSO HORÁRIO GLOBAL (UTC -> SÃO PAULO) ---
            for df in [df_fb, df_ouro, df_pers, df_fon, df_est]:
                if not df.empty and 'criado_em' in df.columns:
                    df['criado_em'] = df['criado_em'].apply(convert_to_sp_time)
            
            if not df_fb.empty: df_fb['categoria'] = df_fb['categoria_id'].map(cats_dict)
            if not df_ouro.empty: df_ouro['categoria'] = df_ouro['categoria_id'].map(cats_dict)
            
            total_avaliados = len(df_fb)
            positivos = len(df_fb[df_fb['avaliacao'] == 1]) if not df_fb.empty and 'avaliacao' in df_fb.columns else 0
            negativos = len(df_fb[df_fb['avaliacao'] == -1]) if not df_fb.empty and 'avaliacao' in df_fb.columns else 0
            total_ouro = len(df_ouro)
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Roteiros Avaliados (Logs)", total_avaliados)
            col2.metric("👍 Avaliações Positivas", positivos)
            col3.metric("👎 Avaliações Negativas", negativos)
            col4.metric("🏆 Roteiros Ouro (Few-Shot)", total_ouro)
            
            st.divider()
            
            tab_ouro, tab_feed, tab_pers, tab_fon = st.tabs(["🏆 Roteiros Ouro", "⚖️ Feedbacks", "💃 Persona", "🗣️ Fonética"])
            
            with tab_ouro:
                st.markdown("### 🏆 Referências Premium")
                if not df_ouro.empty:
                    st.dataframe(df_ouro[['criado_em', 'categoria', 'titulo_produto', 'roteiro_perfeito']].sort_values(by='criado_em', ascending=False), use_container_width=True)
                else:
                    st.info("Nenhum Roteiro Ouro cadastrado.")
            
            with tab_feed:
                st.markdown("### ⚖️ Logs de Feedback")
                if not df_fb.empty:
                    st.dataframe(df_fb[['criado_em', 'avaliacao', 'categoria', 'roteiro_original_ia', 'roteiro_final_humano', 'comentarios']].sort_values(by='criado_em', ascending=False), use_container_width=True)
                else:
                    st.info("Nenhum feedback registrado.")
            
            with tab_pers:
                st.markdown("### 💃 Treinamento de Persona")
                if not df_pers.empty:
                    st.dataframe(df_pers[['criado_em', 'pilar_persona', 'erro_cometido', 'texto_corrigido_humano', 'lexico_sugerido']].sort_values(by='criado_em', ascending=False), use_container_width=True)
                else:
                    st.info("Nenhum ajuste de persona cadastrado.")
                    
            with tab_fon:
                st.markdown("### 🗣️ Regras de Fonética")
                if not df_fon.empty:
                    st.dataframe(df_fon[['criado_em', 'termo_errado', 'termo_corrigido', 'exemplo_no_roteiro']].sort_values(by='criado_em', ascending=False), use_container_width=True)
                else:
                    st.info("Nenhuma regra de fonética cadastrada.")
                
        except Exception as e:
            st.error(f"Erro ao carregar os dados do dashboard: {e}")
