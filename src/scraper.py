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
        client = genai.Client(api_key=api_key, http_options={'timeout': 150000})
        result_text = None
        
        # O novo SDK v2 exige o uso de GoogleSearch em vez de GoogleSearchRetrieval
        config = GenerateContentConfig(
            tools=[Tool(google_search=GoogleSearch())],
            temperature=0.0
        )
        
        # Tenta primeiro com o Gemini 2.5 Flash (Estável com Google Search Grounding)
        # Se falhar, faz fallback automático para o 3.1 Pro (Menos rápido mas bem equipado)
        response = None
        try:
            print(f"[SCRAPER] Tentando Grounding via Gemini 2.5 Flash...")
            response = client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=prompt,
                config=config
            )
        except Exception as e_1:
            print(f"[SCRAPER] Gemini 2.5 instável ({e_1}). Acionando FALLBACK 3.1 Pro...")
            try:
                response = client.models.generate_content(
                    model='gemini-3.1-pro-preview', 
                    contents=prompt,
                    config=config
                )
            except Exception as e_2:
                print(f"[SCRAPER] Gemini 3.1 também falhou no Grounding ({e_2}).")
                response = None
        
        def get_text_safe(resp):
            try:
                if resp and hasattr(resp, 'text'):
                    return resp.text
                return None
            except:
                return None

        result_text = get_text_safe(response)
        
        if not result_text or len(result_text.strip()) < 50 or "ERRO:" in result_text:
            print(f"[SCRAPER] Grounding falhou para {code}. Tentando Prompt Direto...")
            # Fallback 1: Prompt Direto sem Tools
            try:
                response_fallback = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"Extraia a ficha técnica do produto Magalu código {code}. Se não souber, retorne apenas 'FALHA_TOTAL'.",
                )
            except:
                response_fallback = client.models.generate_content(
                    model='gemini-3.1-pro-preview',
                    contents=f"Extraia a ficha técnica do produto Magalu código {code}. Se não souber, retorne apenas 'FALHA_TOTAL'.",
                )
            result_text = get_text_safe(response_fallback)

        if (not result_text or "FALHA_TOTAL" in result_text) and input_val.startswith("http"):
            print(f"[SCRAPER] Prompt Direto falhou. Tentando extração via URL Context...")
            # Fallback 2: URL Context
            try:
                import requests
                from bs4 import BeautifulSoup
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = requests.get(input_val, headers=headers, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    text_content = soup.get_text(separator='\n')
                    
                    try:
                        res_url = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=f"Resuma os dados técnicos deste produto Magalu a partir do conteúdo bruto abaixo:\n\n{text_content[:15000]}"
                        )
                    except:
                        res_url = client.models.generate_content(
                            model='gemini-3.1-pro-preview',
                            contents=f"Resuma os dados técnicos deste produto Magalu a partir do conteúdo bruto abaixo:\n\n{text_content[:15000]}"
                        )
                    result_text = get_text_safe(res_url)
            except Exception as e:
                print(f"[SCRAPER] Erro no Fallback URL: {e}")


        if not result_text or len(result_text.strip()) < 50:
             result_text = f"⚠️ EXTRAÇÃO AUTOMÁTICA FALHOU: Não conseguimos resgatar dados para o SKU {code}. Por favor, cole a ficha técnica manualmente no campo de entrada."

        return {"text": result_text, "images": []}
    except Exception as e:
        return {"text": f"❌ Erro Crítico no Scraper: {str(e)}", "images": []}

def parse_codes(raw_input: str) -> list[str]:
    """Parseia códigos separados por vírgula, espaço ou nova linha."""
    return [c.strip() for c in re.split(r'[,\s\n]+', raw_input.strip()) if c.strip()]
