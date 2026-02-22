import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Carrega variáveis de ambiente (GEMINI_API_KEY)
load_dotenv()

# Diretório raiz do projeto (um nível acima de /src/)
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')

class RoteiristaAgent:
    def __init__(self):
        # Configura a API Key (aceita tanto do .env quanto injetada pelo app.py/Streamlit secrets)
        api_key = os.environ.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada! Configure no .env ou nos Secrets do Streamlit Cloud.")
        genai.configure(api_key=api_key)

        # Usamos o Gemini 2.5 Flash (rápido, gratuito e excelente para seguir instruções)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

        # Carrega a base de conhecimento usando caminhos absolutos
        self.system_prompt = self._load_file(
            os.path.join(PROJECT_ROOT, ".agents", "system_prompt.txt"),
            "Prompt do Sistema Padrão"
        )
        self.phonetics = self._load_json(
            os.path.join(PROJECT_ROOT, "kb", "phonetics.json"), {}
        )
        self.few_shot_examples = self._load_json(
            os.path.join(PROJECT_ROOT, "kb", "few_shot_breno.json"), []
        )

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

    def _build_context(self):
        """Monta o mega-prompt com as regras, exemplos e dicionários."""
        context = f"{self.system_prompt}\n\n"

        if self.phonetics:
            context += "**DICIONÁRIO DE FONÉTICA (OBRIGATÓRIO USAR SE A SIGLA APARECER):**\n"
            for sigla, pronuncia in self.phonetics.items():
                context += f"- {sigla} -> ({pronuncia})\n"
            context += "\n"

        if self.few_shot_examples:
            context += "**EXEMPLOS DE ALTA QUALIDADE (COMO O BRENO EDITA):**\n"
            context += "Estude como a IA errou e como o humano corrigiu nestes casos:\n"
            for ex in self.few_shot_examples:
                context += f"-> Produto: {ex.get('produto', '')}\n"
                context += f"-> O texto que a IA gerou ruim: \n{ex.get('output_antes_ia_ruim', '')}\n"
                context += f"-> O texto CORRETO E APROVADO: \n{ex.get('output_depois_breno_aprovado', '')}\n"
                context += "-"*40 + "\n"

        return context

    def gerar_roteiro(self, scraped_data):
        """Envia a requisição fina para o Gemini gerar o roteiro final."""
        context = self._build_context()

        final_prompt = f"{context}\n\n**CONTEXTO DO PRODUTO (INPUT):**\n{scraped_data}\n\n"
        final_prompt += "Agora, gere o Roteiro Final no Formato Obrigatório para este produto!"

        response = self.model.generate_content(final_prompt)

        return response.text
