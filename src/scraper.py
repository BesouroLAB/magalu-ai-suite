"""
Scraper inteligente usando Gemini Google Search + URL Context.
Usuário informa apenas o código do produto Magalu.
O Gemini pesquisa no Google, encontra a página real e extrai os dados.
"""
import os
import re
import requests
from bs4 import BeautifulSoup
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

**REGRAS RIGOROSAS DE FONTE DE DADOS:**
1. Pesquise primariamente e especificamente por: site:magazineluiza.com.br "{code}".
2. Se a ficha da Magalu não possuir os dados técnicos necessários, você pode usar a ferramenta de busca para procurar **EXCLUSIVAMENTE no site oficial do FABRICANTE**. 
3. É TERMINANTEMENTE PROIBIDO extrair dados de concorrentes (Amazon, Mercado Livre, Casas Bahia, etc).
4. Se você extrair qualquer informação do site do fabricante (fora da Magalu), adicione uma linha no final da sua resposta exatamente assim: "FONTE EXTERNA: [coloque a URL do fabricante aqui]".
5. Extraia SOMENTE dados reais do produto encontrado. NÃO invente informações.
6. Se algum dado não estiver disponível sequer no fabricante, escreva "Não informado".
7. Foque nas especificações técnicas mais relevantes para um roteiro de vídeo (dimensões, peso, voltagem, materiais, capacidades).
"""


def _extract_images(code: str, max_images: int = 5):
    """Tenta baixar imagens da galeria do produto e retorna também o texto bruto da página."""
    images = []
    page_text = ""
    try:
        url = f"https://www.magazineluiza.com.br/p/{code}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair texto bruto da página para ajudar o Gemini caso a busca falhe
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            text_blocks = soup.stripped_strings
            page_text = " ".join(text_blocks)
            
            img_urls = []
            
            # 1. Tenta a og:image primeiro (garante pelo menos a principal)
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                img_urls.append(og_image['content'])
                
            # 2. Varrer código por imagens de showcase/produto (regex)
            encontradas = re.findall(r'https://[^"\'\s]+\.(?:jpg|jpeg|png|webp)', response.text)
            
            for img in encontradas:
                if 'showcase' in img or 'produto' in img or 'magazineluiza.com.br' in img:
                    # Limpeza extra para evitar ícones minúsculos e links quebrados
                    if 'thumb' not in img.lower() and 'icon' not in img.lower():
                        img_urls.append(img)
            
            # Remove duplicatas mantendo a ordem (og:image primeiro)
            seen = set()
            unique_urls = [x for x in img_urls if not (x in seen or seen.add(x))]
            
            for img_url in unique_urls[:max_images]:
                try:
                    img_response = requests.get(img_url, timeout=5)
                    if img_response.status_code == 200:
                        mime = img_response.headers.get('content-type', 'image/jpeg')
                        images.append({"bytes": img_response.content, "mime": mime})
                except Exception:
                    continue
                    
    except Exception as e:
        print(f"[scraper] Erro ao extrair imagens do produto {code}: {e}")
        
    return images, page_text


def scrape_with_gemini(code_or_url: str) -> dict:
    """
    Extrai dados de produto do Magalu (Texto + Imagem).

    Args:
        code_or_url: Código do produto (ex: '240304700') ou URL completa.

    Returns:
        Dicionário com 'text' (dados estruturados) e 'images' (lista de dicts com 'bytes' e 'mime').
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"text": "❌ GEMINI_API_KEY não configurada. Configure no painel lateral.", "images": []}

    input_val = code_or_url.strip()

    # Se for URL completa, tenta extrair o código dela
    if input_val.startswith("http"):
        match = re.search(r'/p/(\w+)', input_val)
        code = match.group(1) if match else input_val
    else:
        code = re.sub(r'[^0-9a-zA-Z]', '', input_val)

    prompt = EXTRACTION_PROMPT.replace("{code}", code)

    # Tenta extrair as imagens e texto direto da página
    images_list, raw_page_text = _extract_images(code)
    
    # Se conseguiu o texto bruto, fornece como dica pesada para o Gemini
    if raw_page_text and len(raw_page_text) > 200:
        prompt += f"\n\n**DICA: AQUI ESTÁ TODO O TEXTO DA PÁGINA DESSE PRODUTO, CASO A BUSCA GOOGLE FALHE:**\n{raw_page_text[:8000]}"
    
    result_text = None
    # Método 1: Google Search + URL Context combinados (mais poderoso)
    # Usamos 1.5-flash pela estabilidade comprovada com ferramentas de pesquisa em 2026
    result = _try_combined_search(prompt, api_key)
    if result:
        result_text = result
    else:
        # Método 2: Apenas Google Search
        result = _try_google_search(prompt, api_key)
        if result:
            result_text = result

    if not result_text:
        result_text = f"⚠️ Não foi possível extrair dados do produto {code}.\nCole a ficha técnica manualmente."

    return {
        "text": result_text,
        "images": images_list
    }

import google.generativeai as genai_old

def _try_combined_search(prompt: str, api_key: str) -> str | None:
    """Tenta com Google Search + URL Context combinados usando SDK v1 para estabilidade."""
    try:
        genai_old.configure(api_key=api_key)
        model = genai_old.GenerativeModel('gemini-2.5-flash', tools='google_search_retrieval')
        response = model.generate_content(prompt)
        text = response.text
        if text and len(text.strip()) > 80:
            return text
    except Exception as e:
        print(f"[scraper] Combinado falhou (v1 auth): {e}")
    return None

def _try_google_search(prompt: str, api_key: str) -> str | None:
    """Fallback: apenas Google Search usando SDK v1."""
    try:
        genai_old.configure(api_key=api_key)
        model = genai_old.GenerativeModel('gemini-2.5-flash', tools='google_search_retrieval')
        response = model.generate_content(prompt)
        text = response.text
        if text and len(text.strip()) > 80:
            return text
    except Exception as e:
        print(f"[scraper] Google Search Fallback falhou: {e}")
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
