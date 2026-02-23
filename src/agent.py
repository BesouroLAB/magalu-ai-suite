import os
import json
import glob
from google import genai
from google.genai.types import GenerateContentConfig
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')

class RoteiristaAgent:
    def __init__(self, supabase_client=None):
        api_key = os.environ.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada!")

        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.5-flash"
        self.supabase = supabase_client

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

    def gerar_roteiro(self, scraped_data, modo_trabalho="NW (NewWeb)"):
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

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=contents,
        )
        return response.text
