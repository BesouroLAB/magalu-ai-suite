import os
import json
import glob
import google.generativeai as genai_v1
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
# Tabela de preços por 1M tokens (USD)
PRICING_USD_PER_1M = {
    "gemini-3.1-pro-preview":   {"input": 3.50, "output": 10.50},
    "gemini-3-flash-preview":   {"input": 0.70, "output": 2.10},
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    # Modelos gratuitos (via Puter, OpenRouter, Z.ai, Kimi)
    "gpt-4o-mini": {"input": 0.00, "output": 0.00},
    "x-ai/grok-4-1-fast": {"input": 0.00, "output": 0.00},
    "moonshot-v1-8k": {"input": 0.00, "output": 0.00},
    "glm-4.5-flash": {"input": 0.00, "output": 0.00},
    "deepseek/deepseek-r1-0528:free": {"input": 0.00, "output": 0.00},
    "google/gemma-3-27b:free": {"input": 0.00, "output": 0.00},
    "meta-llama/llama-4-scout:free": {"input": 0.00, "output": 0.00},
    "meta-llama/llama-3.1-70b-instruct": {"input": 0.00, "output": 0.00},
    "claude-3-5-sonnet": {"input": 0.00, "output": 0.00},
}
USD_TO_BRL = 5.80

MODELOS_DISPONIVEIS = {
    "🚀 Gemini 3 Flash Preview [PAGO] — ~R$0,02/roteiro": "gemini-3-flash-preview",
    "👑 Gemini 3.1 Pro Preview [PAGO] — ~R$0,19/roteiro": "gemini-3.1-pro-preview",
    "💰 Gemini 2.5 Flash-Lite [PAGO] — ~R$0,005/roteiro": "gemini-2.5-flash-lite",
    "🔥 Grok 4.1 Fast [GRÁTIS] — Criativo (Puter)": "puter/x-ai/grok-4-1-fast",
    "🤖 GPT-4o Mini [GRÁTIS] — Fluído (Puter)": "puter/gpt-4o-mini",
    "🇨🇳 GLM-4.5 Flash [GRÁTIS] — Ficha Técnica (Z.ai)": "zai/glm-4.5-flash"
}

MODELOS_DESCRICAO = {
    "gemini-3.1-pro-preview": "[O SUPERIOR] (Fev/2026) Inteligência de ponta absoluta. Melhor estruturação, obediência de formatação e raciocínio hiper avançado. Perfeito para 3D. Custo: ~R$ 0,19.",
    "gemini-3-flash-preview": "[O ÁGIL] (Dez/2025) Rápido e muito preciso na interpretação. Versão ultra-otimizada. Custo: ~R$ 0,02.",
    "gemini-2.5-flash-lite": "[CUSTO-BENEFÍCIO] (2025) Barato e rápido. Ótimo com fonética e resume bem as cenas sem perder a essência. Custo: ~R$ 0,005.",
    "puter/gpt-4o-mini": "[O DESOBEDIENTE] (2024) Bom nos benefícios, mas costuma quebrar regras de cabeçalho e errar pronúncias. Use como estepe.",
    "puter/x-ai/grok-4-1-fast": "[O VENCEDOR / O HUMANO] (2025) O meio termo perfeito. Transforma dados frios em textos diretos, dinâmicos e naturais para a Lu. Prioridade gratuita.",
    "zai/glm-4.5-flash": "[LENTO E PRECISO] (2025) Não alucina. Excelente para fichas ultra-técnicas (ferramentas), mas a sua lentidão inviabiliza lotes grandes."
}
PROVIDER_KEY_MAP = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "puter": "PUTER_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "zai": "ZAI_API_KEY",
    "kimi": "KIMI_API_KEY",
}

def calcular_custo_brl(model_id, tokens_in, tokens_out):
    """Calcula o custo estimado em BRL com base nos tokens consumidos."""
    pricing = PRICING_USD_PER_1M.get(model_id, PRICING_USD_PER_1M["gemini-3-flash-preview"])
    custo_usd = (tokens_in / 1_000_000 * pricing["input"]) + (tokens_out / 1_000_000 * pricing["output"])
    return round(custo_usd * USD_TO_BRL, 6)

