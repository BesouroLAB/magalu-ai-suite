import streamlit as st
import os
import sys
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.agent import RoteiristaAgent
from src.scraper import scrape_with_gemini, parse_codes
from src.exporter import export_roteiro_docx, format_for_display, export_all_roteiros_zip

load_dotenv()

# --- CONFIGURAÇÃO GERAL ---
st.set_page_config(page_title="Magalu AI Suite", page_icon="🛍️", layout="wide", initial_sidebar_state="expanded")

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
    
    .stApp > header { background-color: transparent; }
    .stApp { background-color: var(--bg-main) !important; color: var(--text-primary) !important; }

    h1, h2, h3, p, span, div { color: var(--text-primary) !important; font-family: 'Inter', sans-serif; }
    .stMarkdown, .stText { color: var(--text-muted) !important; }
    
    .stTextArea > div > div > textarea, .stTextInput > div > div > input, .stSelectbox > div > div > div {
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid #2A3241 !important;
        border-radius: 8px;
    }
    .stTextArea > div > div > textarea:focus, .stTextInput > div > div > input:focus {
        border-color: var(--mglu-blue) !important;
        box-shadow: 0 0 0 1px var(--mglu-blue) !important;
    }
    
    .stButton > button[data-baseweb="button"] {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    /* Botões Primários */
    button[kind="primary"] {
        background-color: var(--mglu-purple) !important;
        color: white !important;
        border: none !important;
    }
    button[kind="primary"]:hover {
        background-color: #6a35d6 !important;
        transform: scale(1.02) !important;
    }
    
    /* Botões Secundários */
    button[kind="secondary"] {
        background-color: #2A3241 !important;
        color: var(--text-primary) !important;
        border: 1px solid #3d4659 !important;
    }
    button[kind="secondary"]:hover {
        background-color: #3d4659 !important;
        border-color: var(--mglu-blue) !important;
    }
    
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
    
    [data-testid="stSidebar"] {
        background-color: var(--bg-card) !important;
        border-right: 1px solid #2A3241;
    }
    
    .block-container { padding-top: 2rem; }
</style>
"""
st.markdown(DARK_MODE_CSS, unsafe_allow_html=True)


# --- FUNÇÕES SUPABASE ---
def init_supabase():
    url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")
    if url and key:
        return create_client(url, key)
    return None

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


# --- SIDEBAR E NAVEGAÇÃO ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Magalu_2019_logo.svg/500px-Magalu_2019_logo.svg.png", width=150)
    
    st.markdown("### 🧭 Navegação")
    page = st.radio("Selecione o Módulo", ["Estúdio de Criação", "Dashboard de Inteligência"])
    
    st.divider()
    
    st.markdown("### ⚙️ Configurações API")
    api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    supabase_client = init_supabase()
    
    if not api_key:
        api_key_input = st.text_input("🔑 Cole sua chave Gemini:", type="password")
        if st.button("Salvar Chave Gemini"):
            with open('.env', 'a', encoding='utf-8') as f:
                f.write(f"\nGEMINI_API_KEY={api_key_input}")
            os.environ["GEMINI_API_KEY"] = api_key_input
            st.success("Salva! Pressione F5.")
            st.stop()
    else:
        st.success("🟢 API Gemini Conectada")

    if not supabase_client:
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
        st.session_state['supabase_client'] = supabase_client
        st.success("🟢 Nuvem Conectada (Supabase)")


# --- APLICAÇÃO PRINCIPAL ---
st.title("Magalu AI Suite")
st.markdown("<span style='color: #0086ff; font-weight: bold; font-size: 14px; margin-left: 10px'>V1.0 SÉRIE 1 (Fábrica de Inteligência)</span>", unsafe_allow_html=True)


# --- PÁGINA 1: ESTÚDIO DE CRIAÇÃO ---
if page == "Estúdio de Criação":
    col_left, col_right = st.columns([1.2, 2.5], gap="medium")

    with col_left:
        st.subheader("Novo Roteiro")
        
        # Categoria padrão
        cat_selecionada_id = 1

        # Modo de entrada: Código do Produto ou Ficha Manual
        modo_entrada = st.toggle("📝 Modo Manual (colar ficha técnica)", value=False)

        if not modo_entrada:
            # --- MODO CÓDIGO DE PRODUTO (PADRÃO) ---
            st.markdown("<p style='font-size: 14px; color: #8b92a5'>Digite os códigos dos produtos Magalu (um por linha ou separados por vírgula):</p>", unsafe_allow_html=True)
            
            codigos_raw = st.text_area(
                "Códigos dos Produtos",
                height=150,
                placeholder="Ex:\n240304700\n240305700\n237060600",
                key="codigos_input"
            )
            
            st.caption("💡 O código fica na URL do produto: magazineluiza.com.br/.../p/**240304700**/...")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("🚀 Gerar Roteiros Mágicos", use_container_width=True, type="primary"):
                codigos = parse_codes(codigos_raw) if codigos_raw else []
                
                if not codigos:
                    st.warning("⚠️ Digite pelo menos um código de produto.")
                elif not api_key:
                    st.warning("⚠️ Forneça uma chave da API do Gemini no painel.")
                else:
                    try:
                        agent = RoteiristaAgent(supabase_client=st.session_state.get('supabase_client'))
                        roteiros = []
                        
                        progress = st.progress(0, text="Iniciando extração...")
                        
                        for i, code in enumerate(codigos):
                            progress.progress(
                                (i) / len(codigos),
                                text=f"🔍 Extraindo dados do produto {code}... ({i+1}/{len(codigos)})"
                            )
                            
                            # 1. Gemini extrai dados do produto via URL
                            ficha_extraida = scrape_with_gemini(code)
                            
                            progress.progress(
                                (i + 0.5) / len(codigos),
                                text=f"✍️ Gerando roteiro para {code}... ({i+1}/{len(codigos)})"
                            )
                            
                            # 2. Gera o roteiro com os dados extraídos
                            roteiro = agent.gerar_roteiro(ficha_extraida)
                            roteiros.append({
                                "ficha": ficha_extraida,
                                "roteiro_original": roteiro,
                                "categoria_id": cat_selecionada_id,
                                "codigo": code
                            })
                        
                        progress.progress(1.0, text="✅ Concluído!")
                        st.session_state['roteiros'] = roteiros
                        
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
                    height=150,
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
                        except Exception as e:
                            st.error(f"Erro na geração: {e}")

    with col_right:
        st.subheader("Mesa de Trabalho")
        
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
            
            for idx, item in enumerate(st.session_state['roteiros']):
                linhas = item['ficha'].split('\n')
                titulo_curto = linhas[0][:60] if linhas else f"Produto {idx+1}"
                cat_id_roteiro = item.get("categoria_id", cat_selecionada_id)
                codigo_produto = item.get("codigo", "")

                with st.expander(f"📦 {titulo_curto}", expanded=True):
                    tab_view, tab_edit = st.tabs(["👁️ Roteiro Formatado", "✏️ Editor (Markdown)"])

                    with tab_view:
                        # Exibe roteiro formatado: bold nas locuções, normal nas imagens
                        formatted = format_for_display(item['roteiro_original'])
                        st.markdown(f"<div style='background-color: var(--bg-card); padding: 20px; border-radius: 8px; border: 1px solid #2A3241; line-height: 1.8; font-family: Tahoma, sans-serif;'>{formatted}</div>", unsafe_allow_html=True)
                        
                        # Botão de exportar DOCX
                        st.markdown("<br>", unsafe_allow_html=True)
                        docx_bytes, docx_filename = export_roteiro_docx(
                            item['roteiro_original'],
                            code=codigo_produto,
                            product_name=titulo_curto,
                            selected_month=mes_selecionado
                        )
                        st.download_button(
                            label="📥 Exportar .docx",
                            data=docx_bytes,
                            file_name=docx_filename,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"export_{idx}",
                            use_container_width=True,
                            type="primary"
                        )

                    with tab_edit:
                        edited = st.text_area(
                            "Ajuste fino. Preserva Markdown para cópia.",
                            value=item['roteiro_original'],
                            height=250,
                            key=f"editor_{idx}"
                        )
                        
                        edited_val = st.session_state.get(f"editor_{idx}", item['roteiro_original'])
                        sp_cli = st.session_state.get('supabase_client', None)
                        
                        # Botão de exportar (versão editada)
                        docx_edited_bytes, docx_edited_fn = export_roteiro_docx(
                            edited_val,
                            code=codigo_produto,
                            product_name=titulo_curto,
                            selected_month=mes_selecionado
                        )
                        st.download_button(
                            label="📥 Exportar Editado .docx",
                            data=docx_edited_bytes,
                            file_name=docx_edited_fn,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"export_edit_{idx}",
                            use_container_width=True
                        )
                        
                        st.divider()
                        st.caption("Ações Rápidas de Aprendizado:")
                        c1, c2, c3, c4, c5 = st.columns(5)
                        
                        with c1:
                            if st.button("📋 Copiar", key=f"copy_{idx}", use_container_width=True, type="secondary"):
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
                                
                        with c5:
                            with st.popover("🧠 Treinar", use_container_width=True):
                                st.markdown("🔥 **Treinar Persona**")
                                pilar_opc = st.selectbox("Qual pilar foi ajustado?", ["Acessível e Didática", "Empática e Conectada", "Positiva e Inspiradora", "Engajada e Consciente", "Estilo/Tom Geral"], key=f"pilar_{idx}")
                                lex_opc = st.text_input("Gíria/Léxico sugerido:", placeholder="Ex: mara, partiu", key=f"lex_{idx}")
                                erro_opc = st.text_input("Erro que ela cometeu:", placeholder="Ex: Excesso de formalidade", key=f"err_{idx}")
                                if st.button("💃 Enviar Ajuste de Persona", key=f"btn_pers_{idx}", use_container_width=True, type="primary"):
                                    salvar_persona(sp_cli, pilar_opc, item['roteiro_original'], edited_val, lex_opc, erro_opc)
                                
                                st.divider()
                                
                                st.markdown("🗣️ **Treinar Fonética**")
                                t_err = st.text_input("Como a IA escreveu:", placeholder="Ex: 5G", key=f"te_{idx}")
                                t_cor = st.text_input("Como o Breno (Humano) corrigiria:", placeholder="Ex: cinco gê", key=f"tc_{idx}")
                                if st.button("🔊 Enviar Regra Fonética", key=f"btn_fon_{idx}", use_container_width=True, type="primary"):
                                    salvar_fonetica(sp_cli, t_err, t_cor, edited_val)

            st.divider()
            if st.button("🗑️ Limpar Mesa de Trabalho", use_container_width=True, type="secondary"):
                del st.session_state['roteiros']
                st.rerun()
        else:
            st.markdown(
                """
                <div style='display: flex; height: 450px; align-items: center; justify-content: center; border: 2px dashed #2A3241; border-radius: 8px; color: #8b92a5; text-align: center; padding: 20px'>
                Cole a ficha técnica no painel esquerdo e clique em Gerar.<br><br>
                Os roteiros aparecerão aqui prontos para calibração, treino da IA ou envio para Ouro!
                </div>
                """, 
                unsafe_allow_html=True
            )



# --- PÁGINA 2: DASHBOARD DE INTELIGÊNCIA ---
elif page == "Dashboard de Inteligência":
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
            
            fb_data = res_fb.data if hasattr(res_fb, 'data') else []
            ouro_data = res_ouro.data if hasattr(res_ouro, 'data') else []
            pers_data = res_pers.data if hasattr(res_pers, 'data') else []
            fon_data = res_fon.data if hasattr(res_fon, 'data') else []
            cats_dict = {c['id']: c['nome'] for c in res_cats.data} if hasattr(res_cats, 'data') else {}
            
            df_fb = pd.DataFrame(fb_data)
            df_ouro = pd.DataFrame(ouro_data)
            df_pers = pd.DataFrame(pers_data)
            df_fon = pd.DataFrame(fon_data)
            
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
            
            tab_ouro, tab_feed, tab_pers, tab_fon = st.tabs(["🏆 Roteiros Ouro", "📉 Feedbacks", "💃 Persona", "🗣️ Fonética"])
            
            with tab_ouro:
                st.markdown("### 🏆 Referências Premium")
                if not df_ouro.empty:
                    st.dataframe(df_ouro[['criado_em', 'categoria', 'titulo_produto', 'roteiro_perfeito']].sort_values(by='criado_em', ascending=False), use_container_width=True)
                else:
                    st.info("Nenhum Roteiro Ouro cadastrado.")
            
            with tab_feed:
                st.markdown("### 📉 Logs de Feedback")
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
