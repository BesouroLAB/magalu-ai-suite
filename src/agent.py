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
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "gemini-2.5-pro":   {"input": 1.25, "output": 10.00},
    "gemini-2.0-flash":  {"input": 0.10, "output": 0.40},
    # Novos modelos (Z.ai, Kimi, etc. em modo free por enquanto)
    "gpt-4o-mini": {"input": 0.00, "output": 0.00},
    "grok-4-1-fast": {"input": 0.00, "output": 0.00},
    "grok-2": {"input": 0.00, "output": 0.00},
    "moonshot-v1-8k": {"input": 0.00, "output": 0.00},
    "glm-4-flash": {"input": 0.00, "output": 0.00},
    "deepseek-chat-v3-0324:free": {"input": 0.00, "output": 0.00},
    "deepseek-r1:free": {"input": 0.00, "output": 0.00},
    "gemini-2.5-flash-preview": {"input": 0.15, "output": 0.60},
}
USD_TO_BRL = 5.80

MODELOS_DISPONIVEIS = {
    "⚡ Gemini 2.5 Flash — Grátis": "gemini-2.5-flash",
    "🏆 Gemini 2.5 Pro — ~R$0,06/roteiro": "gemini-2.5-pro",
    "💰 Gemini 2.0 Flash — Grátis": "gemini-2.0-flash",
    "🤖 GPT-4o Mini — Grátis": "openai/gpt-4o-mini",
    "🔥 Grok 4.1 Fast — Grátis (Puter)": "puter/x-ai/grok-4-1-fast",
    "🔥 Grok 2 — Grátis (Puter)": "puter/x-ai/grok-2",
    "🐋 DeepSeek V3 — Grátis (OpenRouter)": "openrouter/deepseek/deepseek-chat-v3-0324:free",
    "🧠 DeepSeek R1 — Grátis (OpenRouter)": "openrouter/deepseek/deepseek-r1:free",
    "⚡ Gemini 2.5 Flash — Créditos (OpenRouter)": "openrouter/google/gemini-2.5-flash-preview",
    "🇨🇳 GLM-4 Flash — Grátis (Z.ai)": "zai/glm-4-flash",
    "🌙 Kimi v1 — Grátis (Moonshot)": "kimi/moonshot-v1-8k",
}

