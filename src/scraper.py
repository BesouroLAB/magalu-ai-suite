"""
Scraper inteligente usando Gemini URL Context Tool.
Usuário informa apenas o código do produto Magalu.
O sistema monta a URL automaticamente e o Gemini extrai os dados.
"""
import os
import re
from google import genai
from google.genai.types import Tool, GenerateContentConfig
from dotenv import load_dotenv

load_dotenv()

# Template fixo Magalu — o redirect automático corrige o slug do produto
MAGALU_URL_TEMPLATE = "https://www.magazineluiza.com.br/_/p/{code}/?seller_id=magazineluiza"

EXTRACTION_PROMPT = """
Você é um extrator de dados de produtos. Acesse a URL do produto fornecida e extraia as seguintes informações de forma COMPLETA e ESTRUTURADA:

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
- Extraia SOMENTE dados reais da página. NÃO invente informações.
- Se algum dado não estiver disponível, escreva "Não informado".
- Foque nas especificações técnicas mais relevantes para um roteiro de vídeo.
- Inclua dimensões, peso, voltagem, capacidade, materiais quando disponíveis.
"""


def build_magalu_url(code: str) -> str:
    """Monta a URL do Magalu a partir do código do produto."""
    clean_code = re.sub(r'[^0-9a-zA-Z]', '', code.strip())
    return MAGALU_URL_TEMPLATE.format(code=clean_code)


def scrape_with_gemini(code_or_url: str) -> str:
    """
    Extrai dados de produto do Magalu usando Gemini URL Context Tool.

    Args:
        code_or_url: Código do produto (ex: '240304700') ou URL completa.

    Returns:
        String com os dados estruturados do produto.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "❌ GEMINI_API_KEY não configurada. Configure no painel lateral."

    # Detecta se é código ou URL completa
    input_val = code_or_url.strip()
    if input_val.startswith("http"):
        url = input_val
    else:
        url = build_magalu_url(input_val)

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{EXTRACTION_PROMPT}\n\nURL DO PRODUTO: {url}",
            config=GenerateContentConfig(
                tools=[Tool(url_context={})],
            ),
        )

        extracted = response.text
        if not extracted or len(extracted.strip()) < 50:
            return _fallback_google_search(url, api_key)

        return extracted

    except Exception as e:
        error_msg = str(e)
        # Se URL Context falhar, tenta Google Search como fallback
        return _fallback_google_search(url, api_key)


def _fallback_google_search(url: str, api_key: str) -> str:
    """Fallback: usa Google Search grounding se URL Context não estiver disponível."""
    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                f"{EXTRACTION_PROMPT}\n\n"
                f"Pesquise o produto desta URL e extraia os dados: {url}"
            ),
            config=GenerateContentConfig(
                tools=[Tool(google_search={})],
            ),
        )

        extracted = response.text
        if not extracted or len(extracted.strip()) < 50:
            return f"⚠️ Não foi possível extrair dados para: {url}\nCole a ficha técnica manualmente."

        return extracted

    except Exception as e:
        return f"❌ Erro no fallback: {str(e)}\nCole a ficha técnica manualmente."


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
        url = build_magalu_url(code)
        print(f"\n🔗 URL: {url}")
        print("⏳ Extraindo dados com Gemini...\n")
        print(scrape_with_gemini(code))
        print("\n" + "=" * 60)
