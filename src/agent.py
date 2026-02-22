import os
import json
import glob
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')

class RoteiristaAgent:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada!")
        genai.configure(api_key=api_key)

        self.model = genai.GenerativeModel('gemini-2.5-flash')

        # Carrega toda a base de conhecimento
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

    def _build_context(self):
        """Monta o contexto completo: Prompt + KB Estratégica + Fonética + Few-Shot."""
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

        # 3. Dicionário de fonética
        if self.phonetics:
            parts.append("\n**DICIONÁRIO DE FONÉTICA (OBRIGATÓRIO USAR SE A SIGLA APARECER):**")
            for sigla, pronuncia in self.phonetics.items():
                parts.append(f"- {sigla} -> ({pronuncia})")

        # 4. Few-Shot Learning (Antes vs Depois do Breno)
        if self.few_shot_examples:
            parts.append("\n**EXEMPLOS REAIS DE CORREÇÃO (ESTUDE COM ATENÇÃO):**")
            parts.append("Abaixo estão roteiros que a IA gerou e como o editor Breno CORRIGIU.")
            parts.append("Você DEVE imitar o estilo do texto APROVADO, não o texto gerado.")
            for ex in self.few_shot_examples:
                parts.append(f"\n--- EXEMPLO: {ex.get('produto', '')} ---")
                parts.append(f"❌ TEXTO RUIM (o que a IA gerou errado):")
                parts.append(ex.get('output_antes_ia_ruim', ''))
                parts.append(f"✅ TEXTO APROVADO (o que o Breno corrigiu):")
                parts.append(ex.get('output_depois_breno_aprovado', ''))
            parts.append("-" * 40)

        return "\n".join(parts)

    def gerar_roteiro(self, scraped_data):
        """Envia a requisição para o Gemini gerar o roteiro."""
        context = self._build_context()

        final_prompt = (
            f"{context}\n\n"
            f"**CONTEXTO DO PRODUTO (INPUT):**\n{scraped_data}\n\n"
            f"**INSTRUÇÃO FINAL:**\n"
            f"Gere o roteiro no FORMATO DE SAÍDA OBRIGATÓRIO.\n"
            f"Siga RIGOROSAMENTE as Regras de Ouro do Estilo Breno.\n"
            f"Imite fielmente o estilo dos exemplos APROVADOS.\n"
            f"Use 'pra' no lugar de 'para'. Coloque a marca entre vírgulas.\n"
            f"NÃO invente informações. Só use dados da ficha técnica acima."
        )

        response = self.model.generate_content(final_prompt)
        return response.text
