import os
import json
import glob
from google import genai
from google.genai.types import GenerateContentConfig
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')

# Tabela de preços por 1M tokens (USD)
PRICING_USD_PER_1M = {
    "gemini-2.5-flash": {"input": 0.70, "output": 2.10},
    "gemini-2.5-pro":   {"input": 3.50, "output": 10.50},
    "gemini-1.5-flash":  {"input": 0.35, "output": 1.05},
    # Novos modelos (Z.ai, Kimi, etc. em modo free por enquanto)
    "gpt-4o-mini": {"input": 0.00, "output": 0.00},
    "x-ai/grok-4-1-fast": {"input": 0.00, "output": 0.00},
    "x-ai/grok-2": {"input": 0.00, "output": 0.00},
    "moonshot-v1-8k": {"input": 0.00, "output": 0.00},
    "glm-4-flash": {"input": 0.00, "output": 0.00},
    "deepseek/deepseek-r1-0528:free": {"input": 0.00, "output": 0.00},
    "deepseek/deepseek-r1-0528:free": {"input": 0.00, "output": 0.00},
    "google/gemma-3-27b-it:free": {"input": 0.00, "output": 0.00},
    "meta-llama/llama-4-scout:free": {"input": 0.00, "output": 0.00},
    "meta-llama/llama-3.1-70b-instruct": {"input": 0.00, "output": 0.00},
    "claude-3-5-sonnet": {"input": 0.00, "output": 0.00},
}
USD_TO_BRL = 5.80

MODELOS_DISPONIVEIS = {
    "⚡ Gemini 2.5 Flash [PAGO] — ~R$0,03/roteiro": "gemini-2.5-flash",
    "🏆 Gemini 2.5 Pro [PAGO] — ~R$0,06/roteiro": "gemini-2.5-pro",
    "🔥 Grok 4.1 Fast [GRÁTIS] — Criativo (Puter)": "puter/x-ai/grok-4-1-fast",
    "🐋 DeepSeek R1 [GRÁTIS] — Técnico (OpenRouter)": "openrouter/deepseek/deepseek-r1-0528:free",
    "🤖 GPT-4o Mini [GRÁTIS] — Fluído (OpenAI)": "openai/gpt-4o-mini",
    "🧠 DeepSeek R1 [GRÁTIS] — Análise (OpenRouter)": "openrouter/deepseek/deepseek-r1-0528:free",
    "💰 Gemini 1.5 Flash [GRÁTIS/PAGO] — Super Econômico": "gemini-1.5-flash",
    "🔥 Grok 2 [GRÁTIS] — Robusto (Puter)": "puter/x-ai/grok-2",
    "💎 Gemma 3 27B [GRÁTIS] — Multimodal (OpenRouter)": "openrouter/google/gemma-3-27b-it:free",
    "🦙 Llama 4 Scout [GRÁTIS] — Nova Geração (OpenRouter)": "openrouter/meta-llama/llama-4-scout:free",
    "🇨🇳 GLM-4 Flash [GRÁTIS] — Ficha Técnica (Z.ai)": "zai/glm-4-flash",
    "🌙 Kimi v1 [GRÁTIS] — Coerência (Moonshot)": "kimi/moonshot-v1-8k",
    "🦙 Llama 3.1 70B [GRÁTIS] — Equilibrado (Puter)": "puter/meta-llama/llama-3.1-70b-instruct",
    "🎭 Claude 3.5 Sonnet [GRÁTIS] — Narrativa Premium (Puter)": "puter/claude-3-5-sonnet",
}

