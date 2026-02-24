import streamlit as st
import os
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pytz
from dotenv import load_dotenv
from supabase import create_client, Client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.agent import RoteiristaAgent, MODELOS_DISPONIVEIS, MODELOS_DESCRICAO, PROVIDER_KEY_MAP
from src.scraper import scrape_with_gemini, parse_codes
from src.exporter import export_roteiro_docx, format_for_display, export_all_roteiros_zip
from src.jsonld_generator import export_jsonld_string, wrap_in_script_tag

load_dotenv()

# --- DEFINIÇÃO DE FUSO HORÁRIO ---
BR_TIMEZONE = pytz.timezone('America/Sao_Paulo')

def get_now_sp():
    """Retorna o datetime atual em São Paulo."""
    return datetime.now(BR_TIMEZONE)

# --- HELPERS PARA NUMERAÇÃO ---
def get_total_script_count(sp_client):
    """Retorna o total de registros na tabela historico_roteiros para numeração sequencial."""
    if not sp_client:
        return 0
    try:
        # Busca o total de registros no banco
        res = sp_client.table("nw_historico_roteiros").select("id", count="exact").limit(1).execute()
        return res.count if hasattr(res, 'count') and res.count is not None else 0
    except Exception:
        return 0

# --- CONFIGURAÇÃO GERAL ---
st.set_page_config(page_title="Magalu AI Suite", page_icon="🛍️", layout="wide", initial_sidebar_state="expanded")

