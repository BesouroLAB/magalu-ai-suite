import streamlit as st
import os
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pytz
import uuid
from dotenv import load_dotenv
from supabase import create_client, Client
import difflib

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
        res = sp_client.table(f"{st.session_state.get('table_prefix', 'nw_')}historico_roteiros").select("id", count="exact").limit(1).execute()
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
    .stApp { background-color: var(--bg-main) !important; color: var(--text-primary); }

    h1 { font-size: 2.4rem !important; font-weight: 800 !important; color: #ffffff !important; letter-spacing: -0.5px; margin-bottom: 0.8rem !important; }
    h2 { font-size: 1.8rem !important; font-weight: 700 !important; color: #e0e6f0 !important; margin-bottom: 0.6rem !important; }
    h3 { font-size: 1.15rem !important; font-weight: 600 !important; color: #b0bdd0 !important; margin-bottom: 0.3rem !important; }
    h4 { font-size: 1.0rem !important; font-weight: 500 !important; color: var(--mglu-blue) !important; margin-bottom: 0.2rem !important; }
    
    p, span, label, li { color: var(--text-primary); font-family: 'Inter', sans-serif; font-size: 0.92rem; }
    .stMarkdown p, .stMarkdown span, .stMarkdown li { color: var(--text-muted); font-size: 0.9rem; }
    .stText { color: var(--text-muted); font-size: 0.9rem; }

    /* Estilização de boxes de alerta do Streamlit para modo escuro */
    div[data-testid="stNotification"] {
        background-color: #050e1d !important;
        border: 1px solid rgba(0, 134, 255, 0.2) !important;
        color: #f0f0f0 !important;
    }
    div[data-testid="stNotification"] p { color: #f0f0f0 !important; }
    div[data-testid="stNotification"] svg { fill: #0086ff !important; }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] { background-color: transparent !important; }
    .stTabs [data-baseweb="tab"] { color: var(--text-muted) !important; font-weight: 600 !important; }
    .stTabs [aria-selected="true"] { color: var(--mglu-blue) !important; border-bottom-color: var(--mglu-blue) !important; }

    /* Popover styling */
    div[data-testid="stPopoverContent"] {
        background-color: #050e1d !important;
        border: 1px solid #0a1b33 !important;
        color: #f0f0f0 !important;
    }

    /* Metric styling */
    div[data-testid="stMetricValue"] { color: white !important; font-weight: 700 !important; }
    div[data-testid="stMetricLabel"] { color: var(--text-muted) !important; text-transform: uppercase; letter-spacing: 1px; font-size: 0.75rem !important; }

    /* Scrollbars customizadas */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: #020710; }
    ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: #0086ff; }
    
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

# --- INICIALIZAÇÃO DE ESTADO ---
if 'batch_queue' not in st.session_state:
    st.session_state['batch_queue'] = []
if 'roteiros' not in st.session_state:
    st.session_state['roteiros'] = []

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
        return dt_sp.strftime('%d/%m/%y às %H:%M')
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
        res = sp_client.table(f"{st.session_state.get('table_prefix', 'nw_')}roteiros_ouro").insert(data).execute()
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
            "roteiro_perfeito": roteiro_perfeito,
            "criado_em": get_now_sp().isoformat()
        }
        res = sp_client.table(f"{st.session_state.get('table_prefix', 'nw_')}roteiros_ouro").insert(data).execute()
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
            "texto_gerado_ia": erro,
            "texto_corrigido_humano": texto_humano,
            "lexico_sugerido": lexico,
            "criado_em": get_now_sp().isoformat()
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
            "exemplo_no_roteiro": exemplo_rot,
            "criado_em": get_now_sp().isoformat()
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
            if not existing.data:
                sp_client.table("nw_treinamento_fonetica").insert({
                    "termo_errado": termo_err,
                    "termo_corrigido": termo_cor,
                    "exemplo_no_roteiro": exemplo,
                    "criado_em": get_now_sp().isoformat()
                }).execute()
                count += 1
        except Exception as e:
            st.error(f"Erro ao salvar fonética: {e}")
    
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
        # Tenta pegar prioritariamente 'texto_ia' (novo padrão) ou 'antes' (fallback)
        raw_ia = regra.get('texto_ia', regra.get('antes', ''))
        texto_ia_rej = str(raw_ia).strip() if raw_ia and str(raw_ia).lower() != 'none' else ""
        
        # Normalização para o padrão do banco
        if "Abertura" in tipo: tipo = "Abertura (Gancho)"
        elif "Fechamento" in tipo or "CTA" in tipo: tipo = "Fechamento (CTA)"
        else: tipo = "Desenvolvimento (Venda)"
        
        if not texto_ouro or tipo not in ('Abertura (Gancho)', 'Fechamento (CTA)', 'Desenvolvimento (Venda)'):
            continue
        
        try:
            sp_client.table(f"{st.session_state.get('table_prefix', 'nw_')}treinamento_estruturas").insert({
                "tipo_estrutura": tipo,
                "texto_ouro": texto_ouro,
                "texto_ia_rejeitado": texto_ia_rej,
                "aprendizado": str(regra.get('motivo', '')).strip(),
                "criado_em": get_now_sp().isoformat()
            }).execute()
            count += 1
        except Exception as e:
            st.error(f"Erro ao salvar estrutura: {e}")
    
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
                "criado_em": get_now_sp().isoformat()
            }).execute()
            count += 1
        except Exception as e:
            st.error(f"Erro ao salvar persona: {e}")
    
    if count > 0:
        st.toast(f"💃 {count} regra(s) de persona da Lu aprendida(s)!", icon="🎭")
    return count

def _auto_salvar_imagens(sp_client, imagens_regras, codigo_p=""):
    """Salva calibragem de descrições de imagem automaticamente."""
    if not sp_client or not imagens_regras:
        return 0
    
    count = 0
    for regra in imagens_regras:
        if not isinstance(regra, dict):
            continue
        raw_antes = regra.get('antes', '')
        raw_depois = regra.get('depois', '')
        antes = str(raw_antes).strip() if raw_antes and str(raw_antes).lower() != 'none' else ""
        depois = str(raw_depois).strip() if raw_depois and str(raw_depois).lower() != 'none' else ""
        motivo = str(regra.get('motivo', '')).strip()
        
        if not antes or not depois:
            continue
            
        try:
            prefix = st.session_state.get('table_prefix', 'nw_')
            sp_client.table(f"{prefix}treinamento_imagens").insert({
                "codigo_produto": codigo_p,
                "descricao_ia": antes,
                "descricao_humano": depois,
                "aprendizado": motivo,
                "criado_em": get_now_sp().isoformat()
            }).execute()
            count += 1
        except Exception as e:
            st.error(f"Erro ao salvar lição visual: {e}")
            
    if count > 0:
        st.toast(f"📸 {count} lição(ões) visual(ais) aprendida(s)!", icon="🖼️")
    return count

def salvar_imagem(sp_client, sku, ia_desc, hum_desc, motivo):
    if not sp_client:
        st.error("Supabase não conectado.")
        return False
    try:
        data = {
            "codigo_produto": sku,
            "descricao_ia": ia_desc,
            "descricao_humano": hum_desc,
            "aprendizado": motivo,
            "criado_em": get_now_sp().isoformat()
        }
        prefix = st.session_state.get('table_prefix', 'nw_')
        res = sp_client.table(f"{prefix}treinamento_imagens").insert(data).execute()
        if hasattr(res, 'data') and len(res.data) > 0:
            st.success("🖼️ Calibragem visual salva com sucesso!")
            return True
        else:
            st.error("⚠️ Falha ao salvar no Supabase (verifique RLS).")
            return False
    except Exception as e:
        st.error(f"❌ Erro: {e}")
        return False


def salvar_estrutura(sp_client, tipo, texto, texto_ia=""):
    if not sp_client:
        st.error("Supabase não conectado.")
        return False
    try:
        data = {
            "tipo_estrutura": tipo,
            "texto_ouro": texto,
            "texto_ia_rejeitado": texto_ia,
            "aprendizado": "", # Manual não tem motivo automático, mas campo existe
            "criado_em": get_now_sp().isoformat()
        }
        res = sp_client.table(f"{st.session_state.get('table_prefix', 'nw_')}treinamento_estruturas").insert(data).execute()
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
            "exemplo_ouro": exemplo,
            "criado_em": get_now_sp().isoformat()
        }
        res = sp_client.table(f"{st.session_state.get('table_prefix', 'nw_')}treinamento_nuances").insert(data).execute()
        if hasattr(res, 'data') and len(res.data) > 0:
            st.success("🧠 Nuance de linguagem registrada para o treinamento!")
            return True
        else:
            st.error("⚠️ Falha ao salvar no Supabase (verifique RLS).")
            return False
    except Exception as e:
        st.error(f"❌ Erro: {e}")
        return False



def render_visual_diff(original, final):
    # Normalização básica para evitar diffs de "espaço em branco" ou quebras de linha diferentes
    text_ia = [l.strip() for l in original.splitlines()]
    text_hum = [l.strip() for l in final.splitlines()]

    html_diff = difflib.HtmlDiff().make_table(
        text_ia,
        text_hum,
        fromdesc="🤖 IA ORIGINAL",
        todesc="✍️ SUA EDIÇÃO",
        context=True,
        numlines=2
    )
    
    # CSS Refinado para Modal Centrado e Escuro
    diff_css = """
    <style>
        .diff_container { width: 100%; display: flex; justify-content: center; }
        table.diff {
            font-family: 'Inter', sans-serif; 
            border: none; 
            background: #020710; 
            width: 100%; 
            border-radius: 12px; 
            overflow: hidden; 
            font-size: 11px;
            border-collapse: collapse;
        }
        .diff_header { background-color: #1e293b; color: #94a3b8; font-weight: bold; padding: 10px; text-transform: uppercase; text-align: center; }
        .diff_add { background-color: #064e3b; color: #34d399; font-weight: bold; }
        .diff_chg { background-color: #1e293b; color: #fbbf24; font-weight: bold; }
        .diff_sub { background-color: #7f1d1d; color: #f87171; font-weight: bold; text-decoration: line-through; }
        td { padding: 6px 12px !important; border: 1px solid #1e293b !important; vertical-align: top; }
        .diff_next { display: none; }
    </style>
    """
    st.markdown(diff_css + f"<div class='diff_container'>{html_diff}</div>", unsafe_allow_html=True)

@st.dialog("📚 Documentação da IA", width="large")
def modal_doc_viewer(file_path):
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            st.markdown(content)
        else:
            st.error(f"Arquivo não encontrado: {file_path}")
    except Exception as e:
        st.error(f"Erro ao ler documentação: {e}")
    
    if st.button("Fechar", use_container_width=True):
        del st.session_state['show_doc_modal']
        st.rerun()

@st.dialog("🧠 Resultado da Calibragem")
def modal_resultado_calibragem(calc, sp_cli, roteiro_ia, roteiro_humano, titulo_curto="", codigo_p=""):
    # Salva no estado para recuperação em caso de fechar acidentalmente
    st.session_state['pending_calibration'] = {
        'calc': calc, 'roteiro_ia': roteiro_ia, 'roteiro_humano': roteiro_humano,
        'titulo_curto': titulo_curto, 'codigo_p': codigo_p
    }
    
    if 'show_diff' not in st.session_state:
        st.session_state['show_diff'] = False

    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.markdown(f"### Aproveitamento Total: **{calc['percentual']}%**")
    with col_t2:
        if st.button("🔍 Ver Diff", use_container_width=True):
            st.session_state['show_diff'] = not st.session_state['show_diff']
            st.rerun()
            
    if st.session_state.get('show_diff', False):
        st.markdown("#### 🔍 Comparação Visual de Alterações")
        render_visual_diff(roteiro_ia, roteiro_humano)
        st.divider()
    
    # 0. Resumo Estratégico (Meta-Análise)
    resumo = calc.get('resumo_estrategico', '')
    if resumo:
        st.markdown(f"""
        <div style='background-color: #1E2530; padding: 15px; border-radius: 8px; border-left: 5px solid #6366f1; margin-bottom: 20px;'>
            <div style='font-size: 0.8rem; color: #8b92a5; font-weight: 600; text-transform: uppercase; margin-bottom: 5px;'>🎯 Direção Criativa (Meta-Análise)</div>
            <div style='font-size: 1rem; color: #c9d1e0; line-height: 1.5;'>"{resumo}"</div>
        </div>
        """, unsafe_allow_html=True)

    # 1. Feedback / Aprendizado
    with st.expander("📝 Lições Técnicas de Redação (Roteiros Ouro)", expanded=True):
        st.write(calc['aprendizado'])

    st.markdown("#### 🗃️ Detalhamento por Tabela")

    # 2. Persona
    p_regras = calc.get('persona_regras', [])
    if p_regras:
        for r in p_regras:
            st.info(f"💃 **Tabela: `nw_treinamento_persona_lu`**\n- **pilar_persona**: {r.get('pilar')}\n- **texto_gerado_ia**: {r.get('erro')}\n- **texto_corrigido_humano**: {r.get('correcao')}\n- **lexico_sugerido**: {r.get('lexico')}")
    else:
        st.info("💃 **Persona:** Não houve mudanças. Nenhuma regra de tom/vocabulário adicionada.")

    # 3. Estrutura
    e_regras = calc.get('estrutura_regras', [])
    if e_regras:
        for r in e_regras:
            raw_ia_modal = r.get('texto_ia', r.get('antes'))
            txt_ia_modal = str(raw_ia_modal).strip() if raw_ia_modal and str(raw_ia_modal).lower() != 'none' else "..."
            st.success(f"🏗️ **Tabela: `{st.session_state.get('table_prefix', 'nw_')}treinamento_estruturas`**\n\n- **tipo_estrutura**: {r.get('tipo', 'Abertura/CTA')}\n- **texto_ia_rejeitado**: {txt_ia_modal}\n- **texto_ouro**: {r.get('texto_ouro')}")
    else:
        st.success("🏗️ **Estruturas:** Não houve mudanças em Ganchos ou CTAs.")

    # 4. Fonética
    f_regras = calc.get('fonetica_regras', [])
    if f_regras:
        for r in f_regras:
            st.warning(f"🗣️ **Tabela: `nw_treinamento_fonetica`**\n- **termo_errado**: {r.get('termo_errado')}\n- **termo_corrigido**: {r.get('termo_corrigido')}\n- **exemplo_no_roteiro**: {r.get('exemplo', '')}")
    else:
        st.warning("🗣️ **Fonética:** Não houve mudanças ou novas pronúncias.")

    # 5. Imagens
    i_regras = calc.get('imagens_regras', [])
    if i_regras:
        for r in i_regras:
            st.markdown(f"""
            <div style='background-color: #2e1065; padding: 15px; border-radius: 8px; border-left: 5px solid #8b5cf6; margin-bottom: 10px; color: #c4b5fd;'>
                📸 <b>Tabela: <code>{st.session_state.get('table_prefix', 'nw_')}treinamento_imagens</code></b><br/><br/>
                <b><code>descricao_ia</code>:</b> {str(r.get('antes')) if r.get('antes') and str(r.get('antes')).lower() != 'none' else '...'}<br/>
                <b><code>descricao_humano</code>:</b> {str(r.get('depois')) if r.get('depois') and str(r.get('depois')).lower() != 'none' else '...'}<br/>
                <b><code>aprendizado</code>:</b> {r.get('motivo')}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style='background-color: #2e1065; padding: 15px; border-radius: 8px; border-left: 5px solid #8b5cf6; margin-bottom: 10px; color: #c4b5fd;'>
            📸 <b>Imagens:</b> Não houve mudanças nas descrições visuais.
        </div>
        """, unsafe_allow_html=True)

    # Categoria automática baseada no aprendizado
    final_cat_id_modal = calc.get('categoria_id', 77)


    st.divider()
    st.caption("Ao confirmar, a IA alimentará simultaneamente as tabelas acima.")
    
    if st.button("🚀 Confirmar e Gravar Todas as Lições", type="primary", use_container_width=True):
        # Salva Feedback Ouro (Aba Feedback)
        cat_id = final_cat_id_modal
        if not cat_id:
             # Fallback categoria ID
             try:
                 # Categoria é sempre nw_categorias independente do prefixo do formato
                 res_c = sp_cli.table("nw_categorias").select("id, nome").execute()
                 lista_c = res_c.data if hasattr(res_c, 'data') else []
                 cat_id = next((c['id'] for c in lista_c if 'Genérico' in c['nome']), 77)
             except Exception as e_cat:
                 print(f"Erro ao buscar categorias: {e_cat}")
                 cat_id = 77
                 
        # Concatena resumo estratégico com diretrizes técnicas
        aprendizado_final = calc['aprendizado']
        if calc.get('resumo_estrategico'):
            aprendizado_final = f"🎯 DIREÇÃO CRIATIVA: {calc['resumo_estrategico']}\n\n📝 DIRETRIZES TÉCNICAS:\n{calc['aprendizado']}"

        salvar_calibracao_ouro(sp_cli, cat_id, roteiro_ia, roteiro_humano, calc['percentual'], aprendizado_final, codigo_p, titulo_curto, calc.get('modelo_calibragem', 'N/A'))
        
        # Salva as outras tabelas (Persona, Fonética, Estrutura, Imagens)
        _auto_salvar_fonetica(sp_cli, f_regras)
        _auto_salvar_estrutura(sp_cli, e_regras)
        _auto_salvar_persona(sp_cli, p_regras)
        _auto_salvar_imagens(sp_cli, i_regras, codigo_p)
        
        st.session_state['calibragem_concluida'] = True
        if 'pending_calibration' in st.session_state:
            del st.session_state['pending_calibration']
        st.rerun()

with st.sidebar:
    # --- Verificação de Status (antes de renderizar) ---
    api_key_env = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    if api_key_env:
        os.environ["GEMINI_API_KEY"] = api_key_env
        os.environ["GOOGLE_API_KEY"] = api_key_env
    
    puter_key_env = os.environ.get("PUTER_API_KEY") or st.secrets.get("PUTER_API_KEY")
    if puter_key_env: os.environ["PUTER_API_KEY"] = puter_key_env
    
    openai_key_env = os.environ.get("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
    if openai_key_env: os.environ["OPENAI_API_KEY"] = openai_key_env
    
    openrouter_key_env = os.environ.get("OPENROUTER_API_KEY") or st.secrets.get("OPENROUTER_API_KEY")
    if openrouter_key_env: os.environ["OPENROUTER_API_KEY"] = openrouter_key_env
    
    zai_key_env = os.environ.get("ZAI_API_KEY") or st.secrets.get("ZAI_API_KEY")
    if zai_key_env: os.environ["ZAI_API_KEY"] = zai_key_env
    
    kimi_key_env = os.environ.get("KIMI_API_KEY") or st.secrets.get("KIMI_API_KEY")
    if kimi_key_env: os.environ["KIMI_API_KEY"] = kimi_key_env
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
        <div style='font-size: 13px; color: #8b92a5; margin-bottom: 25px; margin-top: 5px; display: flex; align-items: center; gap: 8px;'>
            <span style='font-weight: 400; letter-spacing: 0.5px;'>V2.8</span>
            <span style='color: #2A3241;'>|</span>
            <div style='display: flex; align-items: center; gap: 4px;'>
                <span style='color: {sc_llm}; font-weight: 400; font-size: 14px;'>{_llm_name}</span>
                <span style='background: {sb_llm}; color: {sc_llm}; padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: 700; border: 1px solid {sc_llm}66;'>{sl_llm}</span>
            </div>
            <div style='display: flex; align-items: center; gap: 4px;'>
                <span style='color: {sc_sup}; font-weight: 400; font-size: 14px;'>Supabase</span>
                <span style='background: {sb_sup}; color: {sc_sup}; padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: 700; border: 1px solid {sc_sup}66;'>{sl_sup}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # --- SELETOR DE AMBIENTE (NW x NW 3D) ---
    st.markdown("<div style='margin-bottom: 5px; font-weight: 600; font-size: 14px; color: #b0bdd0;'>📁 Ambiente (Tabelas):</div>", unsafe_allow_html=True)
    active_env = st.radio(
        "Ambiente de Trabalho",
        ["NW Padrão", "NW 3D", "Discovery (SOCIAL)"],
        horizontal=True,
        label_visibility="collapsed",
        key="active_mode_radio"
    )
    
    # Salva no session state para refazer queries de banco dinâmicas
    st.session_state['active_mode'] = active_env
    if active_env == "NW Padrão":
        st.session_state['table_prefix'] = "nw_"
    elif active_env == "NW 3D":
        st.session_state['table_prefix'] = "nw3d_"
    else:
        st.session_state['table_prefix'] = "social_"

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
                _temp_agent = RoteiristaAgent(model_id=modelo_id_selecionado, table_prefix=st.session_state.get('table_prefix', 'nw_'))
                st.session_state['modelo_llm'] = modelo_id_selecionado
                st.session_state['last_model'] = modelo_id_selecionado
                st.toast(f"Módulo {modelo_label.split(' — ')[0]} carregado e pronto!", icon="🧠")
                time.sleep(1.0) # Espera o toast ser lido antes do rebuild
            except Exception as e:
                # Se falhar (ex: chave faltando), voltamos para o Gemini mas marcamos que JÁ TENTAMOS esse modelo
                st.session_state['modelo_llm'] = "gemini-3-flash-preview"
                st.session_state['last_model'] = modelo_id_selecionado # Importante: marca como tentado para parar o loop
                st.error(f"❌ Falha ao carregar {modelo_label}: {str(e)}")
                time.sleep(3.0)
        st.rerun()

    # Info rápida sobre o modelo
    _desc = MODELOS_DESCRICAO.get(modelo_id_selecionado, "")
    if _desc:
        st.markdown(f"""
            <div style='background: rgba(0, 134, 255, 0.05); padding: 10px 14px; border-radius: 6px; border-left: 4px solid #0086ff; margin-bottom: 15px;'>
                <p style='font-size: 13.5px; color: #f0f0f0; margin: 0; line-height: 1.4; opacity: 0.9;'>{_desc}</p>
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

    # --- LINK DE DOCUMENTAÇÃO (Como Funciona) ---
    # Custom CSS para o botão de documentação ser azul mais claro (estilo link)
    st.markdown("""
    <style>
        /* Target the specific Documentation button by position or state */
        div[data-testid="stSidebar"] div.stButton:nth-last-child(2) button {
            background-color: transparent !important;
            color: #339dff !important;
            border: 1px solid rgba(51, 157, 255, 0.2) !important;
            font-size: 0.85rem !important;
            margin-top: 10px !important;
        }
        div[data-testid="stSidebar"] div.stButton:nth-last-child(2) button:hover {
            background-color: rgba(51, 157, 255, 0.1) !important;
            border-color: #339dff !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- LINK DE DOCUMENTAÇÃO (Como Funciona) ---
    is_doc_active = st.session_state['page'] == "Como Funciona"
    if st.button("📖 Como Funciona (Básico)", use_container_width=True, key="btn_doc"):
        st.session_state['page'] = "Como Funciona"
        st.rerun()

    # Botoes de Documentação Adicional (Novos)
    st.markdown("<div style='margin-bottom: 5px; font-weight: 600; font-size: 11px; color: #6366f1; opacity: 0.8; margin-top: 10px;'>📚 MANUAIS DA IA:</div>", unsafe_allow_html=True)
    col_doc1, col_doc2 = st.columns(2)
    with col_doc1:
        if st.button("📓 Guia Redator", use_container_width=True, key="doc_redator"):
            st.session_state['show_doc_modal'] = "docs/calibragem_redatores_v3.0.md"
    with col_doc2:
        if st.button("🛠️ Manual Técnico", use_container_width=True, key="doc_tecnico"):
            st.session_state['show_doc_modal'] = "docs/calibragem_tecnica_v3.0.md"

    st.markdown("""
        <div style='margin-top: 50px; padding: 15px 5px; border-top: 1px solid rgba(255,255,255,0.03); text-align: center;'>
            <p style='font-size: 9px; color: #4a5568; margin: 0; opacity: 0.7; font-weight: 300;'>Desenvolvido por <a href='https://besourolab.com.br' target='_blank' style='color: #4a5568; text-decoration: underline; opacity: 0.8;'>Tiago Fernandes | BesouroLAB</a></p>
            <p style='font-size: 8px; color: #2d3748; margin-top: 4px; letter-spacing: 0.5px; opacity: 0.5;'>TODOS OS DIREITOS RESERVADOS © 2026</p>
        </div>
    """, unsafe_allow_html=True)

    page = st.session_state['page']
    
    # --- RECUPERAÇÃO DE CALIBRAGEM ACCIDENTALMENTE FECHADA ---
    if st.session_state.get('pending_calibration'):
        pc = st.session_state['pending_calibration']
        with st.container(border=True):
            st.markdown(f"⚠️ **Calibragem de {pc['codigo_p']} ainda não confirmada!**")
            col_rec1, col_rec2 = st.columns(2)
            if col_rec1.button("🧠 Abrir Resultado Novamente", type="primary", use_container_width=True):
                st.session_state['show_diff'] = False
                modal_resultado_calibragem(pc['calc'], st.session_state.get('supabase_client'), pc['roteiro_ia'], pc['roteiro_humano'], pc['titulo_curto'], pc['codigo_p'])
            if col_rec2.button("🗑️ Descartar", type="secondary", use_container_width=True):
                del st.session_state['pending_calibration']
                st.rerun()

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

# --- MODAIS GLOBAIS ---
if 'show_calib_modal' in st.session_state:
    show_calibragem_summary()

if 'show_doc_modal' in st.session_state:
    modal_doc_viewer(st.session_state['show_doc_modal'])


    # --- PÁGINA 1: CRIAR ROTEIROS ---
if page == "Criar Roteiros":
    
    # --- EXIBIÇÃO DE ERROS PERSISTENTES ---
    if st.session_state.get('last_errors'):
        with st.expander("🚨 Detalhes de Erros Recentemente Ocorridos", expanded=True):
            for err in st.session_state['last_errors']:
                st.error(err)
            if st.button("Clear Errors"):
                del st.session_state['last_errors']
                st.rerun()

    # --- COMMAND CENTER (INPUTS) ---
    # Colapsa automaticamente após geração, mas o usuário sempre pode reabrir
    _has_roteiros = 'roteiros' in st.session_state and st.session_state['roteiros']
    expander_input = st.expander("✍️ Inserir Códigos e Gerar", expanded=not _has_roteiros)
    
    with expander_input:
        cat_selecionada_id = 77
        # Categoria removida da UI para ser automática (ID 77 - Genérico)


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
                "📱 SOCIAL (Reels)": "Hook viral + Captura mobile (Descobrimento)",
                "🎮 3D (NewWeb 3D)": "Cenas em 3D autorais Magalu (Contínuo)",
                "🎙️ Review": "Em breve: Prós e contras pro apresentador"
            }
            
            try:
                # Tenta usar st.pills (Streamlit 1.30+)
                modo_pill = st.pills(
                    "Selecione o Formato:",
                    list(modos_trabalho.keys()),
                    index=0,
                    key="modo_pill",
                    label_visibility="collapsed"
                )
                modo_selecionado = modos_trabalho[modo_pill]
                st.caption(f"💡 {modos_descricao[modo_pill]}")
            except (AttributeError, Exception):
                # Fallback para st.selectbox se st.pills não existir ou falhar
                modo_pill = st.selectbox(
                    "Selecione o Formato:",
                    list(modos_trabalho.keys()),
                    index=0,
                    key="modo_selecao_fallback"
                )
                modo_selecionado = modos_trabalho[modo_pill]
                st.caption(f"💡 {modos_descricao[modo_pill]}")

            col_m_auto, col_d_auto, col_lu_auto = st.columns([2, 2, 1])
            with col_m_auto:
                st.markdown("**Mês de Lançamento**")
                mes_selecionado = st.selectbox(
                    "Mês de Lançamento",
                    ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"],
                    index=datetime.now().month - 1, 
                    key="mes_auto",
                    label_visibility="collapsed"
                )
            with col_d_auto:
                st.markdown("**Data do Roteiro**")
                now_sp = get_now_sp()
                data_roteiro = st.date_input("Data", value=now_sp, format="DD/MM/YYYY", key="data_auto", label_visibility="collapsed")
                data_roteiro_str = data_roteiro.strftime('%d/%m/%y')
            with col_lu_auto:
                st.markdown("**Personagem**")
                com_lu_auto = st.selectbox("Cena 1", ["Com LU", "Sem LU"], key="com_lu_auto_opt", label_visibility="collapsed")

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
                
                if st.button("🚀 Iniciar Extração e Geração", use_container_width=True, type="primary", key="btn_auto"):
                    if modo_selecionado not in ["NW (NewWeb)", "3D (NewWeb 3D)", "SOCIAL (Reels/TikTok)"]:
                        st.warning(f"🚧 O formato {modo_selecionado} ainda está em desenvolvimento.")
                        st.stop()
                    
                    codigos = [str(row['SKU Principal']).strip() for _, row in df_edited.iterrows()]
                    total = len(codigos)
                    progress_text = st.empty()
                    bar = st.progress(0)
                    
                    sp_cli = st.session_state.get('supabase_client')
                    modelo_id = st.session_state.get('modelo_llm', 'gemini-2.5-flash')
                    table_prefix = st.session_state.get('table_prefix', 'nw_')
                    
                     # Instancia Agente (fora do loop para eficiência)
                    agent = RoteiristaAgent(supabase_client=sp_cli, model_id=modelo_id, table_prefix=table_prefix)
                    
                    erros_lote = []
                    for i, (idx, row) in enumerate(df_edited.iterrows()):
                        current_code = str(row['SKU Principal']).strip()
                        percent = int((i + 1) / total * 100)
                        progress_text.markdown(f"**⏳ Processando {i+1}/{total} ({percent}%):** SKU {current_code}")
                        bar.progress((i + 1) / total)
                        
                        try:
                            with st.status(f"🚀 SKU {current_code} ({i+1}/{total})", expanded=True) as status_box:
                                
                                # 1. Scrape
                                status_box.write("🔍 **Etapa 1:** Extraindo dados técnicos Magalu (Scraping)...")
                                gemini_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
                                ficha_extraida = scrape_with_gemini(current_code, api_key=gemini_key)
                                
                                # 2. Geração
                                status_box.write("🧠 **Etapa 2:** Consultando IA e aplicando aprendizados (Agent)...")
                                val_sub = row['Outros Códigos (Cor/Voltagem)']; sub_skus = str(val_sub).strip() if pd.notna(val_sub) and str(val_sub).lower() != 'nan' else ''
                                val_vid = row['Vídeo do Fornecedor (Link)']; video_url = str(val_vid).strip() if pd.notna(val_vid) and str(val_vid).lower() != 'nan' else ''
                                
                                res_gen = agent.gerar_roteiro(
                                    scraped_data=ficha_extraida,
                                    modo_trabalho=modo_selecionado,
                                    codigo=current_code,
                                    sub_skus=sub_skus,
                                    video_url=video_url,
                                    data_roteiro=data_roteiro_str,
                                    mes=mes_selecionado
                                )
                                
                                # 3. Resultado e Salvamento
                                status_box.write("💾 **Etapa 3:** Registrando no histórico e finalizando...")
                                global_num = get_total_script_count(sp_cli) + 1
                                novo_roteiro = {
                                    "_uid": str(uuid.uuid4()),
                                    "ficha": ficha_extraida,
                                    "roteiro_original": res_gen["roteiro"],
                                    "codigo": current_code,
                                    "model_id": res_gen["model_id"],
                                    "tokens_in": res_gen["tokens_in"],
                                    "tokens_out": res_gen["tokens_out"],
                                    "custo_brl": res_gen["custo_brl"],
                                    "global_num": global_num,
                                    "mes": mes_selecionado
                                }
                                
                                # Log Histórico
                                if sp_cli:
                                    try:
                                        sp_cli.table(f"{table_prefix}historico_roteiros").insert({
                                            "codigo_produto": current_code,
                                            "modo_trabalho": modo_selecionado,
                                            "roteiro_gerado": res_gen["roteiro"],
                                            "ficha_extraida": str(ficha_extraida)[:5000],
                                            "modelo_llm": res_gen["model_id"],
                                            "tokens_entrada": res_gen["tokens_in"],
                                            "tokens_saida": res_gen["tokens_out"],
                                            "custo_estimado_brl": res_gen["custo_brl"],
                                            "categoria_id": cat_selecionada_id,
                                            "criado_em": get_now_sp().isoformat()
                                        }).execute()
                                    except Exception as e:
                                        print(f"❌ Erro ao salvar histórico (Auto): {e}")
                                
                                status_box.update(label=f"✅ SKU {current_code} Finalizado!", state="complete")
                                
                                st.session_state['roteiros'].insert(0, novo_roteiro)
                        except Exception as e:
                            err_msg = f"❌ Erro no SKU {current_code}: {str(e)}"
                            st.error(err_msg)
                            erros_lote.append(err_msg)

                    st.session_state['roteiro_ativo_idx'] = 0
                    if erros_lote:
                        st.session_state['last_errors'] = erros_lote
                    
                    if not erros_lote:
                        st.success(f"🎯 Geração de {total} roteiros concluída!")
                    else:
                        st.warning(f"⚠️ Concluído com {len(erros_lote)} erro(s). Veja os detalhes acima.")
                    
                    st.rerun()

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
                if st.button("➕ Adicionar", use_container_width=True, type="secondary", key="btn_add_ficha"):
                    st.session_state['num_fichas'] += 1
                    st.rerun()
            with col_rem:
                if st.session_state['num_fichas'] > 1:
                    if st.button("➖ Remover", use_container_width=True, type="secondary", key="btn_rem_ficha"):
                        st.session_state['num_fichas'] -= 1
                        st.rerun()

            st.markdown("---")
            
            col_m_man, col_d_man, col_lu_man = st.columns([2, 2, 1])
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
            with col_lu_man:
                st.markdown("**Personagem**")
                com_lu_man = st.selectbox("Cena 1", ["Com LU", "Sem LU"], key="com_lu_man_opt", label_visibility="collapsed")
            
            # Seletor de modo manual
            st.markdown("**Formato do Roteiro (Manual)**")
            modo_manual_input = st.selectbox("Selecione:", list(modos_trabalho.keys()), key="modo_man")
            modo_man_selecionado = modos_trabalho[modo_manual_input]

            if st.button("🚀 Gerar Roteiros a partir de Fichas", use_container_width=True, type="primary", key="btn_manual"):
                fichas_validas = [f for f in fichas_informadas if f["ficha"].strip() and f["sku"].strip()]
                
                if not fichas_validas:
                    st.warning("⚠️ Preencha o Código e a Ficha Técnica de pelo menos um produto.")
                else:
                    total = len(fichas_validas)
                    bar = st.progress(0)
                    sp_cli = st.session_state.get('supabase_client')
                    modelo_id = st.session_state.get('modelo_llm', 'gemini-3-flash-preview')
                    table_prefix = st.session_state.get('table_prefix', 'nw_')

                    # Instancia Agente (fora do loop para eficiência)
                    agent = RoteiristaAgent(supabase_client=sp_cli, model_id=modelo_id, table_prefix=table_prefix)
                    
                    progress_text_man = st.empty()
                    for i, itm in enumerate(fichas_validas):
                        percent = int((i + 1) / total * 100)
                        progress_text_man.markdown(f"**⏳ Processando {i+1}/{total} ({percent}%):** SKU {itm['sku']}")
                        bar.progress((i+1)/total)
                        
                        try:
                            with st.status(f"🚀 SKU {itm['sku']} ({i+1}/{total})", expanded=True) as status_box_man:
                                # 1. Preparação
                                status_box_man.write("📝 **Etapa 1:** Processando ficha técnica manual...")
                                ficha_man = {"text": itm["ficha"], "images": []}
                                
                                # 2. Geração
                                status_box_man.write("🧠 **Etapa 2:** Consultando IA e aplicando aprendizados...")
                                res_gen = agent.gerar_roteiro(
                                    scraped_data=ficha_man,
                                    modo_trabalho=modo_man_selecionado,
                                    codigo=itm["sku"],
                                    data_roteiro=data_roteiro_str_man,
                                    mes=mes_selecionado_man,
                                    com_lu=(com_lu_man == "Com LU")
                                )
                                
                                # 3. Salvamento
                                status_box_man.write("💾 **Etapa 3:** Registrando no histórico...")
                                global_num = get_total_script_count(sp_cli) + 1
                                novo_roteiro = {
                                    "_uid": str(uuid.uuid4()),
                                    "ficha": ficha_man,
                                    "roteiro_original": res_gen["roteiro"],
                                    "codigo": itm["sku"],
                                    "model_id": res_gen["model_id"],
                                    "tokens_in": res_gen["tokens_in"],
                                    "tokens_out": res_gen["tokens_out"],
                                    "custo_brl": res_gen["custo_brl"],
                                    "global_num": global_num,
                                    "mes": mes_selecionado_man
                                }
                                st.session_state['roteiros'].insert(0, novo_roteiro)
                                
                                # Log Histórico
                                if sp_cli:
                                    try:
                                        sp_cli.table(f"{table_prefix}historico_roteiros").insert({
                                            "codigo_produto": itm['sku'],
                                            "modo_trabalho": modo_man_selecionado,
                                            "roteiro_gerado": res_gen["roteiro"],
                                            "ficha_extraida": itm['ficha'],
                                            "tokens_entrada": res_gen["tokens_in"],
                                            "tokens_saida": res_gen["tokens_out"],
                                            "custo_estimado_brl": res_gen["custo_brl"],
                                            "modelo_llm": res_gen["model_id"],
                                            "categoria_id": cat_selecionada_id
                                        }).execute()
                                    except Exception as e:
                                        print(f"❌ Erro ao salvar histórico (Manual): {e}")
                                
                                status_box_man.update(label=f"✅ SKU {itm['sku']} Finalizado!", state="complete")
                                
                        except Exception as e:
                            st.error(f"Erro no SKU {itm['sku']}: {e}")

                    st.session_state['roteiro_ativo_idx'] = 0
                    st.rerun()

    # --- SCRIPTS DA SESSÃO (CARDS VISÍVEIS — SEM EXPANDER) ---
    if 'roteiros' in st.session_state and st.session_state['roteiros']:
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("### 📋 Mesa de Trabalho")
        
        if 'selected_mix' not in st.session_state:
            st.session_state['selected_mix'] = []
            
        # Lista simplificada por SKU
        st.info("💡 Selecione um produto para editar abaixo. Marque os checkboxes para combinar roteiros.")
        
        for idx, r_item in enumerate(st.session_state["roteiros"]):
            codigo_card = r_item.get("codigo", "...")
            num_tag = f"#{r_item.get('global_num', '?')}"
            modelo_tag = r_item.get("model_id", "").split("/")[-1][:12]
            
            # Tenta pegar o nome do produto da ficha
            ficha_raw = r_item.get('ficha', '')
            ficha_str = ficha_raw.get('text', str(ficha_raw)) if isinstance(ficha_raw, dict) else str(ficha_raw)
            linhas_f = ficha_str.split('\n')
            nome_p_card = linhas_f[0][:40].strip() if linhas_f and len(linhas_f[0]) > 2 else "Produto"
            
            custo = r_item.get("custo_brl", 0)
            tag_custo = "Grátis" if custo == 0 else f"R$ {custo:.4f}"
            is_active = st.session_state.get("roteiro_ativo_idx", 0) == idx
            is_best_version = r_item.get("is_best_version", False)
            
            # Muda cor da tag se for a Melhor Versão
            tag_color = "#10b981" if is_best_version else "#0086ff"
            tag_icon = "🌟" if is_best_version else "🧠"
            
            # Título diferenciado se for melhor versão
            titulo_display = f"**{num_tag} - {codigo_card}** | *{nome_p_card}*"
            is_nw3d = (st.session_state.get('active_mode') == 'NW 3D')
            cor_otimizado = "violet" if is_nw3d else "green"
            
            if is_best_version:
                titulo_display = f"**{num_tag} - {codigo_card}** | :{cor_otimizado}[*{nome_p_card} - (MELHOR VERSÃO)*]"

            
            # Injetamos o estilo do botão fora das colunas para não quebrar o alinhamento vertical
            if is_best_version and is_active:
                 btn_colors = ("#7c3aed", "#8b5cf6", "rgba(139, 92, 246, 0.4)", "#a78bfa") if is_nw3d else ("#059669", "#10b981", "rgba(16, 185, 129, 0.4)", "#34d399")
                 st.markdown(f"""
                    <style>
                    div.stButton > button[key="sel_{idx}"] {{
                        background: linear-gradient(135deg, {btn_colors[0]} 0%, {btn_colors[1]} 100%) !important;
                        border: 1px solid {btn_colors[3]} !important;
                        box-shadow: 0 0 15px {btn_colors[2]} !important;
                        color: white !important;
                    }}
                    </style>
                    """, unsafe_allow_html=True)

            btn_col_check, btn_col_sel, btn_col_info, btn_col_del = st.columns([0.5, 1.5, 3.5, 0.5])
            
            with btn_col_check:
                is_selected = idx in st.session_state['selected_mix']
                st.checkbox("Mix", value=is_selected, key=f"mix_{idx}", label_visibility="collapsed")
                # Atualiza lista de mix (simplificado para evitar re-runs excessivos)
                if st.session_state[f"mix_{idx}"] != is_selected:
                    if st.session_state[f"mix_{idx}"]: st.session_state['selected_mix'].append(idx)
                    else: st.session_state['selected_mix'].remove(idx)
                    st.rerun()
            
            with btn_col_sel:
                btn_label_edit = "✏️ Editar"
                if st.button(btn_label_edit, key=f"sel_{idx}", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state["roteiro_ativo_idx"] = idx
                    st.rerun()

            with btn_col_info:
                st.markdown(titulo_display)
                st.caption(f"{tag_icon} {modelo_tag.upper()} | {tag_custo}")

            with btn_col_info:
                pass # Já preenchido acima
            
            with btn_col_del:
                # Botão para fechar/remover da mesa
                if st.button("❌", key=f"del_{idx}", help="Remover roteiro da mesa"):
                    st.session_state["roteiros"].pop(idx)
                    
                    # Ajusta as seleções (selected_mix) que pudessem estar abaixo ou acima
                    if idx in st.session_state["selected_mix"]:
                        st.session_state["selected_mix"].remove(idx)
                    # Rebaixa os índices de quem estava abaixo dele
                    st.session_state["selected_mix"] = [i - 1 if i > idx else i for i in st.session_state["selected_mix"]]
                    
                    # Ajusta o index ativo
                    ativo = st.session_state.get("roteiro_ativo_idx", 0)
                    if ativo == idx:
                        st.session_state["roteiro_ativo_idx"] = max(0, idx - 1)
                    elif ativo > idx:
                        st.session_state["roteiro_ativo_idx"] -= 1
                        
                    st.rerun()
                
        # --- AÇÃO: BOTÃO CRIAR MELHOR VERSÃO ---
        # Fica aqui na parte de baixo, após o loop de roteiros
        num_selecionados = len(st.session_state['selected_mix'])
        if num_selecionados >= 2:
            st.markdown("<br><hr style='margin: 10px 0; border-color: rgba(16, 185, 129, 0.3);'>", unsafe_allow_html=True)
            
            # Usando CSS para deixar o botão explicitamente verde
            st.markdown("""
                <style>
                div[data-testid="stButton"] button[kind="primary"].btn-verde {
                    background: linear-gradient(135deg, #059669 0%, #10b981 100%) !important;
                    border: 1px solid #34d399 !important;
                    color: white !important;
                }
                div[data-testid="stButton"] button[kind="primary"].btn-verde:hover {
                    box-shadow: 0 0 15px rgba(16, 185, 129, 0.6) !important;
                }
                </style>
            """, unsafe_allow_html=True)
            
            # Envolvemos num container pra aplicar classe ou usar placeholder caso bugue no front
            col_v1, col_v2, col_v3 = st.columns([1, 4, 1])
            with col_v2:
                # Dica para usar CSS Injection no Streamlit
                st.markdown('<div class="btn-verde-container">', unsafe_allow_html=True)
                if st.button(f"✨ CRIAR MELHOR VERSÃO ({num_selecionados} ROTERIOS) ✨", key="btn_create_best", use_container_width=True, type="primary"):
                    if num_selecionados > 5:
                        st.error("🚨 Selecione NO MÁXIMO 5 roteiros para mesclar.")
                    else:
                        with st.status("🌟 Iniciando a Criação da Melhor Versão...", expanded=True) as status:
                            st.write("📥 Reunindo os textos selecionados...")
                            roteiros_to_mix = [st.session_state['roteiros'][i] for i in st.session_state['selected_mix']]
                            textos_para_mix = [r['roteiro_original'] for r in roteiros_to_mix]
                            
                            st.write("🔍 Extraindo Ficha Técnica como referência...")
                            ficha_base = roteiros_to_mix[0].get('ficha', '')
                            ficha_str = ficha_base.get('text', str(ficha_base)) if isinstance(ficha_base, dict) else str(ficha_base)
                            nome_produto = roteiros_to_mix[0].get('codigo', 'Produto')
                            
                            st.write("🧠 Acionando a Inteligência Artificial (Diretor de Criação)...")
                            try:
                                ag = RoteiristaAgent(
                                    supabase_client=st.session_state.get('supabase_client'),
                                    model_id=st.session_state.get('modelo_llm', 'gemini-3-flash-preview'),
                                    table_prefix=st.session_state.get('table_prefix', 'nw_')
                                )
                                resultado = ag.otimizar_roteiros(
                                    roteiros_textos=textos_para_mix,
                                    codigo=roteiros_to_mix[0].get('codigo', ''),
                                    nome_produto=nome_produto,
                                    ficha_tecnica=ficha_str
                                )
                                
                                st.write("✅ Roteiro sintetizado com sucesso!")
                                status.update(label="🚀 Melhor versão concluída!", state="complete", expanded=False)
                                
                                novo_roteiro = {
                                    "ficha": roteiros_to_mix[0].get('ficha', ''),
                                    "roteiro_original": resultado["roteiro"],
                                    "categoria_id": roteiros_to_mix[0].get('categoria_id', 1),
                                    "codigo": roteiros_to_mix[0].get('codigo', ''),
                                    "model_id": resultado["model_id"],
                                    "tokens_in": resultado["tokens_in"],
                                    "tokens_out": resultado["tokens_out"],
                                    "custo_brl": resultado["custo_brl"],
                                    "global_num": roteiros_to_mix[0].get('global_num', 0),
                                    "mes": roteiros_to_mix[0].get('mes', 'MAR'),
                                    "is_best_version": True,
                                    "_uid": str(uuid.uuid4())
                                }
                                
                                # --- AUTO-SALVAR NO HISTÓRICO DO BANCO ---
                                try:
                                    sp_hist = st.session_state.get('supabase_client')
                                    if sp_hist:
                                        sp_hist.table(f"{st.session_state.get('table_prefix', 'nw_')}historico_roteiros").insert({
                                            "codigo_produto": roteiros_to_mix[0].get('codigo', ''),
                                            "modo_trabalho": roteiros_to_mix[0].get('modo_trabalho', 'NW (NewWeb)'), # Mantém o original
                                            "roteiro_gerado": resultado["roteiro"],
                                            "ficha_extraida": ficha_str[:5000],
                                            "modelo_llm": f"{resultado['model_id']} (Otimizado)", # Marca no modelo
                                            "tokens_entrada": resultado["tokens_in"],
                                            "tokens_saida": resultado["tokens_out"],
                                            "custo_estimado_brl": resultado["custo_brl"]
                                        }).execute()
                                except Exception as e:
                                    st.error(f"Erro ao salvar no banco: {e}")

                                st.session_state['roteiros'].insert(0, novo_roteiro)
                                st.session_state['roteiro_ativo_idx'] = 0
                                st.session_state['selected_mix'] = []
                                st.rerun()
                                
                            except Exception as e:
                                status.update(label=f"❌ Erro: {e}", state="error")
                st.markdown('</div>', unsafe_allow_html=True)
                
        # Limpar só a mesa de trabalho (movido para ficar debaixo da lista de seleções)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Limpar Mesa de Trabalho", use_container_width=True, type="secondary"):
            if 'roteiros' in st.session_state:
                del st.session_state['roteiros']
            if 'roteiro_ativo_idx' in st.session_state:
                del st.session_state['roteiro_ativo_idx']
            if 'selected_mix' in st.session_state:
                del st.session_state['selected_mix']
            st.rerun()

    # --- HISTÓRICO DO BANCO (Expandível, separado) ---
    if 'supabase_client' in st.session_state:
        is_hist_open = st.session_state.get('hist_open', False)
        with st.expander("📜 Histórico do Banco de Dados", expanded=is_hist_open):
            sp_h = st.session_state['supabase_client']
            try:
                res_recent = sp_h.table(f"{st.session_state.get('table_prefix', 'nw_')}historico_roteiros").select("criado_em, codigo_produto, modo_trabalho, roteiro_gerado, ficha_extraida, modelo_llm, custo_estimado_brl").order('criado_em', desc=True).limit(500).execute()
                
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
                        num_roteiros_dia = len(dia_df)
                        # Para manter as datas abertas também caso recarregue, salvamos o ID do dia
                        is_dia_open = st.session_state.get('hist_dia_open') == dia.strftime('%d/%m/%Y')
                        with st.expander(f"📁 {dia.strftime('%d/%m/%Y')} ({num_roteiros_dia} roteiros)", expanded=is_dia_open):
                            cols_db = st.columns(4)
                            for i, (_, r_row) in enumerate(dia_df.iterrows()):
                                # Inverte a numeração para que o primeiro (mais antigo do dia) seja #1
                                n_hist = len(dia_df) - i
                                model_label = r_row['modelo_llm'].split('/')[-1] if r_row['modelo_llm'] else "IA"
                                # Destaca de cor específica caso seja rota "otimizada" no modelo
                                is_nw3d = (st.session_state.get('active_mode') == 'NW 3D')
                                cor_bot = "violet" if is_nw3d else "green"
                                
                                if "(otimizado)" in model_label.lower():
                                    btn_label = f"👁️ {r_row['codigo_produto']} :{cor_bot}[*{model_label.upper()}*]"
                                    is_otimizado = True
                                else:
                                    btn_label = f"👁️ {r_row['codigo_produto']} :blue[*{model_label.upper()}*]"
                                    is_otimizado = False
                                    
                                with cols_db[i % 4]:
                                    if st.button(btn_label, key=f"recall_{r_row['criado_em']}", use_container_width=True):
                                        rec_item = {
                                            "ficha": r_row['ficha_extraida'],
                                            "roteiro_original": r_row['roteiro_gerado'],
                                            "categoria_id": 77,
                                            "codigo": r_row['codigo_produto'],
                                            "model_id": r_row['modelo_llm'],
                                            "custo_brl": r_row['custo_estimado_brl'],
                                            "is_best_version": is_otimizado,
                                            "_uid": str(uuid.uuid4())
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
                                        
                                        # Verifica se já existe na mesa (mesmo SKU e mesmo Modelo)
                                        existing_idx = next(
                                            (idx for idx, x in enumerate(st.session_state['roteiros']) 
                                             if str(x.get('codigo')) == str(rec_item['codigo']) and str(x.get('model_id')) == str(rec_item['model_id'])), 
                                            -1
                                        )
                                        
                                        if existing_idx == -1: # Não existe, insere novo no topo
                                            st.session_state['roteiros'].insert(0, rec_item)
                                            st.session_state['roteiro_ativo_idx'] = 0
                                        else: # Já existe, foca nele
                                            st.session_state['roteiro_ativo_idx'] = existing_idx
                                            
                                        st.session_state['hist_open'] = True
                                        st.session_state['hist_dia_open'] = dia.strftime('%d/%m/%Y')
                                        st.rerun()
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
        num_roteiros_sessao = len(st.session_state['roteiros'])
        st.download_button(
            label=f"📦 BAIXAR TODOS ({num_roteiros_sessao}) SESSÃO ATUAL (ZIP)",
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
            is_nw3d = (st.session_state.get('active_mode') == 'NW 3D')
            if item.get("is_best_version"):
                border_color = "#8b5cf6" if is_nw3d else "#10b981"
                shadow_color = "rgba(139, 92, 246, 0.2)" if is_nw3d else "rgba(16, 185, 129, 0.2)"
            else:
                border_color = "#0086ff"
                shadow_color = "rgba(0, 134, 255, 0.1)"
            
            st.markdown(f"""
            <div style='background: #1e2530; padding: 20px; border-radius: 12px; border: 2px solid {border_color}; box-shadow: 0 4px 15px {shadow_color}; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: start;'>
                <div>
                    <h4 style='margin: 0; color: {border_color}; font-weight: 700;'>{'🌟 Melhor Versão: ' if item.get("is_best_version") else '✨ Edição: '}{codigo_produto}</h4>
                    <p style='margin: 5px 0 0 0; font-size: 13px; color: #8b92a5;'>{titulo_curto}</p>
                </div>
                <div style='text-align: right;'>
                    <span style='background: {shadow_color}; color: {border_color}; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;'>🧠 {item.get('model_id', 'Desconhecido')}</span>
                    <div style='margin-top: 5px; font-size: 11px; color: {border_color}; font-weight: 700;'>{tag_custo}</div>
                    <div style='margin-top: 5px; font-size: 10px; color: #4a5568;'>{tokens_text}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
            # O Canva do Roteiro Ativo
            with st.container(border=True):
                # Usamos o _uid único do item para garantir que o text_area resete ao trocar de script
                script_uid = item.get("_uid", f"{idx}_{codigo_produto}")
                editor_key = f"edit_session_{script_uid}"
                
                # Se mudamos de script (ou o script no index mudou), sincronizamos o session state do editor
                if st.session_state.get("last_script_uid") != script_uid:
                    st.session_state[editor_key] = item['roteiro_original']
                    st.session_state["last_script_uid"] = script_uid

                edited_val = st.text_area(
                    "Editor",
                    value=st.session_state.get(editor_key, item['roteiro_original']),
                    height=450,
                    key=f"text_area_{script_uid}",
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
                    selected_date=st.session_state.get('data_roteiro_global'),
                    model_id=item.get('model_id', '')
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
                        think_calib = st.empty()
                        with st.spinner("A IA está analisando suas correções..."):
                            try:
                                think_calib.markdown("💭 *IA Pensando: '🧐 Comparando roteiro original com sua edição para detectar padrões...'*")
                                res_c = sp_cli.table(f"{st.session_state.get('table_prefix', 'nw_')}categorias").select("id, nome").execute()
                                lista_c = res_c.data if hasattr(res_c, 'data') else []
                            except:
                                lista_c = []
                            
                            local_agent = RoteiristaAgent(model_id="gemini-3-flash-preview", table_prefix=st.session_state.get('table_prefix', 'nw_'))
                            calc = local_agent.analisar_calibracao(item['roteiro_original'], edited_val, lista_c, codigo_produto)
                            think_calib.empty()
                            st.session_state['pending_calibration'] = {
                                'calc': calc,
                                'roteiro_ia': item['roteiro_original'],
                                'roteiro_humano': edited_val,
                                'titulo_curto': titulo_curto,
                                'codigo_p': codigo_produto
                            }
                            st.session_state['show_diff'] = False
                            modal_resultado_calibragem(calc, sp_cli, item['roteiro_original'], edited_val, titulo_curto, codigo_produto)
                    else:
                        st.error("Conecte o Supabase primeiro.")
            
            with col_ouro:
                if st.button("🏆 Enviar Ouro", key=f"ouro_{idx}", use_container_width=True, type="secondary"):
                    salvar_ouro(sp_cli, cat_id_roteiro, titulo_curto, edited_val)

        if st.session_state.get('roteiro_ativo_idx', 0) >= len(st.session_state['roteiros']):
             st.session_state['roteiro_ativo_idx'] = 0
             
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
            prefix = st.session_state.get('table_prefix', 'nw_')
            res_est = sp_client.table(f"{prefix}treinamento_estruturas").select("*").execute()
            res_fon = sp_client.table("nw_treinamento_fonetica").select("*").execute()
            res_pers = sp_client.table("nw_treinamento_persona_lu").select("*").execute()
            res_ouro = sp_client.table(f"{prefix}roteiros_ouro").select("*").execute()
            res_cats = sp_client.table("nw_categorias").select("*").execute()
            res_nuan = sp_client.table(f"{prefix}treinamento_nuances").select("*").execute()
            res_img = sp_client.table(f"{prefix}treinamento_imagens").select("*").execute()
            
            df_est = pd.DataFrame(res_est.data if hasattr(res_est, 'data') else [])
            df_fon = pd.DataFrame(res_fon.data if hasattr(res_fon, 'data') else [])
            df_pers = pd.DataFrame(res_pers.data if hasattr(res_pers, 'data') else [])
            df_ouro = pd.DataFrame(res_ouro.data if hasattr(res_ouro, 'data') else [])
            df_cats = pd.DataFrame(res_cats.data if hasattr(res_cats, 'data') else [])
            df_nuan = pd.DataFrame(res_nuan.data if hasattr(res_nuan, 'data') else [])
            df_img = pd.DataFrame(res_img.data if hasattr(res_img, 'data') else [])
            
            # --- CONVERSÃO DE FUSO HORÁRIO GLOBAL (UTC -> SÃO PAULO) ---
            for df in [df_est, df_fon, df_pers, df_ouro, df_cats, df_nuan, df_img]:
                if not df.empty and 'criado_em' in df.columns:
                    # Garantir que é datetime para ordenar corretamente
                    df['criado_em'] = pd.to_datetime(df['criado_em'])
                    df.sort_values(by='criado_em', ascending=False, inplace=True)
                    # Agora converte para string formatada para exibição
                    df['criado_em'] = df['criado_em'].apply(convert_to_sp_time)
                    
        except Exception as e:
            st.error(f"Erro ao carregar dados do hub: {e}")
            df_est = df_fon = df_pers = df_ouro = df_cats = df_nuan = df_img = pd.DataFrame()

        tab_fb, tab_nuan, tab_est, tab_img, tab_pers, tab_fon, tab_ouro, tab_cat = st.tabs(["⚖️ Calibragem", "🧠 Nuances", "💬 Ganchos & CTAs", "📸 Imagens", "💃 Persona", "🗣️ Fonética", "🏆 Roteiros Ouro", "📂 Categorias"])
        
        # --- FUNÇÕES MODAIS DE DOCUMENTAÇÃO ---
        @st.dialog("📚 Guia do Redator V3.0", width="large")
        def modal_doc_redator():
            try:
                with open("docs/calibragem_redatores_v3.0.md", "r", encoding="utf-8") as f:
                    st.markdown(f.read())
            except Exception as e:
                st.error(f"Arquivo não encontrado: {e}")

        @st.dialog("⚙️ Documentação Técnica V3.0", width="large")
        def modal_doc_tecnica():
            try:
                with open("docs/calibragem_tecnica_v3.0.md", "r", encoding="utf-8") as f:
                    st.markdown(f.read())
            except Exception as e:
                st.error(f"Arquivo não encontrado: {e}")

        with tab_fb:
            col_header, col_btn1, col_btn2 = st.columns([2.5, 1, 1])
            with col_header:
                st.markdown("### ⚖️ Calibragem (IA vs Humano)")
                st.caption("Compare e treine a IA automaticamente.")
            with col_btn1:
                if st.button("📚 Guia do Redator", use_container_width=True):
                    modal_doc_redator()
            with col_btn2:
                if st.button("⚙️ Manual Técnico", use_container_width=True):
                    modal_doc_tecnica()
            
            st.markdown("""
            <div style='background-color: rgba(0, 134, 255, 0.1); padding: 15px; border-radius: 8px; border-left: 5px solid #0084ff; margin-bottom: 20px;'>
                <p style='font-size: 0.9rem; font-weight: 600; color: #0084ff; margin-bottom: 8px;'>⭐ Como funciona a Nova Régua de Calibragem?</p>
                <ul style='font-size: 0.82rem; color: #8b92a5; list-style-type: none; padding-left: 0; margin-bottom: 0; line-height: 1.5;'>
                    <li>• <b>4.8 a 5.0 (Quase Perfeito):</b> O humano fez apenas ajustes finos de estilo, conectivos ou pontuação.</li>
                    <li>• <b>4.0 a 4.7 (Muito Bom):</b> Mudanças notáveis de estilo, encurtamento para fluidez ou troca de jargões técnicos.</li>
                    <li>• <b>3.0 a 3.9 (Regular):</b> Mudança Estrutural. Adição de infos que faltavam ou reconstrução de blocos inteiros.</li>
                    <li>• <b>< 3.0 (Ruim):</b> Erro Grave. A IA errou feio o tom de voz, omitiu funcionalidades vitais ou o SKU.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            # --- FORMULÁRIO DE ENTRADA ---
            with st.form("form_calibracao", clear_on_submit=False):
                col_ia, col_humano = st.columns(2)
                with col_ia:
                    st.markdown("**🤖 ANTES (Roteiro da IA)**")
                    roteiro_ia_input = st.text_area("Cole aqui o roteiro original gerado pela IA:", height=200, key="calib_ia")
                with col_humano:
                    st.markdown("**✅ DEPOIS (Aprovado pelo Humano)**")
                    roteiro_humano_input = st.text_area("Cole aqui a versão final aprovada:", height=200, key="calib_humano")
                
                # A IA identificará a categoria automaticamente via analisar_calibracao
                
                submitted = st.form_submit_button("⚖️ Executar Calibragem e Salvar em Ouro", type="primary", use_container_width=True)
                if submitted:
                    if roteiro_ia_input.strip() and roteiro_humano_input.strip():
                        st.toast("🧠 Enviando para a IA analisar...", icon="⏳")
                        think_hub = st.empty()
                        try:
                            # Usa qualquer provedor disponível (Puter/OpenRouter/Gemini)
                            # Determina qual model_id usar para instanciar o agente. Novo Default: Gemini 2.0 Flash
                            _calib_model = "gemini-2.0-flash"
                            # Verifica tanto env quanto secrets
                            gemini_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
                            puter_key = os.environ.get("PUTER_API_KEY") or st.secrets.get("PUTER_API_KEY")
                            openrouter_key = os.environ.get("OPENROUTER_API_KEY") or st.secrets.get("OPENROUTER_API_KEY")

                            if gemini_key:
                                _calib_model = "gemini-2.0-flash"
                            elif puter_key:
                                _calib_model = "puter/x-ai/grok-4-1-fast"
                            elif openrouter_key:
                                _calib_model = "openrouter/deepseek/deepseek-r1:free"
                            else:
                                st.error("Nenhuma chave de IA configurada (Gemini, Puter ou OpenRouter).")
                                _calib_model = None
                            
                            if _calib_model:
                                ag = RoteiristaAgent(
                                    supabase_client=sp_client, 
                                    model_id=_calib_model,
                                    table_prefix=st.session_state.get('table_prefix', 'nw_')
                                )
                                think_hub.markdown("💭 *IA Pensando: '🧐 Analisando as nuances da sua edição comparada ao original...'*")
                                with st.spinner("🧠 Analisando a calibragem para identificar lições aprendidas..."):
                                    cats_list_manual = df_cats[['id', 'nome']].to_dict('records') if not df_cats.empty else []
                                    calc = ag.analisar_calibracao(roteiro_ia_input, roteiro_humano_input, cats_list_manual)
                                    
                                think_hub.empty()
                                st.session_state['pending_calibration'] = {
                                    'calc': calc,
                                    'roteiro_ia': roteiro_ia_input,
                                    'roteiro_humano': roteiro_humano_input,
                                    'titulo_curto': calc['codigo_produto'],
                                    'codigo_p': calc['codigo_produto']
                                }
                                st.session_state['show_diff'] = False
                                modal_resultado_calibragem(calc, sp_client, roteiro_ia_input, roteiro_humano_input, calc['codigo_produto'], calc['codigo_produto'])
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
                
                df_view = df_ouro[cols_view + (['categoria_id'] if 'categoria_id' in df_ouro.columns else [])].dropna(subset=['aprendizado']).copy()
                df_view = df_view.reset_index(drop=True)
                
                # Mapeia nome da categoria
                if not df_cats.empty and 'categoria_id' in df_view.columns:
                    cat_map = dict(zip(df_cats['id'], df_cats['nome']))
                    df_view['categoria_id'] = df_view['categoria_id'].map(cat_map).fillna("Genérico")

                # Adiciona Sequential ID (#005, #004...) e Emojis de Qualidade
                total_calib = len(df_view)
                df_view.index = [f"#{total_calib - i:03d}" for i in range(total_calib)]
                
                if 'nota_percentual' in df_view.columns:
                    def safe_format_stars(x):
                        try:
                            val = float(x)
                            if pd.isna(val): return "-"
                            return f"{'🟢' if val/20.0 >= 4.0 else ('🟡' if val/20.0 >= 3.0 else '🔴')} {val/20.0:.1f} ⭐ ({int(val)}%)"
                        except:
                            return "-"
                    df_view['nota_percentual'] = df_view['nota_percentual'].apply(safe_format_stars)

                rename_map = {
                    'categoria_id': 'Categoria',
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
                st.dataframe(df_nuan[['criado_em', 'frase_ia', 'analise_critica', 'exemplo_ouro']], use_container_width=True)
            else:
                st.info("Nenhuma nuance registrada ainda.")
                
        with tab_est:
            st.markdown("### 💬 Ganchos e Fechamentos (\"Hooks & CTAs\")")
            st.caption("Armazena ganchos criativos e chamadas para ação Aprovadas para a IA usar como inspiração.")
            
            col_est1, col_est2 = st.columns([1, 2])
            with col_est1:
                t_tipo = st.selectbox("Tipo de Estrutura:", ["Abertura (Gancho)", "Fechamento (CTA)"])
            with col_est2:
                t_texto = st.text_area("Texto Ouro (Aprovado):", height=100)
                
            if st.button("Salvar Estrutura", type="primary", use_container_width=True):
                if t_texto.strip():
                    salvar_estrutura(sp_client, t_tipo, t_texto)
                else:
                    st.warning("Preencha o texto da estrutura.")
                    
            st.divider()
            if not df_est.empty:
                cols_display = ['criado_em', 'tipo_estrutura', 'texto_ouro']
                if 'texto_ia_rejeitado' in df_est.columns:
                    cols_display.append('texto_ia_rejeitado')
                st.dataframe(df_est[cols_display], use_container_width=True)
            else:
                st.info("Nenhuma estrutura cadastrada ainda.")

        with tab_img:
            st.markdown("### 📸 Calibragem Visual (Imagens)")
            st.caption("Ensine a IA como descrever as cenas e enquadramentos. O que aparece na tela é tão importante quanto o que a Lu fala.")
            
            with st.form("form_img_manual", clear_on_submit=True):
                col_sku_img, _ = st.columns([1, 2])
                with col_sku_img:
                    i_sku = st.text_input("SKU (Opcional):", placeholder="Ex: 240304700")
                i_ia = st.text_area("Descrição da IA (Erro):", placeholder="Ex: Close no botão de ligar")
                i_hum = st.text_area("Descrição do Humano (Ideal):", placeholder="Ex: Detalhe macro da textura premium do botão em liga metálica")
                i_mot = st.text_area("Motivo da Mudança / Lição:", placeholder="Ex: Valorizar o material e acabamento do produto em vez de apenas a função.")
                
                if st.form_submit_button("📥 Registrar Calibragem Visual", type="primary", use_container_width=True):
                    if i_ia.strip() and i_hum.strip():
                        salvar_imagem(sp_client, i_sku, i_ia, i_hum, i_mot)
                        st.rerun()
                    else:
                        st.warning("Preencha a descrição da IA e do Humano.")
            
            st.divider()
            if not df_img.empty:
                st.dataframe(df_img[['criado_em', 'codigo_produto', 'descricao_ia', 'descricao_humano', 'aprendizado']], use_container_width=True)
            else:
                st.info("Nenhuma calibragem visual cadastrada ainda.")

        with tab_pers:
            st.markdown("### 💃 Persona da Lu")
            st.caption("Diretrizes de comportamento, vocabulário e estilo da personagem Lu do Magalu.")
            
            with st.form("form_persona_manual", clear_on_submit=True):
                p_pilar = st.selectbox("Pilar da Persona:", ["Tom de Voz", "Vocabulário", "Empatia", "Clareza", "Engajamento"])
                p_erro = st.text_area("O que evitar (Erro da IA):", placeholder="Ex: Linguagem muito formal ou uso de termos técnicos complexos.")
                p_cor = st.text_area("Como a Lu diria (Correção):", placeholder="Ex: Linguagem próxima do cliente, usando termos do dia a dia.")
                p_lex = st.text_input("Léxico / Palavras-chave:", placeholder="Ex: 'olha só', 'vem conferir', 'praticidade'")
                
                if st.form_submit_button("📥 Registrar Regra de Persona", type="primary", use_container_width=True):
                    if p_erro.strip() and p_cor.strip():
                        salvar_persona(sp_client, p_pilar, p_erro, p_cor, p_lex, p_erro)
                        st.rerun()
                    else:
                        st.warning("Preencha o erro e a correção.")
            
            st.divider()
            if not df_pers.empty:
                st.dataframe(df_pers[['criado_em', 'pilar_persona', 'texto_corrigido_humano', 'lexico_sugerido']], use_container_width=True)
            else:
                st.info("Nenhuma regra de persona cadastrada ainda.")
                
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
                            "categoria_id": 77,
                            "titulo_produto": t_prod,
                            "roteiro_perfeito": t_rot,
                        }
                        if t_sku.strip():
                            data_ouro["codigo_produto"] = t_sku.strip()
                        sp_client.table(f"{st.session_state.get('table_prefix', 'nw_')}roteiros_ouro").insert(data_ouro).execute()
                        st.success(f"Roteiro Ouro '{t_prod}' cadastrado!")
                        st.rerun()
                    else:
                        st.warning("Preencha pelo menos o título e o roteiro.")
            
            st.divider()
            if not df_ouro.empty:
                # Tabela de visualização
                cols_ouro = ['criado_em', 'titulo_produto', 'roteiro_perfeito']
                if 'codigo_produto' in df_ouro.columns:
                    cols_ouro.insert(1, 'codigo_produto')
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
        "Google (Desempenho & Custo)": ["gemini-3.1-pro-preview", "gemini-3-flash-preview", "gemini-2.5-flash-lite"],
        "Puter / x-AI (Criatividade Premium)": ["puter/x-ai/grok-4-1-fast", "puter/gpt-4o-mini"],
        "Z.ai (Precisão Técnica)": ["zai/glm-4.5-flash"]
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

# --- PÁGINA: COMO FUNCIONA (DOCUMENTAÇÃO) ---
elif page == "Como Funciona":
    st.subheader("📖 Documentação: Magalu AI Suite")
    st.markdown("Entenda a inteligência por trás da ferramenta, as tecnologias que a sustentam e nossa jornada de evolução.")
    
    st.divider()
    
    col_doc1, col_doc2 = st.columns([2, 1])
    
    with col_doc1:
        with st.container(border=True):
            st.markdown("### 🛍️ O que é a Magalu AI Suite?")
            st.markdown("""
                A **Magalu AI Suite** é o resultado de uma parceria intensa entre o desenvolvedor **Tiago Fernandes** e sua **IA Copiloto**. 
                Juntos, construímos uma plataforma *state-of-the-art* para automatizar e elevar a qualidade da 
                criação de roteiros. Ela não apenas gera textos, mas **aprende** continuamente com o estilo humano para 
                personificar a 'Lu' de forma autêntica e persuasiva.
            """)
            
            st.markdown("### ⚙️ Como o sistema opera?")
            st.markdown("""
                O ecossistema é baseado em uma **Arquitetura de Três Camadas** (Ingestão, Inteligência e Persistência) projetada para escalabilidade:
                
                1. **Motor de Ingestão (Scraper 2.0)**: Diferente de scrapers comuns, utilizamos **Google Search Grounding** via Gemini 2.5 Flash. O sistema realiza buscas dinâmicas em tempo real (Search-to-Context), filtrando dados brutos do site oficial Magalu e eliminando 100% dos bloqueios de bot/captcha que interrompiam a produção legada.
                2. **Orquestrador de IA (Roteirista Agent)**: Uma camada lógica que seleciona dinamicamente entre modelos como **Grok 4.1 Fast**, **Gemini 2.5 Pro** ou **GPT-4o Mini**. O roteiro é gerado em multi-step: análise técnica -> aplicação de persona -> verificação fonética automática.
                3. **Loop de Treinamento Autônomo**: Através da **Calibragem**, o sistema realiza um *Diff-Analysis* entre a saída da IA e a edição final do Tiago. As diferenças são convertidas em Regras de Ouro Imperativas (JSON) e salvas no Supabase, alimentando o contexto das próximas gerações (RAG).
            """)
            
            st.markdown("### 🚀 Evolução do Projeto")
            st.info("""
                **v1.0 - Fundação:** Estabelecimento do core em Python e integração inicial com Supabase para persistência de roteiros.  
                **v2.0 - UI & Persona:** Saída do layout padrão para o design 'Galactic Dark'. Implementação do motor de Persona da Lu com diretrizes de tom de voz.  
                **v2.5 - Grounding:** Substituição do scraping direto por busca semântica via Google SDK v2, resolvendo a instabilidade na captura de fichas técnicas.  
                **v2.8 - Calibragem:** Lançamento do módulo de aprendizado autônomo. A IA passou a extrair fonética e estruturas de abertura/fechamento das edições humanas de forma proativa.
            """)

    with col_doc2:
        st.markdown("### 🛠️ Tecnologias Usadas")
        tech_list = [
            ("Python 3.11", "Linguagem core e processamento de dados"),
            ("Streamlit", "Interface reativa e UX premium"),
            ("Supabase", "Banco de Dados relacional e Realtime"),
            ("Google GenAI", "Mente analítica e visão computacional"),
            ("Puter AI", "Redação criativa via Grok 4.1 Fast"),
            ("OpenRouter", "Fallback e raciocínio lógico")
        ]
        
        for t_name, t_desc in tech_list:
            st.markdown(f"**{t_name}**")
            st.caption(t_desc)
            st.write("")
        
        st.divider()
        st.markdown("### 📞 Suporte & Feedback")
        st.markdown("Dúvidas ou sugestões? Entre em contato com o laboratório de IA.")
        st.link_button("BesouroLAB Website", "https://besourolab.com.br", use_container_width=True)

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
                res_hist = sp_client.table(f"{st.session_state.get('table_prefix', 'nw_')}historico_roteiros").select("*").order('criado_em', desc=True).execute()
                
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
        
        # Inicialização preventiva para evitar NameError
        df_ouro = df_pers = df_fon = df_est = df_hist_dash = df_nuan = df_img = df_cats = pd.DataFrame()
        cats_dict = {}
        df_fb = pd.DataFrame()

        # Carrega dados do banco de forma resiliente (tabela por tabela)
        def safe_fetch(table_name, select="*"):
            try:
                res = sp_client.table(table_name).select(select).execute()
                return res.data if hasattr(res, 'data') else []
            except Exception:
                return []

        active_mode = st.session_state.get('active_mode', 'NW Padrão')
        prefix = st.session_state.get('table_prefix', 'nw_')
        
        # MODO SOCIAL: Se for modo Social, usamos as tabelas nw_ mas com filtro de visualização
        fetch_prefix = prefix
        if active_mode == "Discovery (SOCIAL)":
            fetch_prefix = "nw_" # Fallback para usar tabelas existentes enquanto social_ não são criadas

        # Tabelas que variam por prefixo
        ouro_data = safe_fetch(f"{fetch_prefix}roteiros_ouro")
        est_data = safe_fetch(f"{fetch_prefix}treinamento_estruturas")
        hist_data = safe_fetch(f"{fetch_prefix}historico_roteiros", "criado_em, codigo_produto, modo_trabalho, modelo_llm, custo_estimado_brl")
        nuan_data = safe_fetch(f"{fetch_prefix}treinamento_nuances")
        img_data = safe_fetch(f"{fetch_prefix}treinamento_imagens")
        fon_data = safe_fetch(f"{fetch_prefix}treinamento_fonetica")
        
        # Tabelas fixas (sempre nw_)
        pers_data = safe_fetch("nw_treinamento_persona_lu")
        cats_data = safe_fetch("nw_categorias")

        # Inicialização dos DataFrames (Garante colunas base mesmo se vazio)
        cats_dict = {c['id']: c['nome'] for c in cats_data} if cats_data else {}
        df_cats = pd.DataFrame(cats_data)
        
        def safe_df(data, columns):
            df = pd.DataFrame(data)
            if df.empty:
                return pd.DataFrame(columns=columns)
            return df

        df_ouro = safe_df(ouro_data, ['criado_em', 'categoria_id', 'codigo_produto', 'titulo_produto', 'roteiro_original_ia', 'roteiro_perfeito', 'nota_percentual', 'aprendizado'])
        df_pers = safe_df(pers_data, ['criado_em', 'pilar_persona', 'texto_gerado_ia', 'texto_corrigido_humano', 'lexico_sugerido'])
        df_fon = safe_df(fon_data, ['criado_em', 'termo_errado', 'termo_corrigido', 'exemplo_no_roteiro'])
        df_est = safe_df(est_data, ['criado_em', 'tipo_estrutura', 'texto_ia_rejeitado', 'texto_ouro', 'aprendizado'])
        df_hist_dash = safe_df(hist_data, ['criado_em', 'codigo_produto', 'modo_trabalho', 'modelo_llm', 'custo_estimado_brl'])
        df_nuan = safe_df(nuan_data, ['criado_em', 'frase_ia', 'analise_critica', 'exemplo_ouro'])
        df_img = safe_df(img_data, ['criado_em', 'codigo_produto', 'descricao_ia', 'descricao_humano', 'aprendizado'])
        
        # Filtro Global para Modo SOCIAL no Histórico
        if active_mode == "Discovery (SOCIAL)":
            if not df_hist_dash.empty:
                df_hist_dash = df_hist_dash[df_hist_dash['modo_trabalho'] == 'SOCIAL'].copy()

        # Bloco de processamento de dados (calculados)
        try:
            df_fb = pd.DataFrame()
            if not df_ouro.empty:
                # Primeiro mapeia a categoria em df_ouro
                if 'categoria_id' in df_ouro.columns:
                    df_ouro['categoria'] = df_ouro['categoria_id'].map(cats_dict).fillna("Genérico")
                
                if 'roteiro_original_ia' in df_ouro.columns:
                    df_fb = df_ouro[df_ouro['roteiro_original_ia'].notna()].copy()
                    if not df_fb.empty:
                        # Converte nota_percentual (0-100) para labels de sentimento
                        def map_sentimento(p):
                            if pd.isna(p): return "N/A"
                            if p >= 96: return "Ajuste Fino"
                            if p >= 85: return "Edição Moderada"
                            if p >= 60: return "Mudança Estrutural"
                            return "Reescrita Pesada"
                        df_fb['avaliacao_label'] = df_fb['nota_percentual'].apply(map_sentimento)
                        df_fb['estrela'] = df_fb['nota_percentual'].apply(lambda x: f"{(x/20.0):.1f} ⭐" if pd.notna(x) else "-")
            
            if df_fb.empty:
                df_fb = pd.DataFrame(columns=['criado_em', 'estrela', 'categoria', 'avaliacao_label', 'aprendizado', 'roteiro_original_ia', 'roteiro_perfeito'])
            
            # A coluna 'categoria' já foi mapeada acima na nova lógica
            total_ouro = len(df_ouro)
            total_historico = len(df_hist_dash)
            
            # --- SEÇÃO DE FILTROS GLOBAIS ---
            with st.container():
                col_f1, col_f2 = st.columns([1, 2])
                with col_f1:
                    hoje = datetime.now()
                    um_ano_atras = hoje - pd.Timedelta(days=365)
                    periodo = st.date_input(
                        "📅 Período de Análise:",
                        value=(um_ano_atras, hoje),
                        max_value=hoje,
                        key="periodo_dash"
                    )
                with col_f2:
                    search_dash = st.text_input("🔍 Busca Global (Código/Termo):", placeholder="Filtrar tabelas e métricas...")

            # Aplicar Filtro de Data
            if len(periodo) == 2:
                start_date, end_date = pd.to_datetime(periodo[0]), pd.to_datetime(periodo[1])
                # Ajuste para cobrir o dia inteiro da data final
                end_date = end_date.replace(hour=23, minute=59, second=59)
                
                def safe_filter(df, start_d, end_d):
                    if df.empty or 'criado_em' not in df.columns: return df
                    def parse_val(v):
                        try:
                            if isinstance(v, str) and "às" in v:
                                return pd.to_datetime(v, format='%d/%m/%y às %H:%M').tz_localize(None)
                            return pd.to_datetime(v, utc=True).tz_convert('America/Sao_Paulo').tz_localize(None)
                        except: return pd.NaT
                    
                    parsed_dates = df['criado_em'].apply(parse_val)
                    return df[(parsed_dates >= start_d) & (parsed_dates <= end_d)]

                df_ouro = safe_filter(df_ouro, start_date, end_date)
                df_pers = safe_filter(df_pers, start_date, end_date)
                df_fon = safe_filter(df_fon, start_date, end_date)
                df_est = safe_filter(df_est, start_date, end_date)
                df_hist_dash = safe_filter(df_hist_dash, start_date, end_date)
                df_nuan = safe_filter(df_nuan, start_date, end_date)
                df_img = safe_filter(df_img, start_date, end_date)
                df_fb = safe_filter(df_fb, start_date, end_date)

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
                df_img = filter_search(df_img, search_dash)
                df_fb = filter_search(df_fb, search_dash)

            # Recalcular métricas após filtros
            if not df_ouro.empty and 'nota_percentual' in df_ouro.columns:
                taxa_m = df_ouro['nota_percentual'].mean()
                taxa_aprovacao = float(taxa_m) if pd.notna(taxa_m) else 0.0
                media_estrelas = taxa_aprovacao / 20.0
            else:
                taxa_aprovacao = 0.0
                media_estrelas = 0.0
            
            total_ouro = len(df_ouro)
            total_historico = len(df_hist_dash)
            
            # === SEÇÃO 1: MÉTRICAS PREMIUM (HTML/CSS) ===
            custo_total_dash = CUSTO_LEGADO_BRL
            if not df_hist_dash.empty and 'custo_estimado_brl' in df_hist_dash.columns:
                custo_total_dash += df_hist_dash['custo_estimado_brl'].sum() or 0.0
            
            # Cálculo de Cor Dinâmica para o Score (0=Vermelho, 100=Verde)
            def get_score_color(val):
                if val >= 90: return "#10b981" # Verde Brilhante
                if val >= 75: return "#34d399" # Verde Água
                if val >= 60: return "#f59e0b" # Amarelo/Laranja
                if val >= 40: return "#fb923c" # Laranja Escuro
                return "#ef4444" # Vermelho
            
            score_color = get_score_color(taxa_aprovacao)

            st.markdown(f"""
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 15px; margin-bottom: 25px;">
                    <div class="metric-card-premium">
                        <div class="metric-label">📝 Volume Produzido</div>
                        <div class="metric-value">{total_historico}</div>
                        <div style="font-size: 10px; color: #8b92a5; margin-top: 5px;">Roteiros totais</div>
                    </div>
                    <div class="metric-card-premium">
                        <div class="metric-label">⭐ Média de Estrelas</div>
                        <div class="metric-value" style="color: #fcd34d !important;">{media_estrelas:.2f}</div>
                        <div style="font-size: 10px; color: #8b92a5; margin-top: 5px;">Qualidade técnica</div>
                    </div>
                    <div class="metric-card-premium">
                        <div class="metric-label">🎯 Precisão da IA</div>
                        <div class="metric-value" style="color: {score_color} !important;">{taxa_aprovacao:.1f}%</div>
                        <div style="font-size: 10px; color: #8b92a5; margin-top: 5px;">Taxa de aproveitamento</div>
                    </div>
                    <div class="metric-card-premium">
                        <div class="metric-label">📸 Lições Visuais</div>
                        <div class="metric-value" style="color: #8b5cf6 !important;">{len(df_img)}</div>
                        <div style="font-size: 10px; color: #8b92a5; margin-top: 5px;">Memória de imagens</div>
                    </div>
                    <div class="metric-card-premium">
                        <div class="metric-label">💰 Investimento</div>
                        <div class="metric-value">R$ {custo_total_dash:,.2f}</div>
                        <div style="font-size: 10px; color: #8b92a5; margin-top: 5px;">Custo acumulado</div>
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
                st.markdown("#### 🚀 Velocímetro de Performance")
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = taxa_aprovacao,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    number = {'suffix': "%", 'font': {'size': 24, 'color': score_color}},
                    gauge = {
                        'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "silver", 'tickmode': "linear", 'dtick': 10},
                        'bar': {'color': score_color, 'thickness': 0.15},
                        'bgcolor': "rgba(0,0,0,0)",
                        'borderwidth': 0,
                        'steps': [
                            {'range': [0, 20], 'color': 'rgba(239, 68, 68, 0.3)'},   
                            {'range': [20, 40], 'color': 'rgba(249, 115, 22, 0.3)'},  
                            {'range': [40, 60], 'color': 'rgba(245, 158, 11, 0.3)'},  
                            {'range': [60, 80], 'color': 'rgba(132, 204, 22, 0.3)'},  
                            {'range': [80, 100], 'color': 'rgba(16, 185, 129, 0.3)'}  
                        ],
                        'threshold': {
                            'line': {'color': "white", 'width': 8},
                            'thickness': 0.8,
                            'value': taxa_aprovacao
                        }
                    }
                ))
                
                # Adicionando um triângulo (Seta direcional) via layout annotation
                # O gauge em Plotly é polar, então criamos uma agulha via SVG path
                import math
                r = 0.5
                theta = (1 - taxa_aprovacao / 100) * math.pi
                x_head = 0.5 + r * math.cos(theta)
                y_head = 0.2 + r * math.sin(theta)
                
                fig_gauge.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=280,
                    margin=dict(l=30, r=30, t=30, b=10),
                    # Agulha do velocímetro desenhada com SVG
                    shapes=[
                        go.layout.Shape(
                            type="path",
                            path=f"M 0.5 0.2 L {x_head} {y_head} L 0.5 0.2 Z",
                            fillcolor="white",
                            line_color="white",
                            line_width=4
                        )
                    ]
                )
                st.plotly_chart(fig_gauge, use_container_width=True)

            with col_chart_kb:
                st.markdown("#### 🧠 Saúde da Base de Conhecimento")
                # Distinguimos o que é Calibragem (tem rascunho IA) do que é Ouro puro (Manual)
                num_calib = len(df_fb) if not df_fb.empty else 0
                num_ouro_puro = total_ouro - num_calib
                
                kb_data = {
                    "Componente": ["Fonética", "Estrutura", "Calibragem", "Roteiro Ouro", "Persona", "Nuances", "Imagens"],
                    "Registros": [len(df_fon), len(df_est), num_calib, num_ouro_puro, len(df_pers), len(df_nuan), len(df_img)]
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
                st.markdown("#### 📈 Evolução de Produção & Qualidade")
                if not df_hist_dash.empty and 'criado_em' in df_hist_dash.columns:
                    # Need safe parsing here too!
                    def parse_date_only(v):
                        try:
                            if isinstance(v, str) and "às" in v:
                                return pd.to_datetime(v, format='%d/%m/%y às %H:%M').date()
                            return pd.to_datetime(v, utc=True).tz_convert('America/Sao_Paulo').date()
                        except: return pd.NaT

                    df_timeline = df_hist_dash.copy()
                    df_timeline['data'] = df_timeline['criado_em'].apply(parse_date_only)
                    vol_data = df_timeline.groupby('data').size().reset_index(name='Volume')
                    
                    # Preparação de dados de qualidade (se houver ouro)
                    if not df_ouro.empty:
                        df_q = df_ouro.copy()
                        df_q['data'] = df_q['criado_em'].apply(parse_date_only)
                        qual_data = df_q.groupby('data')['nota_percentual'].mean().reset_index(name='Qualidade')
                        chart_merged = pd.merge(vol_data, qual_data, on='data', how='left').fillna(0)
                    else:
                        chart_merged = vol_data
                        chart_merged['Qualidade'] = 0
                    
                    # Gráfico Combinado
                    fig_evol = go.Figure()
                    
                    # Barras de Volume
                    fig_evol.add_trace(go.Bar(
                        x=chart_merged['data'], y=chart_merged['Volume'],
                        name="Volume", marker_color='rgba(0, 134, 255, 0.3)',
                        yaxis='y'
                    ))
                    
                    # Linha de Qualidade
                    fig_evol.add_trace(go.Scatter(
                        x=chart_merged['data'], y=chart_merged['Qualidade'],
                        name="Qualidade (%)", mode='lines+markers',
                        line=dict(color='#10b981', width=3),
                        marker=dict(size=8, color='#10b981', line=dict(width=2, color='white')),
                        yaxis='y2'
                    ))
                    
                    fig_evol.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        height=350,
                        margin=dict(l=10, r=10, t=30, b=20),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        yaxis=dict(title="Volume (UN)", showgrid=False),
                        yaxis2=dict(title="Qualidade (%)", overlaying='y', side='right', range=[0, 105], showgrid=True, gridcolor='rgba(255,255,255,0.05)')
                    )
                    st.plotly_chart(fig_evol, use_container_width=True)
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
            tab_hist, tab_ouro, tab_feed, tab_est_dash, tab_nuan, tab_img_dash, tab_pers, tab_fon = st.tabs(["💵 Histórico", "🏆 Roteiros Ouro", "⚖️ Feedbacks", "🏗️ Estruturas", "🧠 Nuances", "📸 Imagens", "💃 Persona", "🗣️ Fonética"])
            
            # Data format safe parser
            def safe_format_date(val):
                try:
                    return pd.to_datetime(val, utc=True).tz_convert('America/Sao_Paulo').strftime('%d/%m/%y às %H:%M')
                except:
                    return val

            with tab_hist:
                if not df_hist_dash.empty:
                    df_show_hist = df_hist_dash.copy()
                    
                    # Formatação de colunas
                    if 'criado_em' in df_show_hist.columns:
                        df_show_hist['criado_em'] = df_show_hist['criado_em'].apply(safe_format_date)
                        
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
            
            with tab_est_dash:
                if not df_est.empty:
                    df_e = df_est.copy()
                    if 'criado_em' in df_e.columns:
                        df_e['criado_em'] = df_e['criado_em'].apply(safe_format_date)
                    available_cols = [c for c in ['criado_em', 'tipo_estrutura', 'texto_ia_rejeitado', 'texto_ouro', 'aprendizado'] if c in df_e.columns]
                    st.dataframe(df_e[available_cols].sort_values(by='criado_em', ascending=False), use_container_width=True)
                else:
                    st.info("Nenhuma estrutura cadastrada.")
            
            with tab_nuan:
                if not df_nuan.empty:
                    df_n = df_nuan.copy()
                    if 'criado_em' in df_n.columns:
                        df_n['criado_em'] = df_n['criado_em'].apply(safe_format_date)
                    st.dataframe(df_n[['criado_em', 'frase_ia', 'analise_critica', 'exemplo_ouro']].sort_values(by='criado_em', ascending=False), use_container_width=True)
                else:
                    st.info("Nenhuma nuance de linguagem cadastrada.")
            
            with tab_img_dash:
                if not df_img.empty:
                    df_i = df_img.copy()
                    if 'criado_em' in df_i.columns:
                        df_i['criado_em'] = df_i['criado_em'].apply(safe_format_date)
                    st.dataframe(df_i[['criado_em', 'codigo_produto', 'descricao_ia', 'descricao_humano', 'aprendizado']].sort_values(by='criado_em', ascending=False), use_container_width=True)
                else:
                    st.info("Nenhuma calibragem de imagem cadastrada.")
            
            with tab_ouro:
                if not df_ouro.empty:
                    df_o = df_ouro.copy()
                    if 'categoria_id' in df_o.columns and not df_cats.empty:
                        cat_map_names = dict(zip(df_cats['id'], df_cats['nome']))
                        df_o['Categoria'] = df_o['categoria_id'].map(cat_map_names)
                    
                    if 'criado_em' in df_o.columns:
                        df_o['criado_em'] = df_o['criado_em'].apply(safe_format_date)
                    
                    cols_o = ['criado_em', 'Categoria', 'titulo_produto', 'roteiro_perfeito']
                    available_o = [c for c in cols_o if c in df_o.columns]
                    st.dataframe(df_o[available_o].sort_values(by='criado_em', ascending=False), use_container_width=True)
                else:
                    st.info("Nenhum Roteiro Ouro cadastrado.")
            
            with tab_feed:
                if not df_fb.empty:
                    df_f = df_fb.copy()
                    if 'criado_em' in df_f.columns:
                        df_f['criado_em'] = df_f['criado_em'].apply(safe_format_date)
                    # Colunas do novo sistema de calibragem
                    available_cols = [c for c in ['criado_em', 'estrela', 'categoria', 'modelo_calibragem', 'aprendizado', 'roteiro_original_ia', 'roteiro_perfeito'] if c in df_f.columns]
                    st.dataframe(df_f[available_cols].sort_values(by='criado_em', ascending=False), use_container_width=True)
                else:
                    st.info("Nenhuma calibração realizada ainda.")
            
            with tab_pers:
                if not df_pers.empty:
                    df_p = df_pers.copy()
                    df_p = df_pers.copy()
                    if 'criado_em' in df_p.columns:
                        df_p['criado_em'] = df_p['criado_em'].apply(safe_format_date)
                    st.dataframe(df_p[['criado_em', 'pilar_persona', 'texto_gerado_ia', 'texto_corrigido_humano', 'lexico_sugerido']].sort_values(by='criado_em', ascending=False), use_container_width=True)
                else:
                    st.info("Nenhum ajuste de persona cadastrado.")
                    
            with tab_fon:
                if not df_fon.empty:
                    df_fo = df_fon.copy()
                    if 'criado_em' in df_fo.columns:
                        df_fo['criado_em'] = df_fo['criado_em'].apply(safe_format_date)
                    st.dataframe(df_fo[['criado_em', 'termo_errado', 'termo_corrigido', 'exemplo_no_roteiro']].sort_values(by='criado_em', ascending=False), use_container_width=True)
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
                            d_recent = sp.table(f"{st.session_state.get('table_prefix', 'nw_')}historico_roteiros").select("criado_em, codigo_produto, custo_estimado_brl, modelo_llm").order('criado_em', desc=True).limit(200).execute()
                            if d_recent.data:
                                df = pd.DataFrame(d_recent.data)
                                
                                def parse_date_only(v):
                                    try:
                                        if isinstance(v, str) and "às" in v:
                                            return pd.to_datetime(v, format='%d/%m/%y às %H:%M').date()
                                        return pd.to_datetime(v, utc=True).tz_convert('America/Sao_Paulo').date()
                                    except: return pd.NaT

                                df['data'] = df['criado_em'].apply(parse_date_only)
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
                    model_id=modelo_id,
                    table_prefix=st.session_state.get('table_prefix', 'nw_')
                )
                
                # Fetch response with delay for loading perception
                with st.spinner("Lu está digitando..."):
                    resposta_lu = agent.chat_with_context(prompt, st.session_state.chat_history, context_str)
                
                message_placeholder.markdown(resposta_lu)
                # Add assistant response to chat history
                st.session_state.chat_history.append({"role": "Lu", "content": resposta_lu})
                
            except Exception as e:
                st.error(f"Erro de comunicação com a IA: {e}")
