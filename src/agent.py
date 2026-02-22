import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Carrega variáveis de ambiente (GEMINI_API_KEY)
load_dotenv()

class RoteiristaAgent:
    def __init__(self):
        # Configura a API Key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada no arquivo .env")
        genai.configure(api_key=api_key)
        
        # Usamos o modelo 1.5 Pro (recomendado para RAG complexo e seguir instruções estritas)
        # Pode substituir por 'gemini-1.5-flash' se velocidade e custo forem primordiais no MVP.
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Carrega a base de conhecimento (Prompt, Fonética e Few-Shot)
        self.system_prompt = self._load_file(".agents/system_prompt.txt", "Prompt do Sistema Padrão")
        self.phonetics = self._load_json("kb/phonetics.json", {})
        self.few_shot_examples = self._load_json("kb/few_shot_breno.json", [])
        
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
        print("Montando contexto e enviando ao Gemini...")
        
        context = self._build_context()
        
        final_prompt = f"{context}\n\n**CONTEXTO DO PRODUTO (INPUT):**\n{scraped_data}\n\n"
        final_prompt += "Agora, gere o Roteiro Final no Formato Obrigatório para este produto!"
        
        # No Gemini API, mandamos o textão todo (o system prompt faz parte do content list no SDK simples)
        response = self.model.generate_content(final_prompt)
        
        return response.text
