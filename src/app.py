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
    st.markdown("""
    <div style="display: flex; flex-direction: column; width: 120px; line-height: 1;">
        <span style="color: #0086ff; font-weight: 800; font-size: 14px; letter-spacing: 2px;">MAGALU</span>
        <span style="color: white; font-weight: 400; font-size: 24px; letter-spacing: 0.5px;">AI Suite</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<span style='color: #0086ff; font-weight: bold; font-size: 12px;'>V1.0 SÉRIE 1</span>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""<img src="https://logodownload.org/wp-content/uploads/2014/10/magalu-logo-1.png" width="120" style="margin-bottom: 20px;" />""", unsafe_allow_html=True)
    
    st.markdown("### 🧭 Navegação")
    page = st.radio("Selecione o Módulo", ["Criar Roteiros", "Treinar IA", "Dashboard"])
    
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
                elif not api_key:
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
            linhas_ficha = item['ficha'].split('\n')
            nome_curto = linhas_ficha[0][:20] + "..." if linhas_ficha and len(linhas_ficha[0]) > 20 else (linhas_ficha[0] if linhas_ficha else f"Item {i+1}")
            opcoes_tags.append(f"📦 {codigo} {nome_curto}")
            
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
        linhas = item['ficha'].split('\n')
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
        
        tab_fb, tab_est, tab_fon, tab_ouro = st.tabs(["📉 Calibração (Logs & Comparação)", "💬 Estruturas (Aberturas/Fechamentos)", "🗣️ Fonética", "🏆 Roteiros Ouro"])
        
        with tab_fb:
            st.markdown("### 📉 Tabela Comparativa (IA vs Aprovados pelo Breno)")
            res_fb = sp_client.table("feedback_roteiros").select("*").execute()
            df_fb = pd.DataFrame(res_fb.data if hasattr(res_fb, 'data') else [])
            if not df_fb.empty:
                st.dataframe(df_fb[['criado_em', 'avaliacao', 'roteiro_original_ia', 'roteiro_final_humano']], use_container_width=True)
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
            st.markdown("🗣️ **Treinar Fonética**")
            t_err = st.text_input("Como a IA escreveu:", placeholder="Ex: 5G", key=f"te_{idx}")
            t_cor = st.text_input("Como a locução final deve ser (aprovada):", placeholder="Ex: cinco gê", key=f"tc_{idx}")
            if st.button("🔊 Enviar Regra Fonética", key=f"btn_fon_{idx}", use_container_width=True, type="primary"):
                salvar_fonetica(sp_client, t_err, t_cor, "")
            
            st.divider()
            res_fon = sp_client.table("treinamento_fonetica").select("*").execute()
            df_fon = pd.DataFrame(res_fon.data if hasattr(res_fon, 'data') else [])
            if not df_fon.empty:
                st.dataframe(df_fon[['termo_errado', 'termo_corrigido', 'criado_em']], use_container_width=True)
        
        with tab_ouro:
            st.markdown("### 🏆 Hall da Fama (Roteiros Ouro)")
            t_prod = st.text_input("Produto:")
            t_rot = st.text_area("Roteiro Finalizado:")
            if st.button("Cadastrar Roteiro Ouro", type="primary"):
                salvar_ouro(sp_client, 1, t_prod, t_rot)
            
            st.divider()
            res_ouro = sp_client.table("roteiros_ouro").select("*").execute()
            df_ouro = pd.DataFrame(res_ouro.data if hasattr(res_ouro, 'data') else [])
            if not df_ouro.empty:
                st.dataframe(df_ouro[['titulo_produto', 'roteiro_perfeito']], use_container_width=True)

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