class RoteiristaAgent:
    def __init__(self, supabase_client=None, model_id="gemini-3-flash-preview", table_prefix="nw_"):
        self.model_id = model_id
        self.table_prefix = table_prefix
        self.supabase = supabase_client
        self.client_gemini = None
        self.client_openai = None
        self.provider = "gemini"

        if self.model_id.startswith("gemini"):
            self.provider = "gemini"
            api_key = os.environ.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY não encontrada!")
            genai_v1.configure(api_key=api_key)
            self.client_gemini = genai_v1.GenerativeModel(self.model_id)
        elif self.model_id.startswith("puter/"):
            self.provider = "puter"
            puter_key = os.environ.get("PUTER_API_KEY")
            if not puter_key:
                raise ValueError("PUTER_API_KEY não encontrada!")
            self.client_openai = OpenAI(
                api_key=puter_key,
                base_url="https://api.puter.com/puterai/openai/v1/"
            )
            self.model_id = self.model_id.replace("puter/", "")
        elif self.model_id.startswith("openai/"):
            self.provider = "openai"
            openai_key = os.environ.get("OPENAI_API_KEY")
            if not openai_key:
                raise ValueError("OPENAI_API_KEY não encontrada!")
            self.client_openai = OpenAI(api_key=openai_key)
            self.model_id = self.model_id.replace("openai/", "")
        elif self.model_id.startswith("openrouter/"):
            self.provider = "openrouter"
            or_key = os.environ.get("OPENROUTER_API_KEY")
            if not or_key:
                raise ValueError("OPENROUTER_API_KEY não encontrada!")
            self.client_openai = OpenAI(
                api_key=or_key,
                base_url="https://openrouter.ai/api/v1"
            )
            self.model_id = self.model_id.replace("openrouter/", "")
        elif self.model_id.startswith("puter/"):
            self.provider = "puter"
            puter_key = os.environ.get("PUTER_API_KEY")
            if not puter_key:
                raise ValueError("PUTER_API_KEY não encontrada!")
            self.client_openai = OpenAI(
                api_key=puter_key,
                base_url="https://api.puter.com/puterai/openai/v1/"
            )
            self.model_id = self.model_id.replace("puter/", "")
        elif self.model_id.startswith("zai/"):
            self.provider = "zai"
            zai_key = os.environ.get("ZAI_API_KEY")
            if not zai_key:
                raise ValueError("ZAI_API_KEY não encontrada!")
            self.client_openai = OpenAI(
                api_key=zai_key,
                base_url="https://api.z.ai/api/paas/v4/"
            )
            self.model_id = self.model_id.replace("zai/", "")
        elif self.model_id.startswith("kimi/"):
            self.provider = "kimi"
            kimi_key = os.environ.get("KIMI_API_KEY")
            if not kimi_key:
                raise ValueError("KIMI_API_KEY não encontrada!")
            self.client_openai = OpenAI(
                api_key=kimi_key,
                base_url="https://api.moonshot.ai/v1"
            )
            self.model_id = self.model_id.replace("kimi/", "")

        # Carrega toda a base de conhecimento estática (Apenas prompts e fonética base)
        self.system_prompt = self._load_file(
            os.path.join(PROJECT_ROOT, ".agents", "system_prompt.txt"), ""
        )
        self.phonetics = self._load_json(
            os.path.join(PROJECT_ROOT, "kb", "phonetics.json"), {}
        )
        # Ouro e Calibragem agora são 100% dinâmicos via Supabase
        self.few_shot_examples = [] 
        
        # Carrega documentos de contexto (.md) da KB
        self.context_docs = self._load_all_md_from_kb()

    def _load_file(self, filepath, fallback):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return fallback

    def _load_json(self, filepath, fallback):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return fallback

    def _load_all_md_from_kb(self):
        """Carrega todos os .md da pasta kb/ como contexto estratégico."""
        docs = []
        kb_path = os.path.join(PROJECT_ROOT, "kb")
        for md_file in glob.glob(os.path.join(kb_path, "*.md")):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Limita cada doc a 4000 chars para não estourar o contexto
                    docs.append(content[:4000])
            except Exception:
                pass
        return docs

    def _fetch_supabase_context(self):
        """Busca aprendizado dinâmico no Supabase."""
        sb_parts = []
        if not self.supabase:
            return ""
        
        try:
            # 1. Roteiros Ouro (O "Norte" da Redação - Exemplos de Elite)
            res_ouro = self.supabase.table(f"{self.table_prefix}roteiros_ouro").select("*").order('criado_em', desc=True).limit(5).execute()
            if res_ouro.data:
                sb_parts.append("\n**REFERÊNCIAS DE ELITE (ESTE É O PADRÃO OURO A SER SEGUIDO):**")
                for r in res_ouro.data:
                    sb_parts.append(f"- Produto: {r['titulo_produto']}\n  Roteiro Perfeito (Target): {r['roteiro_perfeito']}")

            # 2. Ajustes de Persona (SHARED)
            res_pers = self.supabase.table("nw_treinamento_persona_lu").select("*").limit(5).execute()
            if res_pers.data:
                sb_parts.append("\n**AJUSTES DE PERSONA (LIÇÕES APRENDIDAS):**")
                for p in res_pers.data:
                    sb_parts.append(f"- Pilar: {p['pilar_persona']}\n  Erro Anterior: {p['erro_cometido']}\n  Correção Master: {p['texto_corrigido_humano']}")

            # 3. Novas Regras Fonéticas (SHARED ACROSS MODES)
            res_fon = self.supabase.table("nw_treinamento_fonetica").select("*").execute()
            if res_fon.data:
                sb_parts.append("\n**NOVAS REGRAS DE FONÉTICA (OBRIGATÓRIO):**")
                for f in res_fon.data:
                    sb_parts.append(f"- {f['termo_errado']} -> ({f['termo_corrigido']})")
                    
            # 4. Estruturas Aprovadas (Aberturas e Fechamentos/CTAs)
            res_est = self.supabase.table(f"{self.table_prefix}treinamento_estruturas").select("*").execute()
            if res_est.data:
                sb_parts.append("\n**ESTRUTURAS APROVADAS PARA INSPIRAÇÃO (HOOKS E CTAs):**")
                for est in res_est.data:
                    sb_parts.append(f"- [{est['tipo_estrutura']}] {est['texto_ouro']}")
                    
            # 5. Nuances de Linguagem (O que evitar e como melhorar)
            res_nuan = self.supabase.table(f"{self.table_prefix}treinamento_nuances").select("*").limit(5).order('criado_em', desc=True).execute()
            if res_nuan.data:
                sb_parts.append("\n**NUANCES E REFINAMENTO DE ESTILO (LIÇÕES DE REDAÇÃO):**")
                for n in res_nuan.data:
                    refinamento = f"- EVITE: '{n['frase_ia']}'\n  POR QUE: {n['analise_critica']}"
                    if n.get('exemplo_ouro'):
                        refinamento += f"\n  FORMA IDEAL: '{n['exemplo_ouro']}'"
                    sb_parts.append(refinamento)

            # 6. Memória de Calibragem (Lições Recentes da Calibragem)
            res_fb = self.supabase.table(f"{self.table_prefix}roteiros_ouro").select("aprendizado").neq("aprendizado", "null").order('criado_em', desc=True).limit(8).execute()
            if res_fb.data:
                valid_mems = [f for f in res_fb.data if f.get('aprendizado') and f['aprendizado'].strip()]
                if valid_mems:
                    sb_parts.append("\n**LIÇÕES RECENTES DA CALIBRAGEM (NÃO REPITA ESTES ERROS):**")
                    for fb in valid_mems:
                        sb_parts.append(f"- {fb['aprendizado']}")

            # 7. Calibragem Visual (Descrição de Imagens)
            res_img = self.supabase.table(f"{self.table_prefix}treinamento_imagens").select("*").limit(5).order('criado_em', desc=True).execute()
            if res_img.data:
                sb_parts.append("\n**DIRETRIZES VISUAIS (COMO DESCREVER IMAGENS):**")
                for img in res_img.data:
                    sb_parts.append(f"- EVITE: '{img['descricao_ia']}'\n  USE PREFERENCIALMENTE: '{img['descricao_humano']}'\n  MOTIVO: {img['aprendizado']}")
        except Exception as e:
            print(f"Error fetching Supabase context: {e}")
            
        return "\n".join(sb_parts)

    def _build_context(self):
        """Monta o contexto completo: Prompt + KB Estratégica + Fonética + Few-Shot + Supabase."""
        parts = []

        # 1. System Prompt (Regras de Ouro do Breno)
        if self.system_prompt:
            parts.append(self.system_prompt)

        # 2. Contexto estratégico do mercado brasileiro e persona Lu
        if self.context_docs:
            parts.append("\n**CONTEXTO ESTRATÉGICO (MERCADO BRASILEIRO E PERSONA LU):**")
            parts.append("Use este conhecimento para adaptar o tom e as referências do roteiro:")
            for doc in self.context_docs:
                parts.append(doc)

        # 3. Dicionário de fonética (Estático)
        if self.phonetics:
            parts.append("\n**DICIONÁRIO DE FONÉTICA BASE (PADRÃO):**")
            for sigla, pronuncia in self.phonetics.items():
                parts.append(f"- {sigla} -> ({pronuncia})")

        # 4. Few-Shot Learning (Estático)
        if self.few_shot_examples:
            parts.append("\n**EXEMPLOS HISTÓRICOS DE REFERÊNCIA:**")
            for ex in self.few_shot_examples:
                parts.append(f"\n--- EXEMPLO: {ex.get('produto', '')} ---")
                parts.append(f"❌ TEXTO IA: {ex.get('output_antes_ia_ruim', '')}")
                parts.append(f"✅ COMO O BRENO QUER: {ex.get('output_depois_breno_aprovado', '')}")

        # 5. Aprendizado em Tempo Real (Supabase)
        supabase_context = self._fetch_supabase_context()
        if supabase_context:
            parts.append(supabase_context)

        return "\n".join(parts)

    def gerar_memoria_calibracao(self, ia_text, breno_text):
        """Analisa a diferença entre o texto da IA e o aprovado, e extrai a 'lição'. Usa fallback multi-provedor."""
        prompt = (
            "Você é um Analista de Redação Publicitária Sênior comparando DUAS versões de um roteiro de vídeo.\n\n"
            "VERSÃO A (Gerada pela IA):\n"
            f"{ia_text}\n\n"
            "VERSÃO B (Aprovada pelo Humano / Breno):\n"
            f"{breno_text}\n\n"
            "Sua tarefa: Não descreva pequenas trocas de palavras. Extraia o PADRÃO TÉCNICO DE ESCRITA que o humano aplicou.\n"
            "Exemplos de padrões: 'Encurtar ganchos iniciais', 'Remover termos técnicos complexos', 'Focar no benefício emocional em vez da ficha técnica', 'Usar tom mais imperativo no fechamento'.\n\n"
            "Responda em NO MÁXIMO 1 frase objetiva (máximo 150 caracteres). "
            "Use o formato estrito: 'PADRÃO OBSERVADO: [descreva a regra técnica de redação aplicada].'\n"
            "NÃO use metáforas. Seja puramente técnico e direto."
        )

        # 🟢 OPÇÃO 1: PUTER (Grok 4.1 Fast — Grátis)
        api_key_puter = os.environ.get("PUTER_API_KEY")
        if api_key_puter:
            try:
                from openai import OpenAI as OpenAIClient
                client = OpenAIClient(api_key=api_key_puter, base_url="https://api.puter.com/puterai/openai/v1/")
                response = client.chat.completions.create(
                    model="x-ai/grok-4-1-fast",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                print("[OK] Memoria de calibragem gerada via Puter (grok-4-1-fast)")
                return response.choices[0].message.content.replace('\n', ' ').strip()
            except Exception as e:
                print(f"[ERROR] Erro Puter Memoria: {e}")

        # 🔵 OPÇÃO 2: OPENROUTER (DeepSeek R1 — Grátis)
        api_key_or = os.environ.get("OPENROUTER_API_KEY")
        if api_key_or:
            try:
                from openai import OpenAI as OpenAIClient
                client = OpenAIClient(api_key=api_key_or, base_url="https://openrouter.ai/api/v1")
                response = client.chat.completions.create(
                    model="deepseek/deepseek-r1-0528:free",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                print("[OK] Memoria de calibragem gerada via OpenRouter (deepseek-r1)")
                return response.choices[0].message.content.replace('\n', ' ').strip()
            except Exception as e:
                print(f"[ERROR] Erro OpenRouter Memoria: {e}")

        # 🟡 OPÇÃO 3: GEMINI (se a key funcionar)
        api_key_gemini = os.environ.get("GEMINI_API_KEY")
        if api_key_gemini:
            try:
                from google.genai import types
                client = genai_v1.Client(api_key=api_key_gemini)
                response = client.models.generate_content(
                    model='gemini-3-flash-preview',
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.3)
                )
                print("[OK] Memoria de calibragem gerada via Gemini (3-flash-preview)")
                return response.text.replace('\n', ' ').strip()
            except Exception as e:
                print(f"[ERROR] Erro Gemini Memoria: {e}")

        return "Erro: Nenhum provedor disponível para gerar memória de calibragem."

    def gerar_roteiro(self, scraped_data, modo_trabalho="NW (NewWeb)", mes="MAR", data_roteiro=None, codigo=None, nome_produto=None, sub_skus=None, video_url=None):
        """Envia a requisição para o Gemini gerar o roteiro. Suporta Multimodal e Modos de Trabalho."""
        context = self._build_context()

        # Verifica se o input tem imagem (novo fluxo do scraper)
        if isinstance(scraped_data, dict):
            text_data = scraped_data.get("text", "")
            images_list = scraped_data.get("images", [])
        else:
            text_data = str(scraped_data)
            images_list = []
            
        # Roteamento básico de Prompt baseado no Modo (Expansão Futura)
        diretriz_modo = f"Crie um roteiro focado no formato padrão NewWeb (descrição rica e completa)."
        
        # INJEÇÃO DAS TÁTICAS NW LU (Mês e Cena Obrigatória)
        if "NW" in modo_trabalho:
            data_str = data_roteiro if data_roteiro else "[DATA_ATUAL]"
            # Garante que o código tenha 9 dígitos (preenche com 0 à direita)
            cod_str = str(codigo).strip() if codigo else "[CÓDIGO_AQUI]"
            if cod_str.isdigit() and len(cod_str) < 9:
                cod_str = cod_str.ljust(9, '0')
            
            sub_skus_str = f" {sub_skus}" if (sub_skus and str(sub_skus).lower() != 'nan') else ""
            video_ref_str = f"\n   {video_url}" if (video_url and str(video_url).lower() != 'nan') else ""
            
            diretriz_modo += (
                f"\n\n🚨 REGRA ABSOLUTA DE FORMATAÇÃO E ESTRUTURA (NW LU):\n"
                f"1. O TEXTO DEVE COMEÇAR COM O CABEÇALHO EXATAMENTE ABAIXO (PROIBIDO COPIAR A DATA OU MÊS DOS EXEMPLOS, USE EXATAMENTE O QUE ESTÁ AQUI):\n"
                f"   Cliente: Magalu\n"
                f"   Roteirista: Tiago Fernandes - Data: {data_str}\n"
                f"   Produto: NW LU {mes} {cod_str}{sub_skus_str} [INSERIR NOME RESUMIDO DO PRODUTO AQUI]{video_ref_str}\n"
                f"2. A CENA 1 (Primeira cena do vídeo) DEVE OBRIGATORIAMENTE mostrar a 'Lu' em ação, interagindo com o produto ou apresentando-o.\n"
                f"3. A partir da CENA 2, CORTE para imagens do produto. REGRA CRÍTICA DE IMAGEM: É ESTRITAMENTE PROIBIDO sugerir ações humanas nas Colunas de Imagem (ex: 'mão segurando o celular', 'pessoa bebendo café', 'cliente usando'). O vídeo NW é feito APENAS com fotos estáticas do fornecedor, animações gráficas (GCs) e recortes do vídeo oficial. IMAGENS 100% LIMPAS DE HUMANOS."
            )

        if "SOCIAL" in modo_trabalho:
            diretriz_modo = f"ATENÇÃO: Este formato é para SOCIAL (Reels/TikTok). O roteiro deve ser EXTREMAMENTE curto, dinâmico e focado em retenção nos primeiros 3 segundos."
        elif "3D" in modo_trabalho:
            diretriz_modo += (
                f"\n\nATENÇÃO: Este formato é para VÍDEO 3D. O estilo de vídeo será feito APENAS com cenas 3D autorais da Magalu. "
                f"Por isso, o roteiro PRECISA ter uma sequência LÓGICA natural, fluida e contínua. NÃO pode ficar 'picotado' "
                f"como o tradicional NewWeb.\nFoque muito em descrever as texturas, cores exatas, reflexos e ângulos de câmera importantes para o time de modelagem."
            )
        elif "Review" in modo_trabalho:
            diretriz_modo += f"\n\nATENÇÃO: Este formato é um REVIEW. Foque em prós, contras, uso prático diário e uma opinião direta para quem vai gravar no estúdio."

        final_prompt = (
            f"{context}\n\n"
            f"**MODO DE TRABALHO SOLICITADO:** {modo_trabalho}\n"
            f"-> {diretriz_modo}\n\n"
            f"**CONTEXTO DO PRODUTO (INPUT TEXTUAL E/OU VISUAL):**\n{text_data}\n\n"
            f"**INSTRUÇÃO FINAL:**\n"
            f"1. Gere o roteiro no FORMATO DE SAÍDA OBRIGATÓRIO.\n"
            f"2. ENCARNE A PERSONA DA LU: Seja acolhedora, direta e prestativa. Siga RIGOROSAMENTE as Regras de Ouro do Estilo Breno e o Contexto Estratégico.\n"
            f"3. Se houverem imagens fornecidas, extraia o máximo de detalhes visuais (cor, textura, design) para enriquecer o roteiro.\n"
            f"4. Imite fielmente o estilo dos exemplos APROVADOS.\n"
            f"5. Use 'pra' no lugar de 'para'. Coloque a marca entre vírgulas.\n"
            f"6. **ENRIQUECIMENTO DE CONTEXTO:** Para produtos mundialmente conhecidos, adicione detalhes técnicos ou curiosidades RELEVANTES que não estejam na ficha, MAS sem alongar o roteiro desnecessariamente.\n"
            f"7. **REGRA FONTE EXTERNA (CRÍTICA):** Se o input contiver uma linha 'FONTE EXTERNA: [URL]', você DEVE OBRIGATORIAMENTE adicionar ao final do seu roteiro uma linha vazia seguida de: 'Fonte Externa: [URL]'.\n"
            f"8. **PROIBIÇÃO DE REDUNDÂNCIA (MUITO IMPORTANTE):** O roteiro deve ser direto e dinâmico. NÃO REPITA o mesmo assunto, benefício ou característica técnica em parágrafos separados de forma desnecessária. Cada cena/fala deve trazer uma informação NOVA.\n"
            f"9. **COMPLETUDE OBJETIVA E SAÚDE:** Seja dinâmico, mas NÃO omita em hipótese alguma diferenciais invisíveis vitais para o consumidor presentes na Ficha Técnica (ex: proteção antiácaro/antimofo/antifungo, antibacteriano, acessórios extras). Transforme essas características essenciais em benefícios claros para a saúde e usabilidade do cliente, sem enrolação.\n"
            f"10. **REGRA DA COMPOSIÇÃO E KITS (ACESSÓRIOS):** Se o produto for um conjunto, kit ou cozinha completa, você DEVE listar explicitamente as peças principais que o compõem (ex: balcão, aéreo, nicho, paneleiro) exatamente como constam no campo 'Composição' ou na descrição, não apenas diga 'é uma cozinha'.\n"
            f"11. **PRONÚNCIA DE ESTRANGEIRISMOS:** Sempre que houver nomes de marcas estrangeiras, tecnologias (Core i7, QLED, OLED, Magsafe) ou palavras difíceis, preveja como um brasileiro falaria e insira a pronúncia em parênteses. Exemplo: OPPO (ó-pô), Reno14 (rê-no quatorze).\n"
            f"12. **PROIBIÇÃO DE SCRIPTS HIPOTÉTICOS:** Se o contexto do produto for insuficiente, NÃO gere roteiro. Responda: 'ERRO: Dados insuficientes do produto para geração automática.'"
        )

        if self.client_gemini:
            contents = [final_prompt]
            if images_list:
                for img_dict in images_list:
                    img_bytes = img_dict.get("bytes")
                    img_mime = img_dict.get("mime")
                    if img_bytes and img_mime:
                        contents.append({
                            "mime_type": img_mime,
                            "data": img_bytes
                        })

            # Chamada via SDK v1
            response = self.client_gemini.generate_content(contents)
            roteiro = response.text
            
            # Métricas via v1
            tokens_in = len(final_prompt) // 4
            tokens_out = len(roteiro) // 4
        
        elif self.client_openai:
            messages = [{"role": "user", "content": final_prompt}]
            # Para modelos OpenAI/Puter, o envio de imagens (vision) tem uma estrutura diferente.
            # Como a documentação primária do Puter para Grok Fast não deixa claro o suporte a imagens,
            # passaremos apenas texto por enquanto, a não ser que o modelo suporte e tenhamos url.
            
            response = self.client_openai.chat.completions.create(
                model=self.model_id,
                messages=messages
            )
            roteiro = response.choices[0].message.content
            
            tokens_in = response.usage.prompt_tokens if hasattr(response, 'usage') else 0
            tokens_out = response.usage.completion_tokens if hasattr(response, 'usage') else 0
        
        else:
            raise Exception("Nenhum cliente LLM configurado válido.")

        # --- POST-PROCESSING ENFORCEMENT ---
        # Força o cabeçalho correto ignorando as alucinações de cópia de exemplos do LLM
        if "NW" in modo_trabalho:
            try:
                import re
                linhas = roteiro.split('\n')
                for i, linha in enumerate(linhas):
                    if "Cliente: Magalu" in linha.replace('*', ''):
                        data_s = data_roteiro if data_roteiro else "[DATA_ATUAL]"
                        cod_s = str(codigo).strip() if codigo else "[CÓDIGO_AQUI]"
                        if cod_s.isdigit() and len(cod_s) < 9: cod_s = cod_s.ljust(9, '0')
                        sub_s = f" {sub_skus}" if (sub_skus and str(sub_skus).lower() != 'nan') else ""
                        vid_s = f"\n   {video_url}" if (video_url and str(video_url).lower() != 'nan') else ""
                        
                        linhas[i] = "Cliente: Magalu"
                        if i + 1 < len(linhas):
                            linhas[i+1] = f"Roteirista: Tiago Fernandes - Data: {data_s}"
                        if i + 2 < len(linhas):
                            prod_str = linhas[i+2].replace('**', '').replace('Produto:', '').strip()
                            nome_purificado = re.sub(r'^(NW\s*(3D)?\s*LU\s*[A-Z]{3}\s*\d+\s+)', '', prod_str)
                            linhas[i+2] = f"Produto: NW LU {mes} {cod_s}{sub_s} {nome_purificado}{vid_s}"
                        roteiro = "\n".join(linhas)
                        break
            except Exception as e:
                print(f"[WARN] Error enforcing header: {e}")

        custo_brl = calcular_custo_brl(self.model_id, tokens_in, tokens_out)

        return {
            "roteiro": roteiro,
            "model_id": self.model_id,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "custo_brl": custo_brl
        }

    def _extract_json(self, text):
        """Extrai JSON de uma resposta que pode conter markdown wrappers (```json ... ```)."""
        import re
        # Tenta parsear direto
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass
        # Tenta extrair de blocos ```json ... ``` ou ``` ... ```
        match = re.search(r'```(?:json)?\s*\n?({.*?})\s*\n?```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        # Tenta encontrar o primeiro { ... } na resposta
        match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Não foi possível extrair JSON da resposta: {text[:200]}")

    def analisar_calibracao(self, original, final, categories_list=[], codigo_original=""):
        """
        Realiza a análise de calibragem de qualidade usando LLMs gratuitos.
        Cadeia de fallback: Puter (Grok 4.1 Fast) → OpenRouter (DeepSeek V3) → Gemini (2.5 Flash).
        """
        # Define um ID de fallback seguro (o primeiro da lista ou 0)
        fallback_id = categories_list[0]['id'] if categories_list else 1
        # Formata a lista de categorias para o prompt
        cat_str = "\n".join([f"- ID {c['id']}: {c['nome']}" for c in categories_list]) if categories_list else "Genérico (ID 1)"

        sys_prompt = (
            "Você é um Editor Sênior de Redação Publicitária e Especialista em Qualidade Magalu.\n"
            "Sua tarefa é realizar uma ANALISE TÉCNICA E CIRÚRGICA da calibragem:\n\n"
            "1. COMPARE o Roteiro Original (IA) com o Roteiro Final (Aprovado pelo Humano).\n"
            "2. CALCULE o SCORE (%) de aproveitamento real seguindo esta RÉGUA ORGÂNICA MAGALU:\n"
            "   - 100%: Perfeito. O humano fez apenas ajustes de formatação, pontuação ou troca de conectivos sem alterar a essência.\n"
            "   - 85% a 95%: Ajustes de Estilo. O humano melhorou a fluidez, encurtou frases ou trocou jargões por termos mais comerciais.\n"
            "   - 60% a 80%: Mudança Estrutural. O humano adicionou informações faltantes, reconstruiu a abertura/fechamento ou cortou blocos inteiros.\n"
            "   - Abaixo de 60%: Erro Grave. A IA errou feio o tom de voz, omitiu funcionalidades vitais ou errou o SKU.\n"
            "   ATENÇÃO: Termos presentes no CÓDIGO SUGERIDO ou NOME DO PRODUTO (ex: 'Aro 26', 'Grau', 'Index') NÃO SÃO ERROS DA IA, não penalize a nota por eles.\n"
            "3. SÍNTESE DE APRENDIZADO (MEMÓRIA TÉCNICA): Transforme as edições do humano em DIRETRIZES TÁTICAS UNIVERSAIS para uma futura IA Redatora.\n"
            "   A diretriz DEVE ser escrita como uma regra de copywriting comercial, não como uma descrição do que aconteceu no produto X ou Y.\n"
            "   - REGRA ANTI-ALUCINAÇÃO E GENERALIZAÇÃO: É ESTRITAMENTE PROIBIDO citar especificações do produto (ex: '85W de potência', 'tela de 6 polegadas') na REGRA EM SI. O produto deve aparecer APENAS dentro de parênteses como o exemplo prático.\n"
            "   - COMECE COM VERBOS IMPERATIVOS: 'Integrar', 'Eliminar', 'Simplificar', 'Encurtar', 'Adotar', 'Reordenar', 'Focar'.\n"
            "   - ERRADO: 'Eliminou 85W de potência mantendo 3 velocidades na cena 1'. (Muito específico, inútil para outros produtos).\n"
            "   - CERTO: '- Remover especificações técnicas iniciais como potência para priorizar features funcionais e benefícios práticos. (Ex: Na abertura, eliminou \"85W de potência\" mantendo \"3 velocidades\").'\n"
            "   - ERRADO: 'Tirou vários modos de funcionamento e colocou várias funções'.\n"
            "3. APRENDIZADO GERAL (TÁTICO): Extraia REGRAS DIRETAS de redação (o que fazer e o que não fazer). "
            "   NUNCA inclua regras visuais, descrições de imagens ou coisas da tela aqui. Jogue essas na regra 10 ('imagens_regras').\n"
            "   Seja curto, grosso e imperativo, mas SEMPRE DÊ O EXEMPLO DO PRODUTO ATUAL DENTRO DE (Ex: ...). Use tópicos com '-'.\n"
            "4. EXTRAIA O CÓDIGO DO PRODUTO (SKU): Procure no texto por sequências numéricas ou o código fornecido.\n"
            "5. CATEGORIZE (CRÍTICO): Escolha a melhor categoria da lista abaixo baseada na FUNÇÃO PRINCIPAL DO PRODUTO. "
            "Não se confunda com funcionalidades extras (ex: um monitor gamer com alto-falante é 'Informatica / Gamer', e NUNCA 'Áudio'). "
            "Leia o texto com atenção para identificar a essência do produto.\n"
            "6. FONÉTICA (AUTO-EXTRAÇÃO): Se houver diferenças entre a IA e o HUMANO na pronúncia (parênteses ex: '(flíker frí)'). "
            "Atenção: 'termo_errado' = EXATAMENTE COMO A IA TINHA ESCRITO (ex: 'New Ortotech' sem pronúncia). 'termo_corrigido' = EXATAMENTE COMO O HUMANO DEIXOU (ex: 'New Ortotech (niu órtotec)'). Cuidado para não inverter quem escreveu o quê! Se não houver, retorne [].\n"
            "7. ESTRUTURAS (GANCHOS E CTAS): EXTRAIA OBRIGATORIAMENTE a Abertura (o Gancho inicial / primeira fala da Lu) e o Fechamento (o CTA final / última fala da Lu) presentes no ROTEIRO FINAL (HUMANO). "
            "Isso é CRÍTICO para termos uma biblioteca de 'Hooks' e 'Call to Actions' aprovados. "
            "Coloque no campo 'estrutura_regras'. Cada regra tem: "
            "'tipo' ('Abertura' ou 'Fechamento') e 'texto_ouro' (a frase exata encontrada no roteiro final). Se nenhuma estrutura for encontrada no roteiro final, retorne [].\n"
            "8. PERSONA LU (AUTO-EXTRAÇÃO): Se o humano corrigiu o TOM DE VOZ, ESTILO ou VOCABULÁRIO da Lu, "
            "extraia como regras no campo 'persona_regras'. Cada regra tem: "
            "'pilar' (tom, vocabulário, gancho, emoção, clareza), 'erro' (o que a IA fez de errado), "
            "'correcao' (como o humano corrigiu) e 'lexico' (palavras-chave ou termos preferíveis identificados na correção). "
            "Se NÃO houver correções de persona, retorne lista vazia [].\n"
            "9. RESUMO ESTRATÉGICO (META-ANÁLISE): No campo 'resumo_estrategico', escreva um parágrafo curto sintetizando a 'Direção Criativa' que o humano está tomando. "
            "Se não houver mudança criativa, escreva 'O roteiro manteve a direção criativa da IA.'\n"
            "10. DESCRIÇÃO DE IMAGENS (VISUAL - ALERTA CRÍTICO): É PROIBIDO COLOCAR FEEDBACKS VISUAIS NO 'aprendizado' DA REGRA 3. "
            "LADO A LADO, compare as linhas que começam com 'Imagem:' na versão da IA e do Humano. "
            "Se o humano detalhou ou alterou os elementos visuais da cena ou da tela, extraia OBRIGATORIAMENTE em 'imagens_regras'. "
            "Cada regra tem: 'antes' (a imagem gerada pela IA), 'depois' (a imagem ditada pelo humano) e 'motivo' (por que o humano mudou a direção de arte/câmera). "
            "SE NÃO EXISTIREM ALTERAÇÕES NAS IMAGENS, retorne uma lista vazia [].\n\n"
            "LISTA DE CATEGORIAS DISPONÍVEIS:\n"
            f"{cat_str}\n\n"
            "🚨 REGRA CRÍTICA DE FORMATAÇÃO DE SAÍDA:\n"
            "Você é um robô de extração de dados Puros. Retorne EXCLUSIVAMENTE o conteúdo JSON abaixo.\n"
            "- NENHUM TEXTO ANTES OU DEPOIS DO JSON.\n"
            "- SEM PENSAMENTOS (tags <think> são proibidas na resposta final).\n"
            "- NÃO use blocos de código markdown (```json ... ```).\n"
            "- Inicie OBRIGATORIAMENTE with { e termine OBRIGATORIAMENTE with }.\n\n"
            "Formato exato:\n"
            "{\n"
            "  \"percentual\": <inteiro 0-100>,\n"
            "  \"aprendizado\": \"<diretrizes táticas de escrita em tópicos>\",\n"
            "  \"resumo_estrategico\": \"<análise da tendência criativa detectada>\",\n"
            "  \"categoria_id\": <id numérico da melhor categoria>,\n"
            "  \"codigo_produto\": \"<código encontrado no texto ou o original>\",\n"
            "  \"fonetica_regras\": [{\"termo_errado\": \"...\", \"termo_corrigido\": \"...\", \"exemplo\": \"...\"}],\n"
            "  \"estrutura_regras\": [{\"tipo\": \"Abertura\", \"texto_ouro\": \"...\"}],\n"
            "  \"persona_regras\": [{\"pilar\": \"...\", \"erro\": \"...\", \"correcao\": \"...\", \"lexico\": \"...\"}],\n"
            "  \"imagens_regras\": [{\"antes\": \"...\", \"depois\": \"...\", \"motivo\": \"...\"}]\n"
            "}"
        )

        user_prompt = f"--- CÓDIGO SUGERIDO ---\n{codigo_original}\n\n--- ROTEIRO ORIGINAL (IA) ---\n{original}\n\n--- ROTEIRO FINAL (HUMANO) ---\n{final}"

        # Usar Gemini 3 Flash Preview como mestre absoluto de Calibragem para todos os cenários
        api_key_gemini = os.environ.get("GEMINI_API_KEY")
        if api_key_gemini:
            try:
                print("[TRY] Tentando calibragem via Gemini (3-flash-preview)...")
                genai_v1.configure(api_key=api_key_gemini)
                model_v1 = genai_v1.GenerativeModel('gemini-3-flash-preview')
                
                # Prompt de sistema + usuário combinados (v1)
                full_prompt = f"{sys_prompt}\n\n{user_prompt}"
                
                response = model_v1.generate_content(
                    full_prompt,
                    generation_config=genai_v1.types.GenerationConfig(
                        temperature=0.1,
                    )
                )
                res = self._extract_json(response.text)
                print("[OK] Calibragem realizada via Gemini (3-flash-preview)")
                return self._process_calib_res(res, fallback_id, categories_list, codigo_original, "Gemini 3 Flash Preview (via Google)")
            except Exception as e:
                print(f"[ERROR] Erro Gemini Calibragem: {e}")

        print("[CRITICAL ERROR] FALHA TOTAL: Nenhum provedor de IA conseguiu realizar a calibragem.")
        return {"percentual": 50, "aprendizado": "Erro: Nenhum provedor de IA disponível para calibragem.", "categoria_id": fallback_id, "codigo_produto": codigo_original, "modelo_calibragem": "N/A", "fonetica_regras": [], "estrutura_regras": [], "persona_regras": []}

    def _process_calib_res(self, res, fallback_id, categories_list, codigo_original, modelo_calibragem="N/A"):
        """Helper para processar e validar o JSON retornado pelos provedores."""
        # Validação rigorosa do ID de categoria
        returned_id = int(res.get("categoria_id", fallback_id)) if str(res.get("categoria_id")).isdigit() else fallback_id
        valid_ids = [c['id'] for c in categories_list] if categories_list else []
        
        # Se for 1 (antigo default errado) força pra Genérico (77) ou o primeiro válido
        if returned_id == 1 and 1 not in valid_ids:
            final_cat_id = 77 if 77 in valid_ids else (valid_ids[0] if valid_ids else fallback_id)
        else:
            final_cat_id = returned_id if returned_id in valid_ids else fallback_id

        
        import re
        sku_raw = str(res.get("codigo_produto", codigo_original))
        # SKUs Magalu tem EXATAMENTE 9 dígitos. Priorizamos encontrar esses blocos.
        skus_found = re.findall(r'\b\d{9}\b', sku_raw)
        # Se não achar blocos isolados, tenta achar qualquer sequência de 9 dígitos
        if not skus_found:
            skus_found = re.findall(r'\d{9}', sku_raw)
            
        sku_clean = " ".join(skus_found) if skus_found else re.sub(r'\D', '', sku_raw)
        
        return {
            "percentual": int(res.get("percentual", 50)),
            "aprendizado": res.get("aprendizado", "Análise realizada."),
            "categoria_id": final_cat_id,
            "codigo_produto": sku_clean,
            "modelo_calibragem": modelo_calibragem,
            "fonetica_regras": res.get("fonetica_regras", []),
            "estrutura_regras": res.get("estrutura_regras", []),
            "persona_regras": res.get("persona_regras", [])
        }

    def chat_with_context(self, user_query, chat_history=[], supabase_context=None):
        """
        Gera uma resposta conversacional baseada no histórico de chat e,
        opcionalmente, injeta dados recentes do Supabase (RAG-lite) no prompt.
        """
        system_base = (
            "Você é a Lu, a assistente virtual inteligente e especialista em IA da Magalu. "
            "Sua missão é ajudar a equipe interna exclusivamente com: criação de roteiros de vídeo, redação publicitária, análise de qualidade (calibragem) e dúvidas sobre esta suíte de IA. "
            "REGRA DE OURO MÁXIMA: É PROIBIDO responder perguntas fora do contexto da Magalu, tecnologia em varejo, redação ou sobre o sistema de roteiros. Se o assunto sair disso, responda educadamente que você só pode ajudar com demandas de conteúdo da Magalu. "
            "Tenha um tom acolhedor ('estilo magalu'), direto ao ponto, e use emojis ocasionalmente.\n\n"
        )
        
        if supabase_context:
            system_base += f"--- CONTEXTO ATUAL DO BANCO DE DADOS ---\n{supabase_context}\n---------------------------------------\n"

        try:
            if self.provider == "gemini":
                # Para o Gemini (SDK v1), montaremos a interface como um string prompt 
                # contendo o system prompt + histórico + pergunta
                full_prompt = system_base + "\n\n--- HISTÓRICO RECENTE ---\n"
                for msg in chat_history[-6:]: 
                    r = msg.get('role', 'user').upper()
                    c = msg.get('content', '')
                    full_prompt += f"{r}: {c}\n"
                full_prompt += f"\nUSUÁRIO: {user_query}\nLU:"
                
                response = self.client_gemini.models.generate_content(
                    model=self.model_id,
                    contents=full_prompt,
                    config={"temperature": 0.5}
                )
                return response.text
                
            elif self.provider in ["openai", "puter", "openrouter", "zai", "kimi"]:
                messages = [{"role": "system", "content": system_base}]
                for msg in chat_history[-6:]:
                    r = "assistant" if msg.get("role") == "Lu" else "user"
                    messages.append({"role": r, "content": msg["content"]})
                    
                messages.append({"role": "user", "content": user_query})
                
                response = self.client_openai.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                    temperature=0.7
                )
                return response.choices[0].message.content
                
            else:
                return "Provedor LLM não reconhecido para Chat."
                
        except Exception as e:
            return f"Desculpe, tive um problema técnico ao conectar com a IA ({self.model_id}): {e}"

    def otimizar_roteiros(self, roteiros_textos: list, codigo: str, nome_produto: str, ficha_tecnica: str = None) -> dict:
        """
        Sintetiza de 2 a 5 roteiros selecionados escolhendo os melhores ganchos, argumentos e fechamentos,
        mantendo o tom de voz da marca e o formato estrito NW LU.
        """
        # Formata os roteiros para o prompt
        roteiros_formatados = ""
        for i, roteiro in enumerate(roteiros_textos):
            roteiros_formatados += f"--- VERSÃO {i + 1} ---\n{roteiro}\n\n"
            
        sys_prompt = (
            "Você é o Diretor de Criação Sênior da Magalu. Especialista em juntar boas ideias.\n"
            "Eu vou te apresentar algumas versões de roteiros gerados por diferentes IAs para o mesmo produto.\n"
            "Sua tarefa: Sintetize o MÁXIMO da capacidade publicitária dessas versões, RETORNANDO UM ÚNICO ROTEIRO DEFINITIVO QUE SEJA A 'MELHOR VERSÃO'.\n\n"
            "DIRETRIZES DE SÍNTESE:\n"
            "- ABERTURA IMPACTANTE: Escolha o gancho (hook) inicial mais forte e criativo entre as versões.\n"
            "- ARGUMENTAÇÃO SÓLIDA: Pegue a melhor explicação técnica e os benefícios mais persuasivos de cada um.\n"
            "- FECHAMENTO AFIADO: Escolha a melhor CTA e fechamento em tom de voz 'Lu do Magalu'.\n"
            "- FLUIDEZ E RITMO: O texto final deve soar natural, sem retalhos.\n"
            "- COMPARAÇÃO COM A FICHA TÉCNICA: Verifique a ficha técnica fornecida e garanta que nenhuma informação vital (acessórios, voltagem, característica principal) foi esquecida pelas outras IAs.\n"
            "- REGRA DE CABEÇALHO: O roteiro final DEVE preservar a estrutura EXATA de cabeçalho NW LU (Cliente, Roteirista, Data, Produto). NUNCA use negrito (**) no cabeçalho.\n\n"
            "Se você não encontrar a ficha técnica, confie apenas nas informações dadas pelas versões."
        )

        ficha_prompt = f"--- FICHA TÉCNICA ORIGINAL ---\n{ficha_tecnica}\n\n" if ficha_tecnica else ""
        user_prompt = f"Código: {codigo}\nProduto: {nome_produto}\n\n{ficha_prompt}{roteiros_formatados}\n\nPor favor, retorne O ROTEIRO DEFINITIVO (MELHOR VERSÃO) seguindo a formatação padrão NW LU. Sem preâmbulos, texto direto."

        contents = [
            sys_prompt,
            user_prompt
        ]

        if self.client_gemini:
            response = self.client_gemini.generate_content(contents)
            roteiro = response.text
            tokens_in = len(str(contents)) // 4
            tokens_out = len(roteiro) // 4
        elif self.client_openai:
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = self.client_openai.chat.completions.create(
                model=self.model_id,
                messages=messages
            )
            roteiro = response.choices[0].message.content
            tokens_in = response.usage.prompt_tokens if hasattr(response, 'usage') else 0
            tokens_out = response.usage.completion_tokens if hasattr(response, 'usage') else 0
        else:
            raise Exception("Nenhum cliente LLM configurado válido.")

        custo_brl = calcular_custo_brl(self.model_id, tokens_in, tokens_out)

        return {
            "roteiro": roteiro,
            "model_id": f"{self.model_id} (Otimizado)",
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "custo_brl": custo_brl
        }
