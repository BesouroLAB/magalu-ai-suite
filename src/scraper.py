"""
Scraper inteligente via Google Search Retrieval (SDK v2).
Foca na pesquisa do Código do Produto Magalu no Google para evitar bloqueios de IP/CAPTCHA.
"""
import os
import re
from google import genai
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
from dotenv import load_dotenv

load_dotenv()

EXTRACTION_PROMPT = """
Você é um pesquisador especialista em produtos do Magazine Luiza.

SUA TAREFA:
1. Pesquise no Google pelo produto da Magalu com o código: "{code}".
2. Encontre a página oficial no site magazineluiza.com.br.
3. Extraia os dados técnicos reais desse produto.

**FORMATO DE SAÍDA OBRIGATÓRIO:**
TÍTULO: [Nome completo]
MARCA: [Fabricante]
DESCRIÇÃO: [Resumo das funcionalidades principais]
FICHA TÉCNICA:
- [Item]: [Valor]
...

**REGRAS DE PESQUISA E REDAÇÃO:**
- Use a ferramenta de busca do Google para encontrar a ficha técnica real.
- Tente pesquisar exatamente por: site:magazineluiza.com.br "{code}"
- Se não achar, tente pesquisar por: "{code}" magazineluiza
- 🚨 REGRA ANTI-PLÁGIO (MUITO IMPORTANTE): Você NÃO DEVE copiar textos inteiros da internet palavra por palavra.
- RESUMA E PARAFRASEIE a "DESCRIÇÃO" com suas próprias palavras, mantendo apenas os fatos técnicos importantes. Sintetize a informação para evitar bloqueios de direitos autorais.
- Na "FICHA TÉCNICA", organize os dados brutos de forma concisa.
- Se não encontrar absolutamente nada sobre esse código, responda rigorosamente: "ERRO: Produto não encontrado ou dados indisponíveis."
"""

def scrape_with_gemini(code_or_url: str, api_key: str | None = None) -> dict:
    """Extrai dados usando Grounding do Google Search via SDK v2 (google.genai)."""
    api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return {"text": "❌ API Key não configurada no painel lateral.", "images": []}

    # Limpeza do código
    input_val = code_or_url.strip()
    if input_val.startswith("http"):
        match = re.search(r'/p/(\w+)', input_val)
        code = match.group(1) if match else input_val
    else:
        code = re.sub(r'[^0-9a-zA-Z]', '', input_val)

    prompt = EXTRACTION_PROMPT.replace("{code}", code)

    try:
        os.environ.setdefault("GOOGLE_API_KEY", api_key)
        client = genai.Client(api_key=api_key)
        
        # O novo SDK v2 exige o uso de GoogleSearch em vez de GoogleSearchRetrieval
        config = GenerateContentConfig(
            tools=[Tool(google_search=GoogleSearch())],
            temperature=0.0
        )
        
        # gemini-2.5-flash suporta search grounding nativamente
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=prompt,
            config=config
        )
        
        result_text = response.text if hasattr(response, "text") else None
        
        if not result_text or len(result_text.strip()) < 50:
            result_text = f"⚠️ Não foi possível extrair dados para o SKU {code} via Google Search Retrieval. Cole a ficha manualmente."

        return {"text": result_text, "images": []}
    except Exception as e:
        return {"text": f"❌ Erro no Scraper GenAI: {str(e)}", "images": []}

def parse_codes(raw_input: str) -> list[str]:
    """Parseia códigos separados por vírgula, espaço ou nova linha."""
    return [c.strip() for c in re.split(r'[,\s\n]+', raw_input.strip()) if c.strip()]