CUSTO_LEGADO_BRL = 5.16  # Valor acumulado antes do tracking automático

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

    h1 { font-size: 2.4rem !important; font-weight: 800 !important; color: #ffffff !important; letter-spacing: -0.5px; margin-bottom: 0.8rem !important; }
    h2 { font-size: 1.8rem !important; font-weight: 700 !important; color: #e0e6f0 !important; margin-bottom: 0.6rem !important; }
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
    
    /* Botões Primários (Global) - Gradiente Moderno */
    button[kind="primary"], .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button, .stFormSubmitButton > button {
        background: linear-gradient(135deg, #0086ff 0%, #004db3 100%) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 2px 8px rgba(0, 134, 255, 0.3) !important;
    }
    button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] > button:hover, .stFormSubmitButton > button:hover {
        background: linear-gradient(135deg, #339dff 0%, #0066cc 100%) !important;
        transform: scale(1.02) !important;
        box-shadow: 0 4px 12px rgba(0, 134, 255, 0.45) !important;
    }
    
    /* Botões Secundários - Gradiente Sutil */
    button[kind="secondary"] {
        background: linear-gradient(135deg, #0a1b33 0%, #001f4d 100%) !important;
        color: var(--text-primary) !important;
        border: 1px solid #003380 !important;
    }
    button[kind="secondary"]:hover {
        background: linear-gradient(135deg, #001f4d 0%, #003380 100%) !important;
        border-color: var(--mglu-blue) !important;
        box-shadow: 0 2px 8px rgba(0, 134, 255, 0.2) !important;
    }
    
    /* Download buttons - Gradiente Verde */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #10b981 0%, #047857 100%) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3) !important;
    }
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #34d399 0%, #10b981 100%) !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.45) !important;
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
    
    /* Sidebar navigation radio buttons - fonte maior */
    [data-testid="stSidebar"] [role="radiogroup"] label {
        font-size: 1.05rem !important;
        font-weight: 500 !important;
        padding: 6px 0 !important;
    }
    
    .block-container { padding-top: 2rem; }

    /* Cards de Métricas Premium */
    .metric-card-premium {
        background: linear-gradient(135deg, rgba(5, 14, 29, 0.7) 0%, rgba(10, 27, 51, 0.4) 100%);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 134, 255, 0.15);
        border-radius: 12px;
        padding: 1.25rem 1rem;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        height: 110px;
        margin-bottom: 20px;
    }
    .metric-card-premium:hover {
        transform: translateY(-3px);
        border-color: rgba(0, 134, 255, 0.4);
        box-shadow: 0 8px 25px rgba(0, 134, 255, 0.15);
    }
    .metric-label {
        font-size: 0.75rem !important;
        color: var(--text-muted) !important;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.5rem;
    }
    .metric-value {
        font-size: 1.25rem !important;
        color: #ffffff !important;
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    /* Estilização de Placeholders para cores nítidas */
    ::placeholder { color: #5c677d !important; opacity: 1; }
    :-ms-input-placeholder { color: #5c677d !important; }
    ::-ms-input-placeholder { color: #5c677d !important; }
    
    textarea::placeholder, input::placeholder {
        color: #5c677d !important;
        font-style: italic;
    }

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
        return dt_sp.strftime('%d/%m/%Y %H:%M')
    except Exception:
        return utc_datetime_str

def salvar_calibracao_ouro(sp_client, cat_id, roteiro_ia, roteiro_final, percentual, aprendizado, codigo_produto="", titulo_produto="", modelo_calibragem="N/A"):
    if not sp_client:
        st.error("Supabase não conectado.")
        return False
    try:
        data = {
            "categoria_id": cat_id,
            "codigo_produto": codigo_produto,
            "titulo_produto": titulo_produto if titulo_produto else codigo_produto,
            "roteiro_original_ia": roteiro_ia,
            "roteiro_perfeito": roteiro_final,
            "nota_percentual": percentual,
            "aprendizado": aprendizado,
            "modelo_calibragem": modelo_calibragem,
            "criado_em": get_now_sp().isoformat()
        }
        res = sp_client.table("nw_roteiros_ouro").insert(data).execute()
        if hasattr(res, 'data') and len(res.data) > 0:
            msg = f"🏆 Calibragem salva como Roteiro Ouro! (Aproveitamento: {percentual}% | Cat ID: {cat_id} | IA: {modelo_calibragem})"
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
        res = sp_client.table("nw_roteiros_ouro").insert(data).execute()
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
        res = sp_client.table("nw_treinamento_persona_lu").insert(data).execute()
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
        res = sp_client.table("nw_treinamento_fonetica").insert(data).execute()
        if hasattr(res, 'data') and len(res.data) > 0:
            st.success("🗣️ Nova regra de Fonética cadastrada!")
            return True
        else:
            st.error("⚠️ Falha ao salvar no Supabase (verifique RLS).")
            return False
    except Exception as e:
        st.error(f"❌ Erro: {e}")
        return False

def _auto_salvar_fonetica(sp_client, fonetica_regras):
    """Salva regras fonéticas automaticamente a partir da calibragem, evitando duplicatas."""
    if not sp_client or not fonetica_regras:
        return 0
    
    count = 0
    for regra in fonetica_regras:
        if not isinstance(regra, dict):
            continue
        termo_err = str(regra.get('termo_errado', '')).strip()
        termo_cor = str(regra.get('termo_corrigido', '')).strip()
        exemplo = str(regra.get('exemplo', '')).strip()
        if not termo_err or not termo_cor:
            continue
        
        try:
            existing = sp_client.table("nw_treinamento_fonetica").select("id").eq("termo_errado", termo_err).execute()
            if hasattr(existing, 'data') and len(existing.data) > 0:
                continue
            
            sp_client.table("nw_treinamento_fonetica").insert({
                "termo_errado": termo_err,
                "termo_corrigido": termo_cor,
                "exemplo_no_roteiro": exemplo
            }).execute()
            count += 1
        except Exception as e:
            print(f"⚠️ Erro ao salvar fonética auto: {e}")
    
    if count > 0:
        st.toast(f"📖 {count} regra(s) fonética(s) aprendida(s) automaticamente!", icon="🎓")
    return count

def _auto_salvar_estrutura(sp_client, estrutura_regras):
    """Salva regras de abertura/fechamento automaticamente a partir da calibragem."""
    if not sp_client or not estrutura_regras:
        return 0
    
    count = 0
    for regra in estrutura_regras:
        if not isinstance(regra, dict):
            continue
        tipo = str(regra.get('tipo', '')).strip()
        texto_ouro = str(regra.get('texto_ouro', '')).strip()
        if not tipo or not texto_ouro or tipo not in ('Abertura', 'Fechamento'):
            continue
        
        try:
            sp_client.table("nw_treinamento_estruturas").insert({
                "tipo_estrutura": tipo,
                "texto_ouro": texto_ouro
            }).execute()
            count += 1
        except Exception as e:
            print(f"⚠️ Erro ao salvar estrutura auto: {e}")
    
    if count > 0:
        st.toast(f"📝 {count} estrutura(s) (abertura/fechamento) aprendida(s)!", icon="✨")
    return count

def _auto_salvar_persona(sp_client, persona_regras):
    """Salva regras de persona da Lu automaticamente a partir da calibragem."""
    if not sp_client or not persona_regras:
        return 0
    
    count = 0
    for regra in persona_regras:
        if not isinstance(regra, dict):
            continue
        pilar = str(regra.get('pilar', '')).strip()
        erro = str(regra.get('erro', '')).strip()
        correcao = str(regra.get('correcao', '')).strip()
        lexico = str(regra.get('lexico', '')).strip()
        if not pilar or not erro:
            continue
        
        try:
            sp_client.table("nw_treinamento_persona_lu").insert({
                "pilar_persona": pilar,
                "texto_gerado_ia": erro,
                "texto_corrigido_humano": correcao,
                "lexico_sugerido": lexico,
                "erro_cometido": erro
            }).execute()
            count += 1
        except Exception as e:
            print(f"⚠️ Erro ao salvar persona auto: {e}")
    
    if count > 0:
        st.toast(f"💃 {count} regra(s) de persona da Lu aprendida(s)!", icon="🎭")
    return count

def salvar_estrutura(sp_client, tipo, texto):
    if not sp_client:
        st.error("Supabase não conectado.")
        return False
    try:
        data = {
            "tipo_estrutura": tipo,
            "texto_ouro": texto
        }
        res = sp_client.table("nw_treinamento_estruturas").insert(data).execute()
        if hasattr(res, 'data') and len(res.data) > 0:
            st.success(f"💬 {tipo} cadastrada com sucesso!")
            return True
        else:
            st.error("⚠️ Falha ao salvar no Supabase (verifique RLS).")
            return False
    except Exception as e:
        st.error(f"❌ Erro: {e}")
        return False

def salvar_nuance(sp_client, frase, analise, exemplo):
    if not sp_client:
        st.error("Supabase não conectado.")
        return False
    try:
        data = {
            "frase_ia": frase,
            "analise_critica": analise,
            "exemplo_ouro": exemplo
        }
        res = sp_client.table("nw_treinamento_nuances").insert(data).execute()
        if hasattr(res, 'data') and len(res.data) > 0:
            st.success("🧠 Nuance de linguagem registrada para o treinamento!")
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
    puter_key_env = os.environ.get("PUTER_API_KEY") or st.secrets.get("PUTER_API_KEY")
    openai_key_env = os.environ.get("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
    openrouter_key_env = os.environ.get("OPENROUTER_API_KEY") or st.secrets.get("OPENROUTER_API_KEY")
    zai_key_env = os.environ.get("ZAI_API_KEY") or st.secrets.get("ZAI_API_KEY")
    kimi_key_env = os.environ.get("KIMI_API_KEY") or st.secrets.get("KIMI_API_KEY")
    supabase_client = init_supabase()
    if supabase_client:
        st.session_state['supabase_client'] = supabase_client
    
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
    
    # --- STATUS INDICATORS (apenas LLM ativa + Supabase) ---
    _modelo_atual = st.session_state.get('modelo_llm', 'gemini-2.5-flash')
    _prov = _modelo_atual.split('/')[0] if '/' in _modelo_atual else 'gemini'
    _env_map = {
        "gemini": api_key_env, 
        "openai": openai_key_env, 
        "puter": puter_key_env, 
        "openrouter": openrouter_key_env, 
        "zai": zai_key_env,
        "kimi": kimi_key_env
    }
    _llm_active = bool(_env_map.get(_prov))
    
    _nomes_modelos = {v: k for k, v in MODELOS_DISPONIVEIS.items()}
    _full_name = _nomes_modelos.get(_modelo_atual, "LLM Desconhecida")
    
    # Ex: "⚡ Gemini 2.5 Flash — Grátis" -> "Gemini 2.5 Flash"
    _llm_name = _full_name.split(' — ')[0]
    
    # Remove emoji/símbolo inicial se houver espaco logo apos
    if _llm_name and " " in _llm_name and ord(_llm_name[0]) > 127:
        _llm_name = _llm_name.split(" ", 1)[-1].strip()
        
    if len(_llm_name) > 15:
        _llm_name = _llm_name[:13] + ".."

    
    sc_llm = "#00ff88" if _llm_active else "#ff4b4b"
    sl_llm = "ON" if _llm_active else "OFF"
    sb_llm = "rgba(0, 255, 136, 0.12)" if _llm_active else "rgba(255, 75, 75, 0.12)"
    
    sc_sup = "#00ff88" if supabase_client else "#ff4b4b"
    sl_sup = "ON" if supabase_client else "OFF"
    sb_sup = "rgba(0, 255, 136, 0.12)" if supabase_client else "rgba(255, 75, 75, 0.12)"

    st.markdown(f"""
        <div style='font-size: 8px; color: #8b92a5; margin-bottom: 25px; margin-top: 5px; display: flex; align-items: center; gap: 8px;'>
            <span style='font-weight: 400; letter-spacing: 0.5px;'>V2.8</span>
            <span style='color: #2A3241;'>|</span>
            <div style='display: flex; align-items: center; gap: 4px;'>
                <span style='color: {sc_llm}; font-weight: 400; font-size: 8px;'>{_llm_name}</span>
                <span style='background: {sb_llm}; color: {sc_llm}; padding: 0.2px 3px; border-radius: 2px; font-size: 6px; font-weight: 600; border: 1px solid {sc_llm}22;'>{sl_llm}</span>
            </div>
            <div style='display: flex; align-items: center; gap: 4px;'>
                <span style='color: {sc_sup}; font-weight: 400; font-size: 8px;'>Supabase</span>
                <span style='background: {sb_sup}; color: {sc_sup}; padding: 0.2px 3px; border-radius: 2px; font-size: 6px; font-weight: 600; border: 1px solid {sc_sup}22;'>{sl_sup}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # --- SELETOR DE MODELO LLM ---
    # Usamos uma chave para detectar mudança
    modelo_label = st.selectbox(
        "🧠 Modelo de IA:",
        list(MODELOS_DISPONIVEIS.keys()),
        index=0,
        key="model_selector"
    )
    modelo_id_selecionado = MODELOS_DISPONIVEIS[modelo_label]
    
    # Se mudou o modelo, mostramos o loading e validamos
    if st.session_state.get('last_model') != modelo_id_selecionado:
        with st.spinner(f"⚡ Sincronizando nova Inteligência: {modelo_label.split(' — ')[0]}..."):
            import time
            time.sleep(1.5) # Delay deliberado para percepção visual do usuário
            try:
                # Teste rápido de inicialização
                _temp_agent = RoteiristaAgent(model_id=modelo_id_selecionado)
                st.session_state['modelo_llm'] = modelo_id_selecionado
                st.session_state['last_model'] = modelo_id_selecionado
                st.toast(f"Módulo {modelo_label.split(' — ')[0]} carregado e pronto!", icon="🧠")
                time.sleep(1.0) # Espera o toast ser lido antes do rebuild
            except Exception as e:
                st.error(f"Erro ao ativar modelo: {e}")
                st.session_state['modelo_llm'] = "gemini-2.5-flash" # Fallback
        st.rerun()

    # Info rápida sobre o modelo
    _desc = MODELOS_DESCRICAO.get(modelo_id_selecionado, "")
    if _desc:
        st.markdown(f"""
            <div style='background: rgba(0, 134, 255, 0.05); padding: 5px 8px; border-radius: 4px; border-left: 3px solid #0086ff; margin-bottom: 20px;'>
                <p style='font-size: 9px; color: #8b92a5; margin: 0; line-height: 1.3;'>{_desc}</p>
            </div>
        """, unsafe_allow_html=True)
    
    # CSS Sidebar Navigation (Alinhamento de botão à esquerda)
    st.markdown("""
    <style>
        [data-testid="stSidebar"] div.stButton > button {
            justify-content: flex-start !important;
            padding-left: 15px !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- MENU DE NAVEGAÇÃO ---
    if 'page' not in st.session_state:
        st.session_state['page'] = "Criar Roteiros"

    nav_items = {
        "Criar Roteiros": "✍️ Criar Roteiros",
        "Treinar IA": "🧠 Treinar IA",
        "Histórico": "🕒 Histórico",
        "Dashboard": "📊 Dashboard"
    }
    
    for page_key, page_label in nav_items.items():
        is_active = st.session_state['page'] == page_key
        if st.button(page_label, use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state['page'] = page_key
            st.rerun()
    
    st.divider()
    
    # --- RODAPÉ: GUIA, CHAT E CONFIGURAÇÕES ---
    is_guia_active = st.session_state['page'] == "Guia de Modelos"
    if st.button("📖 Guia de Modelos", use_container_width=True, type="primary" if is_guia_active else "secondary"):
        st.session_state['page'] = "Guia de Modelos"
        st.rerun()

    is_lu_active = st.session_state['page'] == "Assistente Lu"
    if st.button("💬 Assistente Lu (Chat)", use_container_width=True, type="primary" if is_lu_active else "secondary"):
        st.session_state['page'] = "Assistente Lu"
        st.rerun()

    is_config_active = st.session_state['page'] == "Configurações"
    if st.button("⚙️ Configurações", use_container_width=True, type="primary" if is_config_active else "secondary"):
        st.session_state['page'] = "Configurações"
        st.rerun()

    page = st.session_state['page']

@st.fragment
def show_calibragem_summary():
    """Exibe um resumo persistente das regras aprendidas após calibragem."""
    if 'show_calib_modal' in st.session_state:
        m = st.session_state['show_calib_modal']
        calc = m['calc']
        
        st.markdown(f"### 🧪 Resumo do Aprendizado da IA")
        st.success(f"🏆 Roteiro Ouro Salvo! {m['score_color']} Qualidade: {m['estrelas']:.1f} ⭐")
        
        with st.container(border=True):
            if m['n_f'] > 0:
                st.markdown(f"**🎓 Fonética ({m['n_f']}):**")
                for r in calc['fonetica_regras']:
                    st.code(f"{r['termo_errado']} → {r['termo_corrigido']}", language="text")
            
            if m['n_e'] > 0:
                st.markdown(f"**✨ Estrutura ({m['n_e']}):**")
                for r in calc['estrutura_regras']:
                    st.caption(f"Tipo: {r['tipo']}")
                    st.text_area("Texto Ouro:", value=r['texto_ouro'], height=70, disabled=True, key=f"mdl_est_{r['tipo']}")
            
            if m['n_p'] > 0:
                st.markdown(f"**🎭 Persona Lu ({m['n_p']}):**")
                for r in calc['persona_regras']:
                    st.caption(f"Pilar: {r['pilar']}")
                    st.markdown(f"*Correção:* {r['correcao']}")
        
        st.info("Estas regras foram integradas ao 'cérebro' da IA e serão aplicadas nos próximos roteiros.")
        if st.button("✅ Entendido, Fechar Relatório", use_container_width=True, type="primary"):
            del st.session_state['show_calib_modal']
            st.rerun()

# --- APLICAÇÃO PRINCIPAL ---
if 'show_calib_modal' in st.session_state:
    show_calibragem_summary()


# --- PÁGINA 1: CRIAR ROTEIROS ---
if page == "Criar Roteiros":
    
    # --- COMMAND CENTER (INPUTS) ---
    # Colapsa automaticamente após geração, mas o usuário sempre pode reabrir
    _has_roteiros = 'roteiros' in st.session_state and st.session_state['roteiros']
    expander_input = st.expander("✍️ Inserir Códigos e Gerar", expanded=not _has_roteiros)
    
    with expander_input:
        # Categoria padrão
        cat_selecionada_id = 1

        # Modo de entrada via Tabs
        tab_auto, tab_manual = st.tabs(["⚡ Automático (SKUs da Magalu)", "✍️ Manual (Colar Fichas)"])

        with tab_auto:
            # --- MODO AUTOMÁTICO (MAGALU) ---
            st.markdown("### 1. Formato do Roteiro")
            
            # Formatos de trabalho
            modos_trabalho = {
                "📄 NW (NewWeb)": "NW (NewWeb)",
                "📱 SOCIAL (Reels)": "SOCIAL (Reels/TikTok)",
                "🎮 3D (NewWeb 3D)": "3D (NewWeb 3D)",
                "🎙️ Review": "Review (NwReview)"
            }
            modos_descricao = {
                "📄 NW (NewWeb)": "Descrição completa, Ficha e Foto (Padrão)",
                "📱 SOCIAL (Reels)": "Em breve: Ganchos virais e retenção",
                "🎮 3D (NewWeb 3D)": "Em breve: Shaders e texturas 360",
                "🎙️ Review": "Em breve: Prós e contras pro apresentador"
            }
            
            try:
                modo_pill = st.pills(
                    "Selecione o Formato do Roteiro:",
                    list(modos_trabalho.keys()),
                    default="📄 NW (NewWeb)"
                )
            except AttributeError:
                modo_pill = st.radio(
                    "Selecione o Formato:",
                    list(modos_trabalho.keys()),
                    index=0,
                    horizontal=True
                )
            
            if modo_pill:
                modo_selecionado = modos_trabalho[modo_pill]
                st.caption(f"ℹ️ {modos_descricao[modo_pill]}")
            else:
                modo_selecionado = "NW (NewWeb)"
                st.caption("ℹ️ Descrição completa, Ficha e Foto (Padrão)")

            st.markdown("---")
            col_m_auto, col_d_auto = st.columns(2)
            
            with col_m_auto:
                st.markdown("**Mês de Lançamento**")
                mes_selecionado = st.selectbox(
                    "Mês",
                    ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"],
                    index=2, # Padrão MAR conforme solicitado
                    key="mes_auto",
                    label_visibility="collapsed"
                )
            
            with col_d_auto:
                st.markdown("**Data do Roteiro**")
                now_sp = get_now_sp()
                data_roteiro = st.date_input("Data", value=now_sp, format="DD/MM/YYYY", key="data_auto", label_visibility="collapsed")
                data_roteiro_str = data_roteiro.strftime('%d/%m/%y')

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 2. Códigos dos Produtos")

            st.markdown("<p style='font-size: 14px; color: #8b92a5'>Digite os códigos Magalu, um por linha. Mínimo 3 dígitos. Máximo 15 por vez.</p>", unsafe_allow_html=True)
            
            codigos_raw = st.text_area(
                "Códigos dos Produtos",
                height=150,
                placeholder="240304700\n240305700\n240306800",
                key="codigos_input_auto",
                label_visibility="collapsed"
            )
            st.caption("💡 O código fica na URL: magazineluiza.com.br/.../p/**240304700**/...")

            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- NOVO FLUXO: PRÉ-GERAÇÃO (TABELA EDITÁVEL) ---
            if st.button("🔍 Validar Códigos", use_container_width=True):
                codigos = parse_codes(codigos_raw) if codigos_raw else []
                if not codigos:
                    st.warning("⚠️ Digite pelo menos um código de produto.")
                elif len(codigos) > 15:
                    st.warning("⚠️ Limite excedido: Por favor, insira no máximo 15 códigos por vez (Rate Limit da API).")
                else:
                    df_pre = pd.DataFrame({
                        "SKU Principal": codigos,
                        "Outros Códigos (Cor/Voltagem)": [""] * len(codigos),
                        "Vídeo do Fornecedor (Link)": [""] * len(codigos)
                    })
                    st.session_state['skus_validados'] = df_pre
            
            geracao_bloqueada = modo_selecionado != "NW (NewWeb)"
            
            if 'skus_validados' in st.session_state and not st.session_state['skus_validados'].empty:
                st.markdown("### 3. Dados Extras (Opcional)")
                st.info("💡 Preencha SKUs relacionados (se houver variações de cor/voltagem) e o link do vídeo do fornecedor para enriquecer o roteiro.")
                
                # Editor Interativo
                df_edited = st.data_editor(
                    st.session_state['skus_validados'],
                    use_container_width=True,
                    disabled=["SKU Principal"],
                    hide_index=True,
                    key="editor_pre_gen",
                    column_config={
                        "Outros Códigos (Cor/Voltagem)": st.column_config.TextColumn(
                            "Outros Códigos (Cor/Voltagem)",
                            help="Cole SKUs relacionados separados por espaço ou vírgula",
                            width="large"
                        ),
                        "Vídeo do Fornecedor (Link)": st.column_config.LinkColumn(
                            "Vídeo do Fornecedor (Link)",
                            help="Insira o link do YouTube ou Drive do fornecedor",
                            width="large"
                        )
                    }
                )
                
                if st.button("🚀 Iniciar Extração e Geração", use_container_width=True, type="primary", disabled=geracao_bloqueada, key="btn_auto"):
                    if geracao_bloqueada:
                        st.warning("🚧 Este formato de roteiro ainda está em desenvolvimento. Selecione 'NW (NewWeb)' para continuar.")
                        st.stop()
                    
                    modelo_id = st.session_state.get('modelo_llm', 'gemini-2.5-flash')
                    
                    # Validação genérica de API Key baseada no provider
                    _provider = modelo_id.split('/')[0] if '/' in modelo_id else 'gemini'
                    _env_var = PROVIDER_KEY_MAP.get(_provider)
                    if _env_var and not os.environ.get(_env_var):
                        st.warning(f"⚠️ Forneça a chave `{_env_var}` no painel de Configurações.")
                    else:
                        try:
                            agent = RoteiristaAgent(
                                supabase_client=st.session_state.get('supabase_client'),
                                model_id=modelo_id
                            )
                            roteiros = []
                            base_count = get_total_script_count(st.session_state.get('supabase_client'))
                            
                            progress = st.progress(0, text="Iniciando extração...")
                            
                            total_skus = len(df_edited)
                            for i, row in df_edited.iterrows():
                                code = str(row['SKU Principal']).strip()
                                sub_skus = str(row['Outros Códigos (Cor/Voltagem)']).strip()
                                video_url = str(row['Vídeo do Fornecedor (Link)']).strip()
                                
                                import time
                                
                                progress.progress(
                                    (i) / total_skus,
                                    text=f"🔍 [{code}] Buscando página na Magalu... ({i+1}/{total_skus})"
                                )
                                
                                # 1. Gemini extrai dados do produto via URL
                                ficha_extraida = scrape_with_gemini(code)
                                
                                progress.progress(
                                    (i + 0.5) / total_skus,
                                    text=f"✍️ [{code}] Analisando contexto e escrevendo roteiro... ({i+1}/{total_skus})"
                                )
                                
                                
                                # 2. Gera o roteiro com os dados extraídos (retorna dict)
                                txt_ficha = ficha_extraida.get('text', str(ficha_extraida)) if isinstance(ficha_extraida, dict) else str(ficha_extraida)
                                
                                # Verificação anti-alucinação: se o scraper falhar, não pedimos pro agente inventar
                                if "Não foi possível extrair dados" in txt_ficha or "⚠️" in txt_ficha:
                                    roteiro_texto = (
                                        "⚠️ EXTRAÇÃO AUTOMÁTICA FALHOU\n\n"
                                        "Não conseguimos encontrar os detalhes técnicos para este código automaticamente.\n\n"
                                        "POR FAVOR, COLE A FICHA TÉCNICA MANUALMENTE ABAIXO E CLIQUE EM 'GERAR' NOVAMENTE."
                                    )
                                    resultado = {
                                        "roteiro": roteiro_texto,
                                        "model_id": "-",
                                        "tokens_in": 0,
                                        "tokens_out": 0,
                                        "custo_brl": 0.0
                                    }
                                    nome_p = f"SKU {code} (Falha na Extração)"
                                else:
                                    # Extrai nome do produto (primeira linha da ficha)
                                    nome_p = txt_ficha.split('\n')[0].strip() if txt_ficha else "Produto"
                                    
                                    resultado = agent.gerar_roteiro(
                                        ficha_extraida, 
                                        modo_trabalho=modo_selecionado, 
                                        mes=mes_selecionado, 
                                        data_roteiro=data_roteiro_str,
                                        codigo=code,
                                        nome_produto=nome_p,
                                        sub_skus=sub_skus,
                                        video_url=video_url
                                    )
                                    roteiro_texto = resultado["roteiro"]
                                
                                # Atribuímos o número sequencial histórico (o último é o número mais alto)
                                global_id = base_count + i + 1
                                
                                roteiros.insert(0, { # Insere no INÍCIO para o último ficar no topo
                                    "ficha": ficha_extraida,
                                    "roteiro_original": roteiro_texto,
                                    "categoria_id": cat_selecionada_id,
                                    "codigo": code,
                                    "model_id": resultado["model_id"],
                                    "tokens_in": resultado["tokens_in"],
                                    "tokens_out": resultado["tokens_out"],
                                    "custo_brl": resultado["custo_brl"],
                                    "id_sequencial": global_id, # Deprecated
                                    "global_num": global_id,
                                    "mes": mes_selecionado, # Salva o mês de lançamento
                                    "sub_skus": sub_skus,
                                    "video_url": video_url
                                })
                                
                                progress.progress(
                                    (i + 1) / total_skus,
                                    text=f"✅ [{code}] Roteiro finalizado! ({i+1}/{total_skus})"
                                )
                                
                                # Auto-log no histórico (silencioso) com tracking de custo
                                try:
                                    sp_hist = st.session_state.get('supabase_client')
                                    if sp_hist:
                                        ficha_text = ficha_extraida.get('text', '') if isinstance(ficha_extraida, dict) else str(ficha_extraida)
                                        sp_hist.table("nw_historico_roteiros").insert({
                                            "codigo_produto": code,
                                            "modo_trabalho": modo_selecionado,
                                            "roteiro_gerado": roteiro_texto,
                                            "ficha_extraida": ficha_text[:5000],
                                            "modelo_llm": resultado["model_id"],
                                            "tokens_entrada": resultado["tokens_in"],
                                            "tokens_saida": resultado["tokens_out"],
                                            "custo_estimado_brl": resultado["custo_brl"]
                                        }).execute()
                                except Exception:
                                    pass  # Não bloqueia a geração se o log falhar
                                
                                # Delay para evitar 429 Too Many Requests
                                if i < total_skus - 1:
                                    progress.progress((i + 0.8) / total_skus, text=f"⏳ [{code}] Cota de segurança... Aguardando 5s.")
                                    time.sleep(5)
                            
                            progress.progress(1.0, text="✅ Lote Concluído com Sucesso!")
                            st.session_state['data_roteiro_global'] = data_roteiro_str
                            st.session_state['mes_global'] = mes_selecionado
                            if 'roteiros' not in st.session_state:
                                st.session_state['roteiros'] = []
                            # Prepend o novo lote ao início da lista global da sessão
                            st.session_state['roteiros'] = roteiros + st.session_state.get('roteiros', [])
                            st.session_state['roteiro_ativo_idx'] = 0 # Foca no mais novo
                            st.rerun() 
                            
                        except Exception as e:
                            st.error(f"Erro na geração: {e}")
        
        with tab_manual:
            # --- MODO MANUAL (FALLBACK) ---
            st.markdown("### 1. Dados dos Produtos")
            st.markdown("<p style='font-size: 14px; color: #8b92a5'>Cole o código e a ficha técnica dos produtos:</p>", unsafe_allow_html=True)
            
            if 'num_fichas' not in st.session_state:
                st.session_state['num_fichas'] = 1
                
            fichas_informadas = []
            
            for i in range(st.session_state['num_fichas']):
                col_sku_man, col_ficha_man = st.columns([1, 3])
                with col_sku_man:
                    sku_man = st.text_input(f"Cód. Produto {i+1}", key=f"sku_man_{i}", placeholder="Ex: 2403047")
                with col_ficha_man:
                    val = st.text_area(
                        f"Ficha Técnica {i+1}",
                        height=100,
                        key=f"ficha_input_{i}",
                        placeholder="Cole a ficha técnica aqui..."
                    )
                fichas_informadas.append({"sku": sku_man, "ficha": val})
                
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

            st.markdown("---")
            
            col_m_man, col_d_man = st.columns(2)
            with col_m_man:
                st.markdown("**Mês de Lançamento**")
                mes_selecionado_man = st.selectbox(
                    "Mês de Lançamento",
                    ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"],
                    index=2, # MAR
                    key="mes_man",
                    label_visibility="collapsed"
                )
            with col_d_man:
                st.markdown("**Data do Roteiro**")
                now_sp_man = get_now_sp()
                data_roteiro_man = st.date_input("Data do Roteiro:", value=now_sp_man, format="DD/MM/YYYY", key="date_man", label_visibility="collapsed")
                data_roteiro_str_man = data_roteiro_man.strftime('%d/%m/%y')
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("🚀 Gerar Roteiros a partir de Fichas", use_container_width=True, type="primary", key="btn_manual"):
                fichas_validas = [f for f in fichas_informadas if f["ficha"].strip() and f["sku"].strip()]
                
                if not fichas_validas:
                    st.warning("⚠️ Preencha o Código e a Ficha Técnica de pelo menos um produto.")
                else:
                    modelo_id = st.session_state.get('modelo_llm', 'gemini-2.5-flash')
                    _provider = modelo_id.split('/')[0] if '/' in modelo_id else 'gemini'
                    _env_var = PROVIDER_KEY_MAP.get(_provider)
                    if _env_var and not os.environ.get(_env_var):
                        st.warning(f"⚠️ Forneça a chave `{_env_var}` no painel de Configurações.")
                    else:
                        with st.spinner(f"Processando {len(fichas_validas)} roteiro(s)..."):
                            try:
                                agent = RoteiristaAgent(
                                    supabase_client=st.session_state.get('supabase_client'),
                                    model_id=modelo_id
                                )
                                roteiros = []
                                # Busca a base do histórico para numeração
                                base_count = get_total_script_count(st.session_state.get('supabase_client'))
                                
                                for i, item_man in enumerate(fichas_validas):
                                    ficha = item_man["ficha"]
                                    code = item_man["sku"]
                                    # Extrai nome do produto da ficha manual (primeira linha)
                                    nome_p_man = ficha.split('\n')[0].strip() if ficha else "Produto"
                                    
                                    resultado = agent.gerar_roteiro(
                                        ficha, 
                                        modo_trabalho="NW (NewWeb)", 
                                        mes=mes_selecionado_man, 
                                        data_roteiro=data_roteiro_str_man,
                                        codigo=code,
                                        nome_produto=nome_p_man
                                    )
                                    roteiro_texto = resultado["roteiro"]
                                    
                                    # Atribuímos o número sequencial histórico
                                    global_id = base_count + i + 1

                                    roteiros.insert(0, { # Newest at the beginning
                                        "ficha": ficha,
                                        "roteiro_original": roteiro_texto,
                                        "categoria_id": cat_selecionada_id,
                                        "codigo": code,
                                        "model_id": resultado["model_id"],
                                        "tokens_in": resultado["tokens_in"],
                                        "tokens_out": resultado["tokens_out"],
                                        "custo_brl": resultado["custo_brl"],
                                        "global_num": global_id,
                                        "mes": mes_selecionado_man
                                    })

                                    # Auto-log no histórico (Modo Manual)
                                    try:
                                        sp_hist = st.session_state.get('supabase_client')
                                        if sp_hist:
                                            sp_hist.table("nw_historico_roteiros").insert({
                                                "codigo_produto": code,
                                                "modo_trabalho": "Manual NW",
                                                "roteiro_gerado": roteiro_texto,
                                                "ficha_extraida": ficha[:5000],
                                                "modelo_llm": resultado["model_id"],
                                                "tokens_entrada": resultado["tokens_in"],
                                                "tokens_saida": resultado["tokens_out"],
                                                "custo_estimado_brl": resultado["custo_brl"]
                                            }).execute()
                                    except Exception:
                                        pass

                                    # Delay de segurança extra
                                    if i < len(fichas_validas) - 1:
                                        import time
                                        time.sleep(5)

                                st.session_state['data_roteiro_global'] = data_roteiro_str_man
                                st.session_state['mes_global'] = mes_selecionado_man
                                if 'roteiros' not in st.session_state:
                                    st.session_state['roteiros'] = []
                                # Prepend para o topo
                                st.session_state['roteiros'] = roteiros + st.session_state.get('roteiros', [])
                                st.session_state['roteiro_ativo_idx'] = 0
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro na geração: {e}")

    # --- SCRIPTS DA SESSÃO (CARDS VISÍVEIS — SEM EXPANDER) ---
    if 'roteiros' in st.session_state and st.session_state['roteiros']:
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Cards horizontais de seleção
        n_roteiros = len(st.session_state['roteiros'])
        cols_sessao = st.columns(min(4, n_roteiros))
        for idx, r_item in enumerate(st.session_state['roteiros']):
            num_tag = f"#{r_item.get('global_num', '?')}"
            codigo_card = r_item.get('codigo', '...')
            modelo_tag = r_item.get('model_id', '').split('/')[-1][:12]
            is_active = st.session_state.get('roteiro_ativo_idx', 0) == idx
            with cols_sessao[idx % len(cols_sessao)]:
                if st.button(
                    f"{codigo_card}\n{modelo_tag}",
                    key=f"session_btn_{idx}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary"
                ):
                    st.session_state['roteiro_ativo_idx'] = idx
                    st.rerun()

    # --- HISTÓRICO DO BANCO (Expandível, separado) ---
    if 'supabase_client' in st.session_state:
        with st.expander("📜 Histórico do Banco de Dados", expanded=False):
            sp_h = st.session_state['supabase_client']
            try:
                res_recent = sp_h.table("nw_historico_roteiros").select("criado_em, codigo_produto, modo_trabalho, roteiro_gerado, ficha_extraida, modelo_llm, custo_estimado_brl").order('criado_em', desc=True).limit(50).execute()
                
                if res_recent.data:
                    df_recent = pd.DataFrame(res_recent.data)
                    df_recent['data_simples'] = pd.to_datetime(df_recent['criado_em']).dt.date
                    
                    search_q = st.text_input("🔍 Buscar no histórico:", placeholder="Nome ou SKU...", key="hist_search")
                    if search_q:
                        df_recent = df_recent[
                            df_recent['codigo_produto'].str.contains(search_q, case=False, na=False) |
                            df_recent['roteiro_gerado'].str.contains(search_q, case=False, na=False)
                        ]
                    
                    datas_unicas = df_recent['data_simples'].unique()
                    
                    for dia in datas_unicas:
                        dia_df = df_recent[df_recent['data_simples'] == dia]
                        with st.expander(f"📁 {dia.strftime('%d/%m/%Y')}", expanded=False):
                            cols_db = st.columns(4)
                            for i, (_, r_row) in enumerate(dia_df.iterrows()):
                                # Inverte a numeração para que o primeiro (mais antigo do dia) seja #1
                                n_hist = len(dia_df) - i
                                btn_label = f"👁️ {r_row['codigo_produto']} ({r_row['modo_trabalho'][:2]})"
                                with cols_db[i % 4]:
                                    if st.button(btn_label, key=f"recall_{r_row['criado_em']}", use_container_width=True):
                                        rec_item = {
                                            "ficha": r_row['ficha_extraida'],
                                            "roteiro_original": r_row['roteiro_gerado'],
                                            "categoria_id": 1,
                                            "codigo": r_row['codigo_produto'],
                                            "model_id": r_row['modelo_llm'],
                                            "custo_brl": r_row['custo_estimado_brl']
                                        }
                                        try:
                                            first_line = r_row['roteiro_gerado'].split('\n')[0]
                                            if "NW LU" in first_line:
                                                parts = first_line.split()
                                                if len(parts) >= 3:
                                                    rec_item["mes"] = parts[2]
                                        except:
                                            pass
                                        if 'roteiros' not in st.session_state:
                                            st.session_state['roteiros'] = []
                                        
                                        if not any(x.get('codigo') == rec_item['codigo'] for x in st.session_state['roteiros']):
                                            st.session_state['roteiros'].insert(0, rec_item)
                                            st.session_state['roteiro_ativo_idx'] = 0
                                            st.rerun()
                                        else:
                                            st.info("Este roteiro já está na sua mesa.")
                else:
                    st.info("Nenhum histórico recente no banco.")
            except Exception as e:
                st.error(f"Erro ao carregar histórico: {e}")

    # --- CANVA DO ROTEIRO ATIVO (AGORA OCUPANDO TODA A LARGURA) ---
    if 'roteiros' in st.session_state and st.session_state['roteiros']:
        # Botão para baixar todos os roteiros em um ZIP (Full Width)
        zip_bytes, zip_filename = export_all_roteiros_zip(
            st.session_state['roteiros'], 
            selected_month=st.session_state.get('mes_global', 'FEV'),
            selected_date=st.session_state.get('data_roteiro_global')
        )
        st.download_button(
            label="📦 BAIXAR TODOS SESSÃO ATUAL (ZIP)",
            data=zip_bytes,
            file_name=zip_filename,
            mime="application/zip",
            use_container_width=True,
            type="primary",
            help="Baixa todos os roteiros recém gerados da sessão em um arquivo zipado."
        )
        
        st.divider()

        # Pega o índice ativo setado pelos botões na coluna esquerda
        idx = st.session_state.get('roteiro_ativo_idx', 0)
        
        if idx < len(st.session_state['roteiros']):
            item = st.session_state['roteiros'][idx]
            ficha_raw = item.get('ficha', '')
            ficha_str = ficha_raw.get('text', str(ficha_raw)) if isinstance(ficha_raw, dict) else str(ficha_raw)
            linhas_ficha = ficha_str.split('\n')
            titulo_curto = linhas_ficha[0][:60] if linhas_ficha and len(linhas_ficha[0]) > 2 else f"Produto {idx+1}"
            cat_id_roteiro = item.get("categoria_id", cat_selecionada_id)
            codigo_produto = item.get("codigo", "")
            
            custo = item.get('custo_brl', 0)
            tag_custo = "⚡ Gratuito" if custo == 0 else f"💲 R$ {custo:.4f}"
            tokens_text = "Sem Custo de Tokens" if custo == 0 else f"{item.get('tokens_in', 0)} / {item.get('tokens_out', 0)} tk"
            
            # Container estilizado para o roteiro ativo (Header Card)
            st.markdown(f"""
            <div style='background: #1e2530; padding: 20px; border-radius: 12px; border: 1px solid #0086ff; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: start;'>
                <div>
                    <h4 style='margin: 0; color: #0086ff; font-weight: 700;'>✨ Edição: {codigo_produto}</h4>
                    <p style='margin: 5px 0 0 0; font-size: 13px; color: #8b92a5;'>{titulo_curto}</p>
                </div>
                <div style='text-align: right;'>
                    <span style='background: rgba(0, 134, 255, 0.1); color: #0086ff; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;'>{item.get('model_id', 'LLM')} | {tag_custo}</span>
                    <div style='margin-top: 5px; font-size: 10px; color: #4a5568;'>{tokens_text}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
            # O Canva do Roteiro Ativo
            with st.container(border=True):
                # Chave única por idx e código para garantir atualização ao trocar card
                editor_key = f"editor_{idx}_{codigo_produto}"
                
                # Força a atualização do texto quando o card ativo muda
                if f"last_processed_idx" not in st.session_state or st.session_state.get("last_processed_idx") != idx:
                    st.session_state[editor_key] = item['roteiro_original']
                    st.session_state["last_processed_idx"] = idx

                edited_val = st.text_area(
                    "Editor",
                    value=st.session_state.get(editor_key, item['roteiro_original']),
                    height=450,
                    key=editor_key,
                    label_visibility="collapsed"
                )
            sp_cli = st.session_state.get('supabase_client', None)
                
            # Barra de Ações (3 colunas iguais)
            st.markdown("<br>", unsafe_allow_html=True)
            
            col_docx, col_calib, col_ouro = st.columns(3)
            
            with col_docx:
                docx_edited_bytes, docx_edited_fn = export_roteiro_docx(
                    edited_val,
                    code=codigo_produto,
                    product_name=titulo_curto,
                    selected_month=item.get('mes', st.session_state.get('mes_global', 'FEV')),
                    selected_date=st.session_state.get('data_roteiro_global')
                )
                st.download_button(
                    label="📥 Baixar DOCX",
                    data=docx_edited_bytes,
                    file_name=docx_edited_fn,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"export_edit_{idx}",
                    use_container_width=True,
                    type="secondary"
                )
                
            with col_calib:
                if st.button("🚀 Calibrar IA", key=f"fino_{idx}", use_container_width=True, type="primary"):
                    if sp_cli:
                        st.toast("🧠 Iniciando calibragem...", icon="⏳")
                        with st.spinner("A IA está analisando suas correções..."):
                            try:
                                res_c = sp_cli.table("nw_categorias").select("id, nome").execute()
                                lista_c = res_c.data if hasattr(res_c, 'data') else []
                            except:
                                lista_c = []
                                
                            calc = _temp_agent.analisar_calibracao(item['roteiro_original'], edited_val, lista_c, codigo_produto)
                            salvar_calibracao_ouro(sp_cli, calc['categoria_id'], item['roteiro_original'], edited_val, calc['percentual'], calc['aprendizado'], calc['codigo_produto'], titulo_curto, calc.get('modelo_calibragem', 'N/A'))
                            _auto_salvar_fonetica(sp_cli, calc.get('fonetica_regras', []))
                            _auto_salvar_estrutura(sp_cli, calc.get('estrutura_regras', []))
                            _auto_salvar_persona(sp_cli, calc.get('persona_regras', []))
                    else:
                        st.error("Conecte o Supabase primeiro.")
            
            with col_ouro:
                if st.button("🏆 Enviar Ouro", key=f"ouro_{idx}", use_container_width=True, type="secondary"):
                    salvar_ouro(sp_cli, cat_id_roteiro, titulo_curto, edited_val)

        if st.button("🗑️ Limpar Mesa de Trabalho", use_container_width=True, type="secondary"):
            if 'roteiros' in st.session_state:
                del st.session_state['roteiros']
            if 'roteiro_ativo_idx' in st.session_state:
                del st.session_state['roteiro_ativo_idx']
            st.rerun()
    else:
        st.markdown(
            """
            <div style='display: flex; flex-direction: column; height: 250px; align-items: center; justify-content: center; border: 2px dashed #2A3241; border-radius: 12px; color: #8b92a5; text-align: center; padding: 30px'>
            <div style='font-size: 40px; margin-bottom: 12px;'>✍️</div>
            <div style='font-size: 16px; font-weight: 600; color: #c9d1e0;'>Nenhum roteiro na mesa</div>
            <div style='font-size: 13px; margin-top: 6px;'>Abra "Inserir Códigos e Gerar" acima, cole os SKUs e clique em Gerar.</div>
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
            res_est = sp_client.table("nw_treinamento_estruturas").select("*").execute()
            res_fon = sp_client.table("nw_treinamento_fonetica").select("*").execute()
            res_ouro = sp_client.table("nw_roteiros_ouro").select("*").execute()
            res_cats = sp_client.table("nw_categorias").select("*").execute()
            res_nuan = sp_client.table("nw_treinamento_nuances").select("*").execute()
            
            df_est = pd.DataFrame(res_est.data if hasattr(res_est, 'data') else [])
            df_fon = pd.DataFrame(res_fon.data if hasattr(res_fon, 'data') else [])
            df_ouro = pd.DataFrame(res_ouro.data if hasattr(res_ouro, 'data') else [])
            df_cats = pd.DataFrame(res_cats.data if hasattr(res_cats, 'data') else [])
            df_nuan = pd.DataFrame(res_nuan.data if hasattr(res_nuan, 'data') else [])
            
            # --- CONVERSÃO DE FUSO HORÁRIO GLOBAL (UTC -> SÃO PAULO) ---
            for df in [df_est, df_fon, df_ouro, df_cats, df_nuan]:
                if not df.empty and 'criado_em' in df.columns:
                    df['criado_em'] = df['criado_em'].apply(convert_to_sp_time)
                    
        except Exception as e:
            st.error(f"Erro ao carregar dados do hub: {e}")
            df_est = df_fon = df_ouro = df_cats = df_nuan = pd.DataFrame()

        tab_nuan, tab_fb, tab_est, tab_fon, tab_ouro, tab_cat = st.tabs(["🧠 Nuances", "⚖️ Calibragem", "💬 Estruturas", "🗣️ Fonética", "🏆 Roteiros Ouro", "📂 Categorias"])
        
        with tab_nuan:
            st.markdown("### 🧠 Treinamento de Nuances e Construção")
            st.caption("Ajude a IA a entender as sutilezas da língua portuguesa e a evitar construções artificiais.")
            
            with st.form("form_nuance", clear_on_submit=True):
                n_frase = st.text_area("Frase gerada pela IA (O que evitar):", placeholder="Ex: 'Este produto possui uma característica de cor azul que é muito legal.'")
                n_analise = st.text_area("Análise Crítica (Por que é ruim?):", placeholder="Ex: 'Construção redundante e pobre. O uso de 'possui' com 'característica de' soa burocrático. 'Muito legal' é genérico.'")
                n_exemplo = st.text_area("Exemplo Ouro (Como seria o ideal?):", placeholder="Ex: 'Com um tom azul vibrante, ele se destaca pelo design moderno.'")
                
                if st.form_submit_button("📥 Registrar Nuance", type="primary", use_container_width=True):
                    if n_frase.strip() and n_analise.strip():
                        salvar_nuance(sp_client, n_frase, n_analise, n_exemplo)
                        st.rerun()
                    else:
                        st.warning("Preencha pelo menos a frase da IA e a análise crítica.")
            
            st.divider()
            if not df_nuan.empty:
                st.markdown("#### 📋 Nuances Registradas")
                st.dataframe(df_nuan[['criado_em', 'frase_ia', 'analise_critica', 'exemplo_ouro']].sort_values(by='criado_em', ascending=False), use_container_width=True)
            else:
                st.info("Nenhuma nuance registrada ainda.")
        
        with tab_cat:
            st.markdown("### 📂 Gestão de Categorias e Tom de Voz")
            st.caption("A IA usa o 'Tom de Voz' de cada categoria para adaptar a linguagem do roteiro.")
            
            with st.form("form_nova_cat", clear_on_submit=True):
                c_nome = st.text_input("Nome da Categoria (Ex: Eletrodomésticos, Beleza)")
                c_tom = st.text_area("Tom de Voz / Diretrizes", placeholder="Ex: Linguagem alegre, empolgada, focada em praticidade do dia a dia...")
                if st.form_submit_button("➕ Cadastrar Nova Categoria", type="primary"):
                    if c_nome.strip() and c_tom.strip():
                        sp_client.table("nw_categorias").insert({"nome": c_nome, "tom_de_voz": c_tom}).execute()
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
            st.markdown("### ⚖️ Calibragem: IA vs Aprovado")
            st.caption("Compare o que a IA gerou com o roteiro final aprovado. A Suíte Magalu calculará o nível de aproveitamento e extrairá Diretrizes de Redação automaticamente.")
            
            st.info("""
            **⭐ Como funciona a Nova Régua de Calibragem?**
            - **4.8 a 5.0 (Quase Perfeito):** O humano fez apenas ajustes finos de estilo, conectivos ou pontuação.
            - **4.0 a 4.7 (Muito Bom):** Mudanças notáveis de estilo, encurtamento para fluidez ou troca de jargões técnicos.
            - **3.0 a 3.9 (Regular):** Mudança Estrutural. Adição de infos que faltavam ou reconstrução de blocos inteiros.
            - **< 3.0 (Ruim):** Erro Grave. A IA errou feio o tom de voz, omitiu funcionalidades vitais ou o SKU.
            """)
            
            # --- FORMULÁRIO DE ENTRADA ---
            with st.form("form_calibracao", clear_on_submit=True):
                col_ia, col_breno = st.columns(2)
                with col_ia:
                    st.markdown("**🤖 ANTES (Roteiro da IA)**")
                    roteiro_ia_input = st.text_area("Cole aqui o roteiro original gerado pela IA:", height=200, key="calib_ia")
                with col_breno:
                    st.markdown("**✅ DEPOIS (Aprovado pelo Humano)**")
                    roteiro_breno_input = st.text_area("Cole aqui a versão final aprovada:", height=200, key="calib_breno")
                
                # A IA identificará a categoria automaticamente via analisar_calibracao
                
                submitted = st.form_submit_button("⚖️ Executar Calibragem e Salvar em Ouro", type="primary", use_container_width=True)
                if submitted:
                    if roteiro_ia_input.strip() and roteiro_breno_input.strip():
                        st.toast("🧠 Enviando para a IA analisar...", icon="⏳")
                        try:
                            # Usa qualquer provedor disponível (Puter/OpenRouter/Gemini)
                            # Determina qual model_id usar para instanciar o agente. Novo Default: DeepSeek (OpenRouter)
                            _calib_model = "gemini-2.5-flash"
                            # Verifica tanto env quanto secrets para garantir que DeepSeek seja priorizado se houver chave
                            openrouter_key = os.environ.get("OPENROUTER_API_KEY") or st.secrets.get("OPENROUTER_API_KEY")
                            puter_key = os.environ.get("PUTER_API_KEY") or st.secrets.get("PUTER_API_KEY")
                            gemini_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

                            if openrouter_key:
                                _calib_model = "openrouter/deepseek/deepseek-r1-0528:free"
                            elif puter_key:
                                _calib_model = "puter/x-ai/grok-4-1-fast"
                            elif gemini_key:
                                _calib_model = "gemini-2.5-flash"
                            else:
                                st.error("Nenhuma chave de IA configurada (OpenRouter, Puter ou Gemini).")
                                _calib_model = None
                            
                            if _calib_model:
                                ag = RoteiristaAgent(supabase_client=sp_client, model_id=_calib_model)
                                with st.spinner("🧠 Analisando a calibragem para identificar lições aprendidas..."):
                                    cats_list_manual = df_cats[['id', 'nome']].to_dict('records') if not df_cats.empty else []
                                    calc = ag.analisar_calibracao(roteiro_ia_input, roteiro_breno_input, cats_list_manual)
                                    
                                data = {
                                    "categoria_id": calc['categoria_id'],
                                    "roteiro_original_ia": roteiro_ia_input,
                                    "roteiro_perfeito": roteiro_breno_input,
                                    "nota_percentual": calc['percentual'],
                                    "aprendizado": calc['aprendizado'],
                                    "codigo_produto": calc['codigo_produto'],
                                    "titulo_produto": calc['codigo_produto'],
                                    "modelo_calibragem": calc.get('modelo_calibragem', 'N/A')
                                }
                                sp_client.table("nw_roteiros_ouro").insert(data).execute()
                                estrelas_ui = calc['percentual'] / 20.0
                                _score_color = '🟢' if estrelas_ui >= 4.0 else ('🟡' if estrelas_ui >= 3.0 else '🔴')
                                st.success(f"🏆 Salvo como Roteiro Ouro! {_score_color} Qualidade: {estrelas_ui:.1f} ⭐ | Código: {calc['codigo_produto']} | IA: {calc.get('modelo_calibragem', 'N/A')}")
                                n_f = _auto_salvar_fonetica(sp_client, calc.get('fonetica_regras', []))
                                n_e = _auto_salvar_estrutura(sp_client, calc.get('estrutura_regras', []))
                                n_p = _auto_salvar_persona(sp_client, calc.get('persona_regras', []))

                                if n_f > 0 or n_e > 0 or n_p > 0:
                                    st.session_state['show_calib_modal'] = {
                                        "calc": calc,
                                        "n_f": n_f, "n_e": n_e, "n_p": n_p,
                                        "estrelas": estrelas_ui,
                                        "score_color": _score_color
                                    }
                                else:
                                    st.info("A IA analisou as mudanças, mas não identificou padrões repetíveis para as tabelas de treinamento (apenas ajustes de estilo/contextuais).")
                                    import time
                                    time.sleep(3)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar calibragem: {e}")
                    else:
                        st.warning("Preencha ambos os campos (IA e Humano).")
            
            st.divider()
            st.markdown("#### 📋 Histórico de Calibragens Ouro")
            if not df_ouro.empty and 'nota_percentual' in df_ouro.columns:
                cols_view = ['criado_em', 'codigo_produto']
                if 'nota_percentual' in df_ouro.columns: cols_view.append('nota_percentual')
                if 'modelo_calibragem' in df_ouro.columns: cols_view.append('modelo_calibragem')
                if 'aprendizado' in df_ouro.columns: cols_view.append('aprendizado')
                
                df_view = df_ouro[cols_view].dropna(subset=['aprendizado']).copy()
                df_view = df_view.sort_values(by='criado_em', ascending=False).reset_index(drop=True)
                
                # Adiciona Sequential ID (#005, #004...) e Emojis de Qualidade
                total_calib = len(df_view)
                df_view.index = [f"#{total_calib - i:03d}" for i in range(total_calib)]
                
                if 'nota_percentual' in df_view.columns:
                    df_view['nota_percentual'] = df_view['nota_percentual'].apply(
                        lambda x: f"{'🟢' if x/20.0 >= 4.0 else ('🟡' if x/20.0 >= 3.0 else '🔴')} {x/20.0:.1f} ⭐ ({int(x)}%)"
                    )

                rename_map = {
                    'aprendizado': 'Memória da IA (Lição Aprendida)', 
                    'nota_percentual': 'Estrelas ⭐', 
                    'codigo_produto': 'SKU', 
                    'modelo_calibragem': 'IA Analista',
                    'criado_em': 'Data'
                }
                df_view.rename(columns={k: v for k, v in rename_map.items() if k in df_view.columns}, inplace=True)
                st.dataframe(df_view, use_container_width=True)
            else:
                st.info("Nenhuma calibragem ouro registrada ainda.")
                
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
                        sp_client.table("nw_roteiros_ouro").insert(data_ouro).execute()
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
                    res_cats_ouro = sp_client.table("nw_categorias").select("id, nome").execute()
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

# --- PÁGINA: GUIA DE MODELOS ---
elif page == "Guia de Modelos":
    st.subheader("🧪 Laboratório de LLMs: Descubra o Poder de cada IA")
    st.markdown("""
        Bem-vindo ao guia oficial de inteligência da **Magalu AI Suite**. Aqui você encontra os detalhes técnicos 
        e o perfil de 'personalidade' de cada modelo integrado para escolher o melhor para o seu lote.
    """)
    
    st.divider()
    
    # Categorizando modelos por provedor
    categorias = {
        "Google (Nativo)": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"],
        "Puter (Grok & Elite)": ["puter/x-ai/grok-4-1-fast", "puter/gpt-4o-mini", "puter/meta-llama/llama-3.1-70b-instruct", "puter/claude-3-5-sonnet"],
        "OpenRouter (Especializados)": [
            "openrouter/deepseek/deepseek-r1-0528:free",
            "openrouter/google/gemma-3-27b:free",
            "openrouter/meta-llama/llama-4-scout:free"
        ],
        "Z.ai & Moonshot": ["zai/glm-4.5-flash", "kimi/moonshot-v1-8k"]
    }
    
    # Invertemos o MODELOS_DISPONIVEIS para facilitar a busca pelo nome amigável
    NOME_AMIGAVEL = {v: k for k, v in MODELOS_DISPONIVEIS.items()}
    
    for cat_name, models in categorias.items():
        st.markdown(f"#### {cat_name}")
        cols = st.columns(2)
        for i, mid in enumerate(models):
            with cols[i % 2]:
                display_name = NOME_AMIGAVEL.get(mid, mid)
                # Extraindo o preço da label se houver
                preco_tag = "Grátis" if "Grátis" in display_name else "Pago/Créditos"
                bg_color = "rgba(0, 255, 136, 0.1)" if preco_tag == "Grátis" else "rgba(255, 75, 75, 0.1)"
                text_color = "#00ff88" if preco_tag == "Grátis" else "#ff4b4b"
                
                st.markdown(f"""
                <div style='background: #1e2530; padding: 20px; border-radius: 12px; border: 1px solid #2d3848; height: 180px; margin-bottom: 20px; position: relative;'>
                    <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
                        <span style='color: #0086ff; font-weight: 700; font-size: 14px;'>{display_name.split(' — ')[0]}</span>
                        <span style='background: {bg_color}; color: {text_color}; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600;'>{preco_tag}</span>
                    </div>
                    <p style='color: #8b92a5; font-size: 12px; margin-top: 15px; line-height: 1.5;'>{MODELOS_DESCRICAO.get(mid, "Sem descrição disponível.")}</p>
                    <div style='position: absolute; bottom: 15px; left: 20px; font-size: 9px; color: #4a5568;'>ID: {mid}</div>
                </div>
                """, unsafe_allow_html=True)
        st.write("")

# --- PÁGINA: CONFIGURAÇÕES ---
elif page == "Configurações":
    st.subheader("⚙️ Configurações do Sistema")
    st.markdown("Gerencie suas chaves de API de Inteligência Artificial e a conexão com o banco de dados Supabase em um só lugar.")
    st.divider()

    col_llm, col_db = st.columns(2)

    with col_llm:
        st.markdown("#### 🧠 Chaves de IA (LLMs)")
        st.caption("Adicione suas as chaves de API para desbloquear novos modelos.")
        
        keys_to_manage = [
            ("Gemini", "GEMINI_API_KEY", api_key_env),
            ("Puter (Grok/Llama)", "PUTER_API_KEY", puter_key_env),
            ("OpenAI (GPT)", "OPENAI_API_KEY", openai_key_env),
            ("OpenRouter", "OPENROUTER_API_KEY", openrouter_key_env),
            ("Z.ai (GLM)", "ZAI_API_KEY", zai_key_env),
            ("Moonshot (Kimi)", "KIMI_API_KEY", kimi_key_env)
        ]
        
        for name, env_var, current_val in keys_to_manage:
            with st.container():
                st.markdown(f"**{name}**")
                if env_var in os.environ and os.environ.get(env_var):
                    st.success("✅ Conectado e Ativo")
                else:
                    new_key = st.text_input(f"Token/API Key", type="password", key=f"key_in_{env_var}", label_visibility="collapsed", placeholder=f"Cole sua chave {name} aqui")
                    if new_key:
                        with open('.env', 'a', encoding='utf-8') as f:
                            f.write(f"\n{env_var}={new_key}")
                        os.environ[env_var] = new_key
                        st.toast(f"✅ {name} Adicionada com sucesso!")
                        st.rerun()
                st.write("") # Margem

    with col_db:
        st.markdown("#### 🗄️ Banco de Dados (Supabase)")
        st.caption("Conexão com o Supabase para salvar métricas e histórico de roteiros.")
        
        gemini_status = "Ativo" if api_key_env else "Inativo"
        supa_status_p = "Ativo" if supabase_client else "Inativo"

        supa_url_env = os.environ.get("SUPABASE_URL", "")
        supa_url_placeholder = supa_url_env[:30] + "..." if supa_url_env and len(supa_url_env) > 30 else ""
        
        st.markdown(f"**URL do Projeto** (Status: {supa_status_p})")
        supa_url_input = st.text_input(
            "URL Supabase",
            placeholder=supa_url_placeholder if supa_url_env else "Ex: https://xyz.supabase.co",
            label_visibility="collapsed"
        )
        
        st.markdown("**Role Key (Service)**")
        supa_key_input = st.text_input("API Key Supabase", type="password", placeholder="Cole sua Role Key (Service)", label_visibility="collapsed")
        
        if st.button("💾 Salvar Conexão Supabase", type="primary", use_container_width=True):
            if supa_url_input.strip() and supa_key_input.strip():
                with open('.env', 'a', encoding='utf-8') as f:
                    f.write(f"\nSUPABASE_URL={supa_url_input}")
                    f.write(f"\nSUPABASE_KEY={supa_key_input}")
                st.toast("✅ Conexão com o Supabase atualizada!", icon="🚀")
                import time
                time.sleep(1) # Aguarda para dar percepção de salvar
                st.rerun()
            else:
                st.error("Preencha a URL e a Key para salvar.")

# --- PÁGINA 1.5: HISTÓRICO ---
elif page == "Histórico":
    st.subheader("🕒 Histórico de Roteiros")
    st.markdown("Confira todos os roteiros gerados automaticamente pelo sistema com rastreamento de custo por geração.")
    
    if 'supabase_client' not in st.session_state:
        st.warning("Conecte o Supabase no painel lateral para visualizar o histórico.")
    else:
        sp_client = st.session_state['supabase_client']
        try:
            with st.spinner("Carregando histórico..."):
                res_hist = sp_client.table("nw_historico_roteiros").select("*").order('criado_em', desc=True).execute()
                
            if res_hist.data:
                df_hist = pd.DataFrame(res_hist.data)
                
                if not df_hist.empty and 'criado_em' in df_hist.columns:
                    df_hist['criado_em'] = df_hist['criado_em'].apply(convert_to_sp_time)
                
                total_registros = len(df_hist)
                
                # --- MÉTRICAS DE CUSTO ---
                custo_total = CUSTO_LEGADO_BRL
                custo_medio = 0.0
                modelo_mais_usado = "-"
                
                if 'custo_estimado_brl' in df_hist.columns:
                    custo_total += df_hist['custo_estimado_brl'].sum() or 0.0
                    custo_medio = custo_total / total_registros if total_registros > 0 else 0.0
                    
                if 'modelo_llm' in df_hist.columns:
                    try:
                        modelo_mais_usado = df_hist['modelo_llm'].mode().iloc[0] if not df_hist['modelo_llm'].dropna().empty else "-"
                    except Exception:
                        modelo_mais_usado = "-"
                
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                with col_m1:
                    st.markdown(f'<div class="metric-card-premium"><div class="metric-label">📝 Roteiros Gerados</div><div class="metric-value">{total_registros}</div></div>', unsafe_allow_html=True)
                with col_m2:
                    val_tot = f"R$ {custo_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    st.markdown(f'<div class="metric-card-premium"><div class="metric-label">💰 Custo Total</div><div class="metric-value">{val_tot}</div></div>', unsafe_allow_html=True)
                with col_m3:
                    val_med = f"R$ {custo_medio:,.4f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    st.markdown(f'<div class="metric-card-premium"><div class="metric-label">📋 Custo Médio</div><div class="metric-value">{val_med}</div></div>', unsafe_allow_html=True)
                with col_m4:
                    st.markdown(f'<div class="metric-card-premium"><div class="metric-label">🧠 Modelo Mais Usado</div><div class="metric-value">{modelo_mais_usado}</div></div>', unsafe_allow_html=True)
                
                st.divider()
                
                # --- BARRA DE FILTROS ---
                col_search, col_modo, col_modelo = st.columns([3, 1, 1])
                with col_search:
                    search = st.text_input("🔍 Filtrar por código ou palavra-chave:", placeholder="Ex: 240304700, Geladeira", label_visibility="collapsed")
                with col_modo:
                    modos_unicos = ["Todos"] + sorted(df_hist['modo_trabalho'].dropna().unique().tolist()) if 'modo_trabalho' in df_hist.columns else ["Todos"]
                    modo_filtro = st.selectbox("Modo", modos_unicos, label_visibility="collapsed")
                with col_modelo:
                    if 'modelo_llm' in df_hist.columns:
                        modelos_unicos = ["Todos"] + sorted(df_hist['modelo_llm'].dropna().unique().tolist())
                    else:
                        modelos_unicos = ["Todos"]
                    modelo_filtro = st.selectbox("Modelo", modelos_unicos, label_visibility="collapsed")
                
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
                
                # Filtro por Modelo LLM
                if modelo_filtro != "Todos" and 'modelo_llm' in df_hist.columns:
                    df_hist = df_hist[df_hist['modelo_llm'] == modelo_filtro]
                
                # Formata custo para exibição
                if 'custo_estimado_brl' in df_hist.columns:
                    df_hist['custo_brl'] = df_hist['custo_estimado_brl'].apply(
                        lambda x: f"R$ {x:,.4f}".replace(',', 'X').replace('.', ',').replace('X', '.') if pd.notna(x) and x > 0 else "-"
                    )
                else:
                    df_hist['custo_brl'] = "-"
                
                # Define o index da tabela para usar a lógica inversa (mais recentes com nº maior)
                df_hist.reset_index(drop=True, inplace=True)
                total_linhas = len(df_hist)
                df_hist.index = [f"#{total_linhas - i:03d}" for i in range(total_linhas)]
                
                # Colunas a exibir
                cols_display = ['criado_em', 'codigo_produto', 'modo_trabalho']
                if 'modelo_llm' in df_hist.columns:
                    cols_display.append('modelo_llm')
                cols_display.append('custo_brl')
                cols_display.append('roteiro_gerado')

                st.dataframe(
                    df_hist[cols_display], 
                    use_container_width=True,
                    height=600
                )
            else:
                st.info("Nenhum roteiro gerado ainda. Vá em 'Criar Roteiros' para começar!")
        except Exception as e:
            st.error(f"Erro ao carregar histórico: {e}")

# --- PÁGINA 3: DASHBOARD ---
elif page == "Dashboard":
    st.subheader("📊 Painel de Inteligência da IA")
    
    if 'supabase_client' not in st.session_state:
        st.warning("Conecte o Supabase no painel lateral para visualizar os dados.")
    else:
        sp_client = st.session_state['supabase_client']
        
        # Carrega dados do banco
        try:
            res_ouro = sp_client.table("nw_roteiros_ouro").select("*").execute()
            res_pers = sp_client.table("nw_treinamento_persona_lu").select("*").execute()
            res_fon = sp_client.table("nw_treinamento_fonetica").select("*").execute()
            res_cats = sp_client.table("nw_categorias").select("*").execute()
            res_est = sp_client.table("nw_treinamento_estruturas").select("*").execute()
            res_hist = sp_client.table("nw_historico_roteiros").select("criado_em, codigo_produto, modo_trabalho, modelo_llm, custo_estimado_brl").execute()
            res_nuan = sp_client.table("nw_treinamento_nuances").select("*").execute()
            
            ouro_data = res_ouro.data if hasattr(res_ouro, 'data') else []
            pers_data = res_pers.data if hasattr(res_pers, 'data') else []
            fon_data = res_fon.data if hasattr(res_fon, 'data') else []
            est_data = res_est.data if hasattr(res_est, 'data') else []
            hist_data = res_hist.data if hasattr(res_hist, 'data') else []
            nuan_data = res_nuan.data if hasattr(res_nuan, 'data') else []
            cats_dict = {c['id']: c['nome'] for c in res_cats.data} if hasattr(res_cats, 'data') else {}
            
            df_ouro = pd.DataFrame(ouro_data)
            df_pers = pd.DataFrame(pers_data)
            df_fon = pd.DataFrame(fon_data)
            df_est = pd.DataFrame(est_data)
            df_hist_dash = pd.DataFrame(hist_data)
            df_nuan = pd.DataFrame(nuan_data)
            
            # --- NOVA LÓGICA: df_fb agora vem de df_ouro (Calibragens) ---
            if not df_ouro.empty:
                # Primeiro mapeia a categoria em df_ouro
                df_ouro['categoria'] = df_ouro['categoria_id'].map(cats_dict).fillna("Genérico")
                
                df_fb = df_ouro[df_ouro['roteiro_original_ia'].notna()].copy()
                # Converte nota_percentual (0-100) para labels de sentimento
                def map_sentimento(p):
                    if p >= 96: return "Ajuste Fino"
                    if p >= 85: return "Edição Moderada"
                    if p >= 60: return "Mudança Estrutural"
                    return "Reescrita Pesada"
                df_fb['avaliacao_label'] = df_fb['nota_percentual'].apply(map_sentimento)
                df_fb['estrela'] = df_fb['nota_percentual'].apply(lambda x: f"{(x/20.0):.1f} ⭐")
            else:
                df_fb = pd.DataFrame()
            
            # --- CONVERSÃO DE FUSO HORÁRIO GLOBAL (UTC -> SÃO PAULO) ---
            for df in [df_ouro, df_pers, df_fon, df_est, df_nuan]:
                if not df.empty and 'criado_em' in df.columns:
                    df['criado_em'] = df['criado_em'].apply(convert_to_sp_time)
            
            # A coluna 'categoria' já foi mapeada acima na nova lógica
            total_ouro = len(df_ouro)
            total_historico = len(df_hist_dash)
            
            # --- SEÇÃO DE FILTROS GLOBAIS ---
            with st.container():
                col_f1, col_f2 = st.columns([1, 2])
                with col_f1:
                    hoje = datetime.now()
                    periodo = st.date_input(
                        "📅 Período de Análise:",
                        value=(hoje.replace(day=1), hoje),
                        format="DD/MM/YYYY"
                    )
                with col_f2:
                    search_dash = st.text_input("🔍 Busca Global (Código/Termo):", placeholder="Filtrar tabelas e métricas...")

            # Aplicar Filtro de Data
            if len(periodo) == 2:
                start_date, end_date = pd.to_datetime(periodo[0]), pd.to_datetime(periodo[1])
                # Ajuste para cobrir o dia inteiro da data final
                end_date = end_date.replace(hour=23, minute=59, second=59)
                
                df_ouro = df_ouro[(pd.to_datetime(df_ouro['criado_em']).dt.tz_localize(None) >= start_date) & (pd.to_datetime(df_ouro['criado_em']).dt.tz_localize(None) <= end_date)] if not df_ouro.empty else df_ouro
                df_pers = df_pers[(pd.to_datetime(df_pers['criado_em']).dt.tz_localize(None) >= start_date) & (pd.to_datetime(df_pers['criado_em']).dt.tz_localize(None) <= end_date)] if not df_pers.empty else df_pers
                df_fon = df_fon[(pd.to_datetime(df_fon['criado_em']).dt.tz_localize(None) >= start_date) & (pd.to_datetime(df_fon['criado_em']).dt.tz_localize(None) <= end_date)] if not df_fon.empty else df_fon
                df_est = df_est[(pd.to_datetime(df_est['criado_em']).dt.tz_localize(None) >= start_date) & (pd.to_datetime(df_est['criado_em']).dt.tz_localize(None) <= end_date)] if not df_est.empty else df_est
                df_hist_dash = df_hist_dash[(pd.to_datetime(df_hist_dash['criado_em']).dt.tz_localize(None) >= start_date) & (pd.to_datetime(df_hist_dash['criado_em']).dt.tz_localize(None) <= end_date)] if not df_hist_dash.empty else df_hist_dash
                df_nuan = df_nuan[(pd.to_datetime(df_nuan['criado_em']).dt.tz_localize(None) >= start_date) & (pd.to_datetime(df_nuan['criado_em']).dt.tz_localize(None) <= end_date)] if not df_nuan.empty else df_nuan

            # Aplicar Filtro de Busca
            if search_dash:
                def filter_search(df, term):
                    if df.empty: return df
                    mask = df.astype(str).apply(lambda row: row.str.contains(term, case=False).any(), axis=1)
                    return df[mask]

                df_ouro = filter_search(df_ouro, search_dash)
                df_pers = filter_search(df_pers, search_dash)
                df_fon = filter_search(df_fon, search_dash)
                df_est = filter_search(df_est, search_dash)
                df_hist_dash = filter_search(df_hist_dash, search_dash)
                df_nuan = filter_search(df_nuan, search_dash)

            # Recalcular métricas após filtros
            if not df_ouro.empty and 'nota_percentual' in df_ouro.columns:
                taxa_m = df_ouro['nota_percentual'].mean()
                taxa_aprovacao = float(taxa_m) if pd.notna(taxa_m) else 0.0
            else:
                taxa_aprovacao = 0.0
            
            total_ouro = len(df_ouro)
            total_historico = len(df_hist_dash)
            
            # === SEÇÃO 1: MÉTRICAS PREMIUM (HTML/CSS) ===
            custo_total_dash = CUSTO_LEGADO_BRL
            if not df_hist_dash.empty and 'custo_estimado_brl' in df_hist_dash.columns:
                custo_total_dash += df_hist_dash['custo_estimado_brl'].sum() or 0.0
            
            # Cálculo de Cor Dinâmica para o Score (0=Vermelho, 100=Verde)
            def get_score_color(val):
                if val >= 80: return "#10b981" # Verde
                if val >= 50: return "#f59e0b" # Laranja/Amarelo
                return "#ef4444" # Vermelho
            
            score_color = get_score_color(taxa_aprovacao)

            st.markdown(f"""
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px;">
                    <div class="metric-card-premium">
                        <div class="metric-label">📝 Roteiros Gerados</div>
                        <div class="metric-value">{total_historico}</div>
                    </div>
                    <div class="metric-card-premium">
                        <div class="metric-label">💰 Custo Total</div>
                        <div class="metric-value" style="color: #10b981 !important;">R$ {custo_total_dash:,.2f}</div>
                    </div>
                    <div class="metric-card-premium">
                        <div class="metric-label">🏆 Roteiros Ouro</div>
                        <div class="metric-value" style="color: #f59e0b !important;">{total_ouro}</div>
                    </div>
                    <div class="metric-card-premium">
                        <div class="metric-label">🎯 Taxa Aprovação</div>
                        <div class="metric-value" style="color: {score_color} !important;">{taxa_aprovacao:.1f}%</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            with st.popover("ℹ️ Entenda a Métrica de Aprovação", use_container_width=False):
                st.markdown("#### 🎯 Qualidade Medida via Calibragem")
                st.markdown("A **Taxa de Aprovação** não é mais uma nota subjetiva dada por botões. Ela é a **média do aproveitamento real** dos roteiros gerados.")
                st.markdown("Toda vez que você edita um roteiro e clica em `🚀 Enviar Calibragem para a IA`, uma **IA especializada** atua como QA (Quality Assurance). Ela compara o rascunho original com a sua edição final e calcula qual o percentual (%) das ideias geradas que foi mantido por você.")
                st.info("💡 **Exemplo:** Se a IA nota que 90% das ideias do rascunho foram mantidas, a nota de aprovação daquele roteiro é 90%. O Dashboard exibe a média histórica de todas essas calibrações.")
            
            st.divider()
            
            # === SEÇÃO 2: PERFORMANCE E SAÚDE ===
            col_gauge, col_chart_kb = st.columns([1, 2])
            
            with col_gauge:
                st.markdown("#### 🎯 Performance da IA")
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = taxa_aprovacao,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "Aprovação (%)", 'font': {'size': 18}},
                    gauge = {
                        'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
                        'bar': {'color': "#0086ff"},
                        'bgcolor': "rgba(0,0,0,0)",
                        'borderwidth': 2,
                        'bordercolor': "rgba(255,255,255,0.1)",
                        'steps': [
                            {'range': [0, 50], 'color': 'rgba(239, 68, 68, 0.1)'},
                            {'range': [50, 80], 'color': 'rgba(245, 158, 11, 0.1)'},
                            {'range': [80, 100], 'color': 'rgba(16, 185, 129, 0.1)'}
                        ],
                        'threshold': {
                            'line': {'color': "white", 'width': 3},
                            'thickness': 0.75,
                            'value': taxa_aprovacao
                        }
                    }
                ))
                fig_gauge.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=280,
                    margin=dict(l=30, r=30, t=50, b=20)
                )
                st.plotly_chart(fig_gauge, use_container_width=True)

            with col_chart_kb:
                st.markdown("#### 🧠 Saúde da Base de Conhecimento")
                # Distinguimos o que é Calibragem (tem rascunho IA) do que é Ouro puro (Manual)
                num_calib = len(df_fb) if not df_fb.empty else 0
                num_ouro_puro = total_ouro - num_calib
                
                kb_data = {
                    "Componente": ["Fonética", "Estrutura", "Calibragem", "Roteiro Ouro", "Persona", "Nuances"],
                    "Registros": [len(df_fon), len(df_est), num_calib, num_ouro_puro, len(df_pers), len(df_nuan)]
                }
                df_kb = pd.DataFrame(kb_data)
                fig_kb = px.bar(df_kb, x='Registros', y='Componente', orientation='h', 
                               color='Registros', color_continuous_scale='Blues')
                fig_kb.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    height=300,
                    margin=dict(l=20, r=20, t=30, b=20),
                    xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
                    yaxis=dict(showgrid=False)
                )
                st.plotly_chart(fig_kb, use_container_width=True)
            
            st.divider()

            # === SEÇÃO 3: PRODUÇÃO E ANÁLISE ===
            col_prod, col_modo, col_aval = st.columns(3)
            
            with col_prod:
                st.markdown("#### 📈 Evolução de Produção")
                if not df_hist_dash.empty and 'criado_em' in df_hist_dash.columns:
                    df_timeline = df_hist_dash.copy()
                    df_timeline['data'] = pd.to_datetime(df_timeline['criado_em']).dt.date
                    chart_data = df_timeline.groupby('data').size().reset_index(name='Quantidade')
                    
                    fig_prod = px.line(chart_data, x='data', y='Quantidade', 
                                     render_mode='svg', markers=True)
                    fig_prod.update_traces(line_color='#0086ff', line_width=4, 
                                         marker=dict(size=10, line=dict(width=2, color='white')))
                    fig_prod.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        height=350,
                        margin=dict(l=20, r=20, t=30, b=20),
                        xaxis=dict(showgrid=False, title=None),
                        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', title=None)
                    )
                    st.plotly_chart(fig_prod, use_container_width=True)
                else:
                    st.info("Sem dados de produção ainda.")
            
            with col_modo:
                st.markdown("#### 🎯 Mix de Modos de Trabalho")
                if not df_hist_dash.empty and 'modo_trabalho' in df_hist_dash.columns:
                    modo_counts = df_hist_dash['modo_trabalho'].value_counts().reset_index()
                    modo_counts.columns = ['Modo', 'Quantidade']
                    fig_modo = px.pie(modo_counts, values='Quantidade', names='Modo', hole=0.5,
                                    color_discrete_sequence=px.colors.qualitative.Bold)
                    fig_modo.update_traces(textposition='inside', textinfo='percent+label')
                    fig_modo.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        height=350,
                        margin=dict(l=20, r=20, t=30, b=20),
                        showlegend=False
                    )
                    st.plotly_chart(fig_modo, use_container_width=True)
                else:
                    st.info("Sem dados de modos.")
            
            with col_aval:
                st.markdown("#### ⚖️ Sentimento das Calibrações")
                if not df_fb.empty and 'avaliacao_label' in df_fb.columns:
                    aval_counts = df_fb['avaliacao_label'].value_counts().reset_index()
                    aval_counts.columns = ['Avaliação', 'Quantidade']
                    
                    # Cores específicas para as novas métricas
                    color_map = {
                        "Ajuste Fino": "#10b981",       # Verde
                        "Edição Moderada": "#34d399",   # Esmeralda
                        "Mudança Estrutural": "#f59e0b", # Âmbar
                        "Reescrita Pesada": "#ef4444"    # Vermelho
                    }
                    
                    fig_aval = px.bar(aval_counts, x='Avaliação', y='Quantidade', color='Avaliação',
                                    color_discrete_map=color_map, category_orders={"Avaliação": ["Ajuste Fino", "Edição Moderada", "Mudança Estrutural", "Reescrita Pesada"]})
                    fig_aval.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        showlegend=False,
                        margin=dict(l=20, r=20, t=30, b=20)
                    )
                    st.plotly_chart(fig_aval, use_container_width=True)
                else:
                    st.info("Sem avaliações registradas.")

            st.divider()

            # === SEÇÃO 4: ANÁLISE DE CUSTOS POR MODELO ===
            st.markdown("#### 💰 Investimento por Modelo (BRL)")
            if not df_hist_dash.empty and 'modelo_llm' in df_hist_dash.columns and 'custo_estimado_brl' in df_hist_dash.columns:
                df_cost = df_hist_dash.groupby('modelo_llm')['custo_estimado_brl'].sum().reset_index()
                df_cost.columns = ['Modelo', 'Custo Total (R$)']
                
                fig_cost = px.pie(df_cost, values='Custo Total (R$)', names='Modelo', hole=0.6,
                                color_discrete_sequence=px.colors.sequential.Bluyl)
                fig_cost.update_traces(textinfo='percent+label')
                fig_cost.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=20, r=20, t=30, b=20),
                    showlegend=False
                )
                
                col_c1, col_c2 = st.columns([2, 1])
                with col_c1:
                    st.plotly_chart(fig_cost, use_container_width=True)
                with col_c2:
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    for _, row in df_cost.iterrows():
                        st.write(f"**{row['Modelo']}:** R$ {row['Custo Total (R$)']:.4f}")
            else:
                st.info("Sem dados de custo para analisar.")
            
            st.divider()
            
            # === SEÇÃO 4: TABELAS DETALHADAS ===
            st.markdown("### 📋 Dados Detalhados")
            tab_hist, tab_ouro, tab_feed, tab_nuan, tab_pers, tab_fon = st.tabs(["💵 Histórico In-Depth", "🏆 Roteiros Ouro", "⚖️ Feedbacks", "🧠 Nuances", "💃 Persona", "🗣️ Fonética"])
            
            with tab_hist:
                if not df_hist_dash.empty:
                    df_show_hist = df_hist_dash.copy()
                    
                    # Formatação de colunas
                    if 'custo_estimado_brl' in df_show_hist.columns:
                        df_show_hist['Custo Brl'] = df_show_hist['custo_estimado_brl'].apply(
                            lambda x: f"R$ {x:,.4f}".replace(',', 'X').replace('.', ',').replace('X', '.') if pd.notna(x) and x > 0 else "-"
                        )
                    
                    # Renomeando colunas para o usuário
                    cols_to_show = {'criado_em': 'Data Geração', 'codigo_produto': 'Cód. Produto', 
                                   'modo_trabalho': 'Modo', 'modelo_llm': 'Modelo', 'Custo Brl': 'Custo (R$)'}
                    
                    df_show_hist = df_show_hist.rename(columns=cols_to_show)
                    
                    # Ordenar e filtrar apenas as colunas mapeadas
                    col_order = [cols_to_show[k] for k in cols_to_show if cols_to_show[k] in df_show_hist.columns]
                    st.dataframe(df_show_hist[col_order].sort_values(by='Data Geração', ascending=False), use_container_width=True)
                else:
                    st.info("Nenhum histórico de produção registrado.")
            
            with tab_nuan:
                if not df_nuan.empty:
                    st.dataframe(df_nuan[['criado_em', 'frase_ia', 'analise_critica', 'exemplo_ouro']].sort_values(by='criado_em', ascending=False), use_container_width=True)
                else:
                    st.info("Nenhuma nuance de linguagem cadastrada.")
            
            with tab_ouro:
                if not df_ouro.empty:
                    st.dataframe(df_ouro[['criado_em', 'categoria', 'titulo_produto', 'roteiro_perfeito']].sort_values(by='criado_em', ascending=False), use_container_width=True)
                else:
                    st.info("Nenhum Roteiro Ouro cadastrado.")
            
            with tab_feed:
                if not df_fb.empty:
                    # Colunas do novo sistema de calibragem
                    available_cols = [c for c in ['criado_em', 'estrela', 'categoria', 'modelo_calibragem', 'aprendizado', 'roteiro_original_ia', 'roteiro_perfeito'] if c in df_fb.columns]
                    st.dataframe(df_fb[available_cols].sort_values(by='criado_em', ascending=False), use_container_width=True)
                else:
                    st.info("Nenhuma calibração realizada ainda.")
            
            with tab_pers:
                if not df_pers.empty:
                    st.dataframe(df_pers[['criado_em', 'pilar_persona', 'erro_cometido', 'texto_corrigido_humano', 'lexico_sugerido']].sort_values(by='criado_em', ascending=False), use_container_width=True)
                else:
                    st.info("Nenhum ajuste de persona cadastrado.")
                    
            with tab_fon:
                if not df_fon.empty:
                    st.dataframe(df_fon[['criado_em', 'termo_errado', 'termo_corrigido', 'exemplo_no_roteiro']].sort_values(by='criado_em', ascending=False), use_container_width=True)
                else:
                    st.info("Nenhuma regra de fonética cadastrada.")
                
        except Exception as e:
            st.error(f"Erro ao carregar os dados do dashboard: {e}")

# --- PÁGINA 7: ASSISTENTE LU (INTERACTIVE CHAT) ---
elif page == "Assistente Lu":
    st.subheader("💬 Assistente Lu")
    st.caption("Converse com a Lu sobre os roteiros gerados, métricas da equipe ou dúvidas gerais.")
    
    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "Lu", "content": "Oi! Sou a Lu, sua assistente focada em IA para Magalu. Como posso te ajudar hoje?"}
        ]

    # Display chat messages from history on app rerun
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("Pergunte sobre os roteiros (ex: 'quantos foram gerados hoje?')..."):
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        # Generate response using the active RoteiristaAgent
        with st.chat_message("Lu"):
            message_placeholder = st.empty()
            
            # Re-instantiate agent to ensure it uses the current model_id
            modelo_id = st.session_state.get('modelo_llm', 'gemini-2.5-flash')
            
            try:
                # Compile Supabase context for RAG
                context_str = ""
                sp = st.session_state.get('supabase_client')
                if sp:
                    try:
                            # Buscamos as estatísticas rápidas
                            now_sp_chat = get_now_sp()
                            hoje = now_sp_chat.date().isoformat()
                            # Consulta os ultimos roteiros da semana
                            d_recent = sp.table("nw_historico_roteiros").select("criado_em, codigo_produto, custo_estimado_brl, modelo_llm").order('criado_em', desc=True).limit(200).execute()
                            if d_recent.data:
                                df = pd.DataFrame(d_recent.data)
                                df['data'] = pd.to_datetime(df['criado_em']).dt.tz_convert('America/Sao_Paulo').dt.date
                                total_geral = len(df)
                                total_hoje = len(df[df['data'] == now_sp_chat.date()])
                                custo_total = df['custo_estimado_brl'].sum()
                                context_str = f"Métricas do Banco de Dados:\n- Total Recente Analisado: {total_geral}\n- Gerados Hoje ({hoje}): {total_hoje}\n- Custo Recente Total: R$ {custo_total:.4f}\n"
                    except Exception as e:
                        context_str = f"Aviso: Não consegui ler o banco de dados completamente ({e})."
                else:
                    context_str = "Aviso: Banco de dados Supabase não conectado nesta sessão."

                agent = RoteiristaAgent(
                    supabase_client=sp,
                    model_id=modelo_id
                )
                
                # Fetch response with delay for loading perception
                with st.spinner("Lu está digitando..."):
                    resposta_lu = agent.chat_with_context(prompt, st.session_state.chat_history, context_str)
                
                message_placeholder.markdown(resposta_lu)
                # Add assistant response to chat history
                st.session_state.chat_history.append({"role": "Lu", "content": resposta_lu})
                
            except Exception as e:
                st.error(f"Erro de comunicação com a IA: {e}")
