"""
Scraper inteligente usando Gemini Google Search + URL Context.
Usuário informa apenas o código do produto Magalu.
O Gemini pesquisa no Google, encontra a página real e extrai os dados.
"""
import os
import re
from google import genai
from google.genai.types import Tool, GenerateContentConfig
from dotenv import load_dotenv

load_dotenv()

EXTRACTION_PROMPT = """
Você é um extrator de dados de produtos do Magazine Luiza (Magalu).

TAREFA: Pesquise o produto com o código "{code}" no site magazineluiza.com.br e extraia os dados abaixo.

**FORMATO DE SAÍDA OBRIGATÓRIO:**
TÍTULO DO PRODUTO: [título completo do produto]

MARCA: [marca/fabricante]

DESCRIÇÃO DO FABRICANTE:
[descrição completa do produto, máximo 1500 caracteres]

FICHA TÉCNICA PRINCIPAL:
- [Especificação 1]: [Valor]
- [Especificação 2]: [Valor]
- [Especificação 3]: [Valor]
[...continue com todas as specs disponíveis, máximo 20]

PREÇO: [se disponível]

**REGRAS:**
- Pesquise especificamente por: site:magazineluiza.com.br "{code}"
- Extraia SOMENTE dados reais do produto encontrado. NÃO invente informações.
- Se algum dado não estiver disponível, escreva "Não informado".
- Foque nas especificações técnicas mais relevantes para um roteiro de vídeo.
- Inclua dimensões, peso, voltagem, capacidade, materiais quando disponíveis.
"""


def scrape_with_gemini(code_or_url: str) -> str:
    """
    Extrai dados de produto do Magalu usando Gemini com Google Search + URL Context.

    Args:
        code_or_url: Código do produto (ex: '240304700') ou URL completa.

    Returns:
        String com os dados estruturados do produto.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "❌ GEMINI_API_KEY não configurada. Configure no painel lateral."

    input_val = code_or_url.strip()

    # Se for URL completa, tenta extrair o código dela
    if input_val.startswith("http"):
        match = re.search(r'/p/(\w+)', input_val)
        code = match.group(1) if match else input_val
    else:
        code = re.sub(r'[^0-9a-zA-Z]', '', input_val)

    prompt = EXTRACTION_PROMPT.replace("{code}", code)

    # Método 1: Google Search + URL Context combinados (mais poderoso)
    result = _try_combined_search(prompt, api_key)
    if result:
        return result

    # Método 2: Apenas Google Search
    result = _try_google_search(prompt, api_key)
    if result:
        return result

    return f"⚠️ Não foi possível extrair dados do produto {code}.\nCole a ficha técnica manualmente."


def _try_combined_search(prompt: str, api_key: str) -> str | None:
    """Tenta com Google Search + URL Context combinados."""
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=GenerateContentConfig(
                tools=[
                    Tool(google_search={}),
                    Tool(url_context={}),
                ],
            ),
        )
        text = response.text
        if text and len(text.strip()) > 80:
            return text
    except Exception as e:
        print(f"[scraper] Combinado falhou: {e}")
    return None


def _try_google_search(prompt: str, api_key: str) -> str | None:
    """Fallback: apenas Google Search grounding."""
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=GenerateContentConfig(
                tools=[Tool(google_search={})],
            ),
        )
        text = response.text
        if text and len(text.strip()) > 80:
            return text
    except Exception as e:
        print(f"[scraper] Google Search falhou: {e}")
    return None


def parse_codes(raw_input: str) -> list[str]:
    """
    Parseia a entrada do usuário em lista de códigos.
    Aceita: vírgula, espaço, nova linha como separador.
    """
    codes = re.split(r'[,\s\n]+', raw_input.strip())
    return [c.strip() for c in codes if c.strip()]


if __name__ == "__main__":
    raw = input("Digite código(s) de produto (separados por vírgula): ")
    codes = parse_codes(raw)
    for code in codes:
        print(f"\n🔍 Pesquisando produto {code} no Magalu...")
        print(scrape_with_gemini(code))
        print("\n" + "=" * 60)