# Mapeamento de provider -> env var necessária
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

        # Carrega toda a base de conhecimento estática
        self.system_prompt = self._load_file(
            os.path.join(PROJECT_ROOT, ".agents", "system_prompt.txt"), ""
        )
        self.phonetics = self._load_json(
            os.path.join(PROJECT_ROOT, "kb", "phonetics.json"), {}
        )
        self.few_shot_examples = self._load_json(
            os.path.join(PROJECT_ROOT, "kb", "few_shot_breno.json"), []
        )
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
            # 1. Roteiros Ouro (Exemplos Master)
            res_ouro = self.supabase.table("roteiros_ouro").select("*").limit(3).execute()
            if res_ouro.data:
                sb_parts.append("\n**REFERÊNCIAS DE ELITE (ROTEIROS OURO SÃO O ALVO):**")
                for r in res_ouro.data:
                    sb_parts.append(f"- Produto: {r['titulo_produto']}\n  Roteiro Perfeito: {r['roteiro_perfeito']}")

            # 2. Ajustes de Persona
            res_pers = self.supabase.table("treinamento_persona_lu").select("*").limit(5).execute()
            if res_pers.data:
                sb_parts.append("\n**AJUSTES DE PERSONA (LIÇÕES APRENDIDAS):**")
                for p in res_pers.data:
                    sb_parts.append(f"- Pilar: {p['pilar_persona']}\n  Erro Anterior: {p['erro_cometido']}\n  Correção Master: {p['texto_corrigido_humano']}")

            # 3. Novas Regras Fonéticas
            res_fon = self.supabase.table("treinamento_fonetica").select("*").execute()
            if res_fon.data:
                sb_parts.append("\n**NOVAS REGRAS DE FONÉTICA (OBRIGATÓRIO):**")
                for f in res_fon.data:
                    sb_parts.append(f"- {f['termo_errado']} -> ({f['termo_corrigido']})")
                    
            # 4. Estruturas Aprovadas (Aberturas e Fechamentos/CTAs)
            res_est = self.supabase.table("treinamento_estruturas").select("*").execute()
            if res_est.data:
                sb_parts.append("\n**ESTRUTURAS APROVADAS PARA INSPIRAÇÃO (HOOKS E CTAs):**")
                for est in res_est.data:
                    sb_parts.append(f"- [{est['tipo_estrutura']}] {est['texto_ouro']}")
                    
            # 5. Nuances de Linguagem (O que evitar e como melhorar)
            res_nuan = self.supabase.table("treinamento_nuances").select("*").limit(5).order('criado_em', desc=True).execute()
            if res_nuan.data:
                sb_parts.append("\n**NUANCES E REFINAMENTO DE ESTILO (LIÇÕES DE REDAÇÃO):**")
                for n in res_nuan.data:
                    refinamento = f"- EVITE: '{n['frase_ia']}'\n  POR QUE: {n['analise_critica']}"
                    if n.get('exemplo_ouro'):
                        refinamento += f"\n  FORMA IDEAL: '{n['exemplo_ouro']}'"
                    sb_parts.append(refinamento)

            # 6. Memória de Calibração (Lições Recentes do Antes x Depois)
            res_fb = self.supabase.table("feedback_roteiros").select("comentarios").neq("comentarios", "null").limit(5).order('criado_em', desc=True).execute()
            if res_fb.data:
                valid_mems = [f for f in res_fb.data if f.get('comentarios') and f['comentarios'].strip()]
                if valid_mems:
                    sb_parts.append("\n**MEMÓRIA RECENTE DE CORREÇÕES (NÃO REPITA ESTES ERROS):**")
                    for fb in valid_mems:
                        sb_parts.append(f"- O Breno corrigiu recentemente: {fb['comentarios']}")
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
        """Analisa a diferença entre o texto da IA e o aprovado, e extrai a 'lição'."""
        prompt = (
            "Você é um analista de texto comparando DUAS versões de um roteiro de vídeo.\n\n"
            "VERSÃO A (Gerada pela IA):\n"
            f"{ia_text}\n\n"
            "VERSÃO B (Aprovada pelo Breno):\n"
            f"{breno_text}\n\n"
            "Sua tarefa: Faça uma análise TÉCNICA e ESPECÍFICA das diferenças entre A e B.\n"
            "Identifique EXATAMENTE:\n"
            "- O que foi CORTADO da versão A\n"
            "- O que foi SUBSTITUÍDO e pelo quê\n"
            "- O que foi ADICIONADO na versão B\n"
            "- Qual PADRÃO de escrita o Breno aplicou (ex: encurtou frases, trocou termo técnico por coloquial, reorganizou a ordem das cenas, etc.)\n\n"
            "Responda em NO MÁXIMO 2 frases objetivas (máximo 200 caracteres). "
            "Use o formato: 'Breno cortou [X] e trocou por [Y]. Padrão: [razão técnica].'\n"
            "NÃO use metáforas. NÃO mencione 'júnior' ou 'sênior'. Seja direto e técnico."
        )
        try:
            from google import genai
            from google.genai import types
            import os
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
            if not api_key:
                return "API Key ausente para gerar memória."
            
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.3)
            )
            return response.text.replace('\n', ' ').strip()
        except Exception as e:
            print(f"Erro na auto-avaliação: {e}")
            return "Erro ao gerar memória."

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
            
            diretriz_modo += (
                f"\n\n🚨 REGRA ABSOLUTA DE FORMATAÇÃO E ESTRUTURA (NW LU):\n"
                f"1. O TEXTO DEVE COMEÇAR COM O CABEÇALHO EXATAMENTE NO FORMATO:\n"
                f"   Cliente: Magalu\n"
                f"   Roteirista: Tiago Fernandes - Data: {data_str}\n"
                f"   Produto: NW LU {mes} {cod_str} {prod_str}\n"
                f"2. A CENA 1 (Primeira cena do vídeo) DEVE OBRIGATORIAMENTE mostrar a 'Lu' em ação, interagindo com o produto ou apresentando-o.\n"
                f"3. A partir da CENA 2, CORTE para cenas detalhadas apenas do produto (Sem a Lu no vídeo)."
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
            f"2. Siga RIGOROSAMENTE as Regras de Ouro do Estilo Breno.\n"
            f"3. Se houverem imagens fornecidas, extraia o máximo de detalhes visuais (cor, textura, design dos vários ângulos) para enriquecer o roteiro.\n"
            f"4. Imite fielmente o estilo dos exemplos APROVADOS.\n"
            f"5. Use 'pra' no lugar de 'para'. Coloque a marca entre vírgulas.\n"
            f"6. **ENRIQUECIMENTO DE CONTEXTO:** Para produtos mundialmente conhecidos (Ex: LEGO, Star Wars, iPhone), você PODE usar seu conhecimento interno para adicionar detalhes técnicos ou curiosidades que NÃO estejam na ficha, visando valorizar o roteiro.\n"
            f"7. **REGRA DE REFERÊNCIA:** Se você usar conhecimento interno (item 6) OU dados de 'FONTE EXTERNA' (fabricante), você deve OBRIGATORIAMENTE adicionar uma nota de referência com o link da fonte (ou site oficial do fabricante) no rodapé do roteiro."
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