MODELOS_DESCRICAO = {
    "gemini-2.5-flash": "[RECOMENDADO] (2025) O equilíbrio perfeito. Extremamente rápido, lida bem com lotes e tem a melhor integração com a persona da Lu. Custo baixíssimo (~R$ 0,03).",
    "gemini-2.5-pro": "[ELITE] (2025) O modelo mais inteligente. Ideal para produtos complexos ou roteiros que exigem criatividade fora da curva e lógica impecável. Custo (~R$ 0,06).",
    "gemini-1.5-flash": "[ECONÔMICO] (2024) Uma versão estável e muito rápida se as chaves 2.5 estiverem lentas. Ótimo custo-benefício.",
    "openai/gpt-4o-mini": "[ESTÁVEL] (2024) Respostas muito diretas e limpas. Excelente para manter o formato NW sem erros de estrutura.",
    "puter/x-ai/grok-4-1-fast": "[NEGOCIAL/RETIRO] (2025) Excelente para Reels e formatos sociais. Tem um tom mais persuasivo e ganchos de retenção mais fortes.",
    "puter/x-ai/grok-2": "[ROBUSTO] (2024) Muito bom para seguir regras rígidas sem 'pular' instruções. Segue bem a proibição de humanos nas imagens.",
    "openrouter/deepseek/deepseek-r1-0528:free": "Ideal para lógica rigorosa, revisão gramatical avançada e extração de regras complexas, sem as taxas da OpenAI. Menos 'criativo', mas muito preciso nos dados.",
    "openrouter/deepseek/deepseek-r1-0528:free": "[RACIOCÍNIO] (2025) Ideal para calibragem. Pensa passo a passo, identificando erros sutis de pronúncia e tom.",
    "openrouter/google/gemma-3-27b-it:free": "[IMAGEM/VISÃO] (2025) Versão aberta do Google. Surpreendentemente bom em descrever detalhes de fotos do produto.",
    "openrouter/meta-llama/llama-4-scout:free": "[GIGANTE] (2025) Inteligência de ponta para descrições ricas. Ótimo para quando você quer um texto mais longo e detalhado.",
    "zai/glm-4-flash": "[PRECISÃO] (2024) IA chinesa focada em não alucinar. Se o produto tem muitos números e medidas, ele é uma ótima escolha.",
    "kimi/moonshot-v1-8k": "[COERÊNCIA] (2024) Mantém o fio da meada em roteiros longos. Bom para vídeos de Review extensos.",
    "puter/meta-llama/llama-3.1-70b-instruct": "[EQUILIBRADO] (2024) Inteligência de nível Pro em formato aberto. Versátil para todos os modos de trabalho.",
    "puter/claude-3-5-sonnet": "[NARRATIVA PREMIUM] (2024) O rei da escrita natural. Se você quer que o roteiro pareça escrito por um redator sênior, use este.",
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
    pricing = PRICING_USD_PER_1M.get(model_id, PRICING_USD_PER_1M["gemini-2.5-flash"])
    custo_usd = (tokens_in / 1_000_000 * pricing["input"]) + (tokens_out / 1_000_000 * pricing["output"])
    return round(custo_usd * USD_TO_BRL, 6)

class RoteiristaAgent:
    def __init__(self, supabase_client=None, model_id="gemini-2.5-flash"):
        self.model_id = model_id
        self.supabase = supabase_client
        self.client_gemini = None
        self.client_openai = None
        self.provider = "gemini"

        if self.model_id.startswith("gemini"):
            self.provider = "gemini"
            api_key = os.environ.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY não encontrada!")
            self.client_gemini = genai.Client(api_key=api_key)
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
                base_url="https://api.moonshot.cn/v1"
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
            res_ouro = self.supabase.table("nw_roteiros_ouro").select("*").order('criado_em', desc=True).limit(5).execute()
            if res_ouro.data:
                sb_parts.append("\n**REFERÊNCIAS DE ELITE (ESTE É O PADRÃO OURO A SER SEGUIDO):**")
                for r in res_ouro.data:
                    sb_parts.append(f"- Produto: {r['titulo_produto']}\n  Roteiro Perfeito (Target): {r['roteiro_perfeito']}")

            # 2. Ajustes de Persona
            res_pers = self.supabase.table("nw_treinamento_persona_lu").select("*").limit(5).execute()
            if res_pers.data:
                sb_parts.append("\n**AJUSTES DE PERSONA (LIÇÕES APRENDIDAS):**")
                for p in res_pers.data:
                    sb_parts.append(f"- Pilar: {p['pilar_persona']}\n  Erro Anterior: {p['erro_cometido']}\n  Correção Master: {p['texto_corrigido_humano']}")

            # 3. Novas Regras Fonéticas
            res_fon = self.supabase.table("nw_treinamento_fonetica").select("*").execute()
            if res_fon.data:
                sb_parts.append("\n**NOVAS REGRAS DE FONÉTICA (OBRIGATÓRIO):**")
                for f in res_fon.data:
                    sb_parts.append(f"- {f['termo_errado']} -> ({f['termo_corrigido']})")
                    
            # 4. Estruturas Aprovadas (Aberturas e Fechamentos/CTAs)
            res_est = self.supabase.table("nw_treinamento_estruturas").select("*").execute()
            if res_est.data:
                sb_parts.append("\n**ESTRUTURAS APROVADAS PARA INSPIRAÇÃO (HOOKS E CTAs):**")
                for est in res_est.data:
                    sb_parts.append(f"- [{est['tipo_estrutura']}] {est['texto_ouro']}")
                    
            # 5. Nuances de Linguagem (O que evitar e como melhorar)
            res_nuan = self.supabase.table("nw_treinamento_nuances").select("*").limit(5).order('criado_em', desc=True).execute()
            if res_nuan.data:
                sb_parts.append("\n**NUANCES E REFINAMENTO DE ESTILO (LIÇÕES DE REDAÇÃO):**")
                for n in res_nuan.data:
                    refinamento = f"- EVITE: '{n['frase_ia']}'\n  POR QUE: {n['analise_critica']}"
                    if n.get('exemplo_ouro'):
                        refinamento += f"\n  FORMA IDEAL: '{n['exemplo_ouro']}'"
                    sb_parts.append(refinamento)

            # 6. Memória de Calibragem (Lições Recentes da Calibragem)
            res_fb = self.supabase.table("nw_roteiros_ouro").select("aprendizado").neq("aprendizado", "null").order('criado_em', desc=True).limit(8).execute()
            if res_fb.data:
                valid_mems = [f for f in res_fb.data if f.get('aprendizado') and f['aprendizado'].strip()]
                if valid_mems:
                    sb_parts.append("\n**LIÇÕES RECENTES DA CALIBRAGEM (NÃO REPITA ESTES ERROS):**")
                    for fb in valid_mems:
                        sb_parts.append(f"- {fb['aprendizado']}")
        except Exception as e:
            print(f"Erro ao buscar contexto no Supabase: {e}")
            
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
                print("✅ Memória de calibragem gerada via Puter (grok-4-1-fast)")
                return response.choices[0].message.content.replace('\n', ' ').strip()
            except Exception as e:
                print(f"⚠️ Erro Puter Memória: {e}")

        # 🔵 OPÇÃO 2: OPENROUTER (DeepSeek V3 — Grátis)
        api_key_or = os.environ.get("OPENROUTER_API_KEY")
        if api_key_or:
            try:
                from openai import OpenAI as OpenAIClient
                client = OpenAIClient(api_key=api_key_or, base_url="https://openrouter.ai/api/v1")
                response = client.chat.completions.create(
                    model="deepseek/deepseek-chat-v3-0324:free",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                print("✅ Memória de calibragem gerada via OpenRouter (deepseek-v3)")
                return response.choices[0].message.content.replace('\n', ' ').strip()
            except Exception as e:
                print(f"⚠️ Erro OpenRouter Memória: {e}")

        # 🟡 OPÇÃO 3: GEMINI (se a key funcionar)
        api_key_gemini = os.environ.get("GEMINI_API_KEY")
        if api_key_gemini:
            try:
                from google.genai import types
                client = genai.Client(api_key=api_key_gemini)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.3)
                )
                print("✅ Memória de calibragem gerada via Gemini (2.5-flash)")
                return response.text.replace('\n', ' ').strip()
            except Exception as e:
                print(f"⚠️ Erro Gemini Memória: {e}")

        return "Erro: Nenhum provedor disponível para gerar memória de calibragem."

    def gerar_roteiro(self, scraped_data, modo_trabalho="NW (NewWeb)", mes="MAR", data_roteiro=None, codigo=None, nome_produto=None):
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
            prod_str = nome_produto if nome_produto else "[NOME_DO_PRODUTO_AQUI]"
            cod_str = codigo if codigo else "[CÓDIGO_AQUI]"
            
            sub_skus_str = f" (Variações/Cores: {sub_skus})" if sub_skus else ""
            video_ref_str = f"\n   Vídeo Base do Fornecedor: {video_url} (Sugira cortes deste vídeo para as imagens quando aplicável)" if video_url else ""
            
            diretriz_modo += (
                f"\n\n🚨 REGRA ABSOLUTA DE FORMATAÇÃO E ESTRUTURA (NW LU):\n"
                f"1. O TEXTO DEVE COMEÇAR COM O CABEÇALHO EXATAMENTE NO FORMATO:\n"
                f"   Cliente: Magalu\n"
                f"   Roteirista: Tiago Fernandes - Data: {data_str}\n"
                f"   Produto: NW LU {mes} {cod_str} {prod_str}{sub_skus_str}{video_ref_str}\n"
                f"2. A CENA 1 (Primeira cena do vídeo) DEVE OBRIGATORIAMENTE mostrar a 'Lu' em ação, interagindo com o produto ou apresentando-o.\n"
                f"3. A partir da CENA 2, CORTE para imagens do produto. REGRA CRÍTICA DE IMAGEM: É ESTRITAMENTE PROIBIDO sugerir ações humanas nas Colunas de Imagem (ex: 'mão segurando o celular', 'pessoa bebendo café', 'cliente usando'). O vídeo NW é feito APENAS com fotos estáticas do fornecedor, animações gráficas (GCs) e recortes do vídeo oficial. IMAGENS 100% LIMPAS DE HUMANOS."
            )

        if "SOCIAL" in modo_trabalho:
            diretriz_modo = f"ATENÇÃO: Este formato é para SOCIAL (Reels/TikTok). O roteiro deve ser EXTREMAMENTE curto, dinâmico e focado em retenção nos primeiros 3 segundos."
        elif "3D" in modo_trabalho:
            diretriz_modo = f"ATENÇÃO: Este formato é para 3D. Foque muito em descrever as texturas, cores exatas, reflexos e ângulos importantes para o time de modelagem."
        elif "Review" in modo_trabalho:
            diretriz_modo = f"ATENÇÃO: Este formato é um REVIEW. Foque em prós, contras, uso prático diário e uma opinião direta para quem vai gravar no estúdio."

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
            f"7. **REGRA DE REFERÊNCIA:** Se usar conhecimento interno (item 6) ou dados de 'FONTE EXTERNA', adicione OBRIGATORIAMENTE uma nota com o link oficial no rodapé do roteiro.\n"
            f"8. **PROIBIÇÃO DE SCRIPTS HIPOTÉTICOS:** Se o contexto do produto for insuficiente ou tiver mensagem de erro, NÃO gere roteiro hipotético. Responda APENAS: 'ERRO: Dados insuficientes do produto para geração automática.'"
        )

        if self.client_gemini:
            contents = [final_prompt]
            # Adiciona a lista de imagens se houver
            if images_list:
                from google.genai.types import Part
                for img_dict in images_list:
                    img_bytes = img_dict.get("bytes")
                    img_mime = img_dict.get("mime")
                    if img_bytes and img_mime:
                        contents.append(
                            Part.from_bytes(data=img_bytes, mime_type=img_mime)
                        )

            response = self.client_gemini.models.generate_content(
                model=self.model_id,
                contents=contents,
            )
            roteiro = response.text
            
            # Captura métricas de uso (tokens)
            tokens_in = getattr(response.usage_metadata, 'prompt_token_count', 0) if hasattr(response, 'usage_metadata') else 0
            tokens_out = getattr(response.usage_metadata, 'candidates_token_count', 0) if hasattr(response, 'usage_metadata') else 0
        
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
            "3. SÍNTESE DE APRENDIZADO (MEMÓRIA TÉCNICA): Transforme as edições em DIRETRIZES TÁTICAS E IMPERATIVAS DE ESCRITA, INCLUINDO SEMPRE UM EXEMPLO PRÁTICO do que foi mudado.\n"
            "   Sua diretriz DEVE ser aplicável a futuros roteiros como uma regra de ouro.\n"
            "   - REGRA ANTI-ALUCINAÇÃO: É ESTRITAMENTE PROIBIDO listar especificações técnicas do produto como se fossem regras de redação (ex: 'Falar que tem freio a disco'). Foque APENAS no ESTILO de escrita.\n"
            "   - REGRA DE LOCALIZAÇÃO E CONTEXTO: Se o humano CORTOU ou ADICIONOU um bloco de texto, explique O QUE era, POR QUE cortou e ONDE (em qual cena exata isso ocorreu). \n"
            "     * O roteiro possui uma estrutura lógica (ex: Cena 1 - Abertura, Cena 3 - Features, Penúltima cena - Conexões/Bateria, Fechamento). Mapeie a alteração para a cena correspondente.\n"
            "     * Ex: 'Na penúltima cena, cortou redundância sobre cansaço visual pois a tecnologia Frost Free ou Flicker-Free já havia sido explicada na primeira metade'.\n"
            "   - ERRADO: 'Breno tirou a palavra X e colocou Y.'\n"
            "   - CERTO: '- Focar no benefício emocional em vez da ficha técnica (Ex: Trocou \"Possui painel IPS\" por \"Cores vivas de qualquer ângulo\"). - Iniciar o texto com sujeito explícito (Ex: \"Ela tem\" em vez de \"Tem\").'\n"
            "   Seja curto, grosso e imperativo, mas SEMPRE DÊ EXEMPLOS nas próprias frases. Use tópicos com '-'.\n"
            "4. EXTRAIA O CÓDIGO DO PRODUTO (SKU): Procure no texto por sequências numéricas ou o código fornecido.\n"
            "5. CATEGORIZE (CRÍTICO): Escolha a melhor categoria da lista abaixo baseada na FUNÇÃO PRINCIPAL DO PRODUTO. "
            "Não se confunda com funcionalidades extras (ex: um monitor gamer com alto-falante é 'Informatica / Gamer', e NUNCA 'Áudio'). "
            "Leia o texto com atenção para identificar a essência do produto.\n"
            "6. FONÉTICA (AUTO-EXTRAÇÃO): Se o humano ADICIONOU, CORRIGIU ou REMOVEU pronúncias fonéticas (ex: acrescentou '(flíker frí)' para Flicker-Free), "
            "extraia como regras no campo 'fonetica_regras'. Cada regra tem: "
            "'termo_errado' (a versão sem pronúncia se o humano adicionou, ou a versão com pronúncia ruim), 'termo_corrigido' (a versão final que o humano deixou, ex: Flicker-Free (flíker frí)), "
            "'exemplo' (frase de contexto). Importante: Capturar casos onde o humano removeu o parênteses de pronúncia para deixar o texto mais limpo, E TAMBÉM quando o humano adicionou uma pronúncia essencial que a IA esqueceu. Se NÃO houver correções, retorne [].\n"
            "7. ESTRUTURAS (AUTO-EXTRAÇÃO): Se o humano MUDOU a ABERTURA (primeira frase) ou o FECHAMENTO (última frase), "
            "extraia o texto APROVADO PELO HUMANO no campo 'estrutura_regras'. Cada regra tem: "
            "'tipo' ('Abertura' ou 'Fechamento') e 'texto_ouro' (a frase exata aprovada pelo humano). "
            "Se NÃO houve mudança na abertura/fechamento, retorne lista vazia [].\n"
            "8. PERSONA LU (AUTO-EXTRAÇÃO): Se o humano corrigiu o TOM DE VOZ, ESTILO ou VOCABULÁRIO da Lu, "
            "extraia como regras no campo 'persona_regras'. Cada regra tem: "
            "'pilar' (tom, vocabulário, gancho, emoção, clareza), 'erro' (o que a IA fez de errado), "
            "'correcao' (como o humano corrigiu) e 'lexico' (palavras-chave ou termos preferíveis identificados na correção). "
            "Se NÃO houver correções de persona, retorne lista vazia [].\n\n"
            "LISTA DE CATEGORIAS DISPONÍVEIS:\n"
            f"{cat_str}\n\n"
            "🚨 REGRA CRÍTICA DE FORMATAÇÃO DE SAÍDA:\n"
            "Você é um robô de extração de dados. Retorne EXCLUSIVAMENTE o conteúdo JSON abaixo.\n"
            "- NÃO use blocos de código markdown (```json ... ```).\n"
            "- NÃO diga 'Aqui está o JSON'.\n"
            "- Inicie com { e termine com }.\n\n"
            "Formato exato:\n"
            "{\n"
            "  \"percentual\": <inteiro 0-100>,\n"
            "  \"aprendizado\": \"<diretrizes táticas de escrita em tópicos>\",\n"
            "  \"categoria_id\": <id numérico da melhor categoria>,\n"
            "  \"codigo_produto\": \"<código encontrado no texto ou o original>\",\n"
            "  \"fonetica_regras\": [{\"termo_errado\": \"...\", \"termo_corrigido\": \"...\", \"exemplo\": \"...\"}],\n"
            "  \"estrutura_regras\": [{\"tipo\": \"Abertura\", \"texto_ouro\": \"...\"}],\n"
            "  \"persona_regras\": [{\"pilar\": \"...\", \"erro\": \"...\", \"correcao\": \"...\", \"lexico\": \"...\"}]\n"
            "}"
        )

        user_prompt = f"--- CÓDIGO SUGERIDO ---\n{codigo_original}\n\n--- ROTEIRO ORIGINAL (IA) ---\n{original}\n\n--- ROTEIRO FINAL (HUMANO) ---\n{final}"

        # Tenta múltiplos provedores para garantir a calibragem (OpenRouter [DeepSeek] → Puter [Grok] → Gemini)
        from openai import OpenAI as OpenAIClient
        
        # 🔵 OPÇÃO 1: OPENROUTER (DeepSeek V3 — Grátis e Superior para Lógica)
        api_key_or = os.environ.get("OPENROUTER_API_KEY")
        if api_key_or:
            try:
                print("🔄 Tentando calibragem via OpenRouter (deepseek-r1)...")
                client = OpenAIClient(api_key=api_key_or, base_url="https://openrouter.ai/api/v1")
                response = client.chat.completions.create(
                    model="deepseek/deepseek-r1-0528:free",
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1
                )
                res = self._extract_json(response.choices[0].message.content)
                print("✅ Calibragem realizada via OpenRouter (deepseek-r1)")
                return self._process_calib_res(res, fallback_id, categories_list, codigo_original, "DeepSeek R1 (via OpenRouter)")
            except Exception as e:
                print(f"⚠️ Erro OpenRouter Calibragem: {e}")

        # 🟢 OPÇÃO 2: PUTER (Grok 4.1 Fast — Grátis e reserva)
        api_key_puter = os.environ.get("PUTER_API_KEY")
        if api_key_puter:
            try:
                print("🔄 Tentando calibragem via Puter (grok-4-1-fast)...")
                client = OpenAIClient(api_key=api_key_puter, base_url="https://api.puter.com/puterai/openai/v1/")
                response = client.chat.completions.create(
                    model="x-ai/grok-4-1-fast",
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1
                )
                res = self._extract_json(response.choices[0].message.content)
                print("✅ Calibragem realizada via Puter (grok-4-1-fast)")
                return self._process_calib_res(res, fallback_id, categories_list, codigo_original, "Grok 4.1 Fast (via Puter)")
            except Exception as e:
                print(f"⚠️ Erro Puter Calibragem: {e}")

        # 🟡 OPÇÃO 3: GEMINI (último recurso — pode ter key inválida)
        api_key_gemini = os.environ.get("GEMINI_API_KEY")
        if api_key_gemini:
            try:
                print("🔄 Tentando calibragem via Gemini (2.5-flash)...")
                client = genai.Client(api_key=api_key_gemini)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=user_prompt,
                    config=GenerateContentConfig(
                        system_instruction=sys_prompt,
                        response_mime_type="application/json",
                        temperature=0.1
                    ),
                )
                res = json.loads(response.text)
                print("✅ Calibragem realizada via Gemini (2.5-flash)")
                return self._process_calib_res(res, fallback_id, categories_list, codigo_original, "Gemini 2.5 Flash (via Google)")
            except Exception as e:
                print(f"⚠️ Erro Gemini Calibragem: {e}")

        print("❌ FALHA TOTAL: Nenhum provedor de IA conseguiu realizar a calibragem.")
        return {"percentual": 50, "aprendizado": "Erro: Nenhum provedor de IA disponível para calibragem.", "categoria_id": fallback_id, "codigo_produto": codigo_original, "modelo_calibragem": "N/A", "fonetica_regras": [], "estrutura_regras": [], "persona_regras": []}

    def _process_calib_res(self, res, fallback_id, categories_list, codigo_original, modelo_calibragem="N/A"):
        """Helper para processar e validar o JSON retornado pelos provedores."""
        # Validação rigorosa do ID de categoria
        returned_id = int(res.get("categoria_id", fallback_id))
        valid_ids = [c['id'] for c in categories_list] if categories_list else []
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
