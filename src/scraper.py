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
1. Acesse DIRETAMENTE a página do produto através da URL: https://www.magazineluiza.com.br/produto/p/{code}/br/brmd/?seller_id=magazineluiza
2. Caso a URL direta não seja o suficiente, faça a busca exata no Google por: site:magazineluiza.com.br "{code}"
3. Extraia os dados técnicos reais desse produto a partir do site oficial.

🚨 CONTEXTO DO ROTEIRO: {modo}
- Se for NW (NewWeb): Foco total em ficha técnica, precisão de medidas e materiais.
- Se for 3D (NewWeb 3D): Foco em detalhes físicos, texturas, partes móveis, e ângulos visuais (essencial para animação).
- Se for SOCIAL: Foco no "lifestyle", diferenciais visuais e "uau" do produto.
- Se for REVIEW: Foco em pontos fortes que os clientes costumam elogiar.

🚨 REGRA ANTI-TROCA DE PRODUTO (CRÍTICO):
- Você DEVE encontrar o produto EXATO que corresponde ao código "{code}".
- Se o código não aparecer na URL ou na página encontrada, responda: "ERRO: Produto não encontrado ou dados indisponíveis."
- NÃO substitua por um produto parecido, similar ou da mesma marca. É ESTE código ou ERRO.

🚨 REGRA DE PRODUTO COMBO / KIT:
Muitos produtos Magalu são COMBOS. Identifique se o título contém "(Box + Colchão)", "Conjunto", "Kit", etc.
Se for COMBO: Extraia a ficha de CADA componente separadamente.

🚨 REGRA DE DETALHES VISUAIS (MUITO IMPORTANTE PARA BRINQUEDOS/LEGO/MODA):
- Extraia todos os detalhes concretos: peças inclusas, personagens, mecânicas (ex: "tem rodas", "brilha no escuro"), acessórios.
- Para roupas/móveis: Descreva texturas e acabamentos.

**FORMATO DE SAÍDA OBRIGATÓRIO:**
CÓDIGO CONFIRMADO: {code}
TIPO_PRODUTO: [SIMPLES | COMBO | COMBO_PARCIAL]
TÍTULO: [Nome completo do produto]
MARCA: [Fabricante]
URLS_IMAGENS: [Liste até 5 URLs diretas de imagens do produto separadas por vírgula. Busque URLs que contenham 'static.mlcdn.com.br'.]
LINHA/NOME COMERCIAL: [Ex: "UltraGear", "Galaxy M53"]
FRANQUIA/UNIVERSO: [Ex: Star Wars, Marvel. Se não houver, N/A]
DESCRIÇÃO: [Resumo factual e sem marketing]
FICHA TÉCNICA:
- [Item]: [Valor]
...
VOLTAGEM: [110V / 220V / Bivolt / N/A]
CORES DISPONÍVEIS: [Liste todas as variantes visíveis]
FEATURES PRÁTICAS: [Recursos úteis escondidos]
"""

def scrape_with_gemini(code_or_url: str, api_key: str | None = None, modo: str = "NW") -> dict:
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

    prompt = EXTRACTION_PROMPT.format(code=code, modo=modo)

    try:
        os.environ.setdefault("GOOGLE_API_KEY", api_key)
        client = genai.Client(api_key=api_key, http_options={'timeout': 150000})
        result_text = None
        
        config = GenerateContentConfig(
            tools=[Tool(google_search=GoogleSearch())],
            temperature=0.0
        )
        
        import time as _time
        response = None
        scraper_max_retries = 3
        scraper_base_wait = 10
        
        def _call_with_retry(model_name, prompt_text, cfg, retries=scraper_max_retries):
            for attempt in range(retries + 1):
                try:
                    return client.models.generate_content(
                        model=model_name, 
                        contents=prompt_text,
                        config=cfg
                    )
                except Exception as e:
                    err_str = str(e)
                    is_retryable = any(code in err_str for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"])
                    if is_retryable and attempt < retries:
                        _time.sleep(scraper_base_wait * (2 ** attempt))
                    else:
                        raise e
        
        try:
            response = _call_with_retry('gemini-2.0-flash', prompt, config)
        except:
            try:
                response = _call_with_retry('gemini-3.1-pro-preview', prompt, config)
            except:
                response = None
        
        def get_text_safe(resp):
            try:
                return resp.text if resp and hasattr(resp, 'text') else None
            except:
                return None

        result_text = get_text_safe(response)
        
        # Parsing de imagens da resposta do Gemini
        image_urls = []
        if result_text:
            img_match = re.search(r'URLS_IMAGENS:\s*([^\n]+)', result_text, re.IGNORECASE)
            if img_match:
                urls_raw = img_match.group(1).split(',')
                image_urls = [u.strip() for u in urls_raw if 'http' in u]

        if not result_text or len(result_text.strip()) < 50 or "ERRO:" in result_text:
            # Fallback 1: Prompt Direto
            fallback_prompt = f"Extraia a ficha técnica e 3 URLs de imagens (static.mlcdn.com.br) do produto Magalu código: {code}. Comece com CÓDIGO CONFIRMADO: {code}"
            try:
                response_fallback = _call_with_retry('gemini-2.0-flash', fallback_prompt, GenerateContentConfig(temperature=0.0), retries=2)
                result_text = get_text_safe(response_fallback)
                if result_text:
                    img_match = re.search(r'(?:URLS_IMAGENS:|Imagens:)\s*([^\n]+)', result_text, re.IGNORECASE)
                    if img_match:
                        urls_raw = img_match.group(1).split(',')
                        image_urls.extend([u.strip() for u in urls_raw if 'http' in u])
            except:
                pass

        # Fallback 2: Extração via URL Context + BeautifulSoup (se for URL)
        if (not result_text or "FALHA_TOTAL" in result_text) and input_val.startswith("http"):
            try:
                import requests
                from bs4 import BeautifulSoup
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = requests.get(input_val, headers=headers, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    text_content = soup.get_text(separator='\n')
                    # Tenta capturar imagens da Magalu no HTML
                    if not image_urls:
                        imgs = soup.find_all('img', src=re.compile(r'static\.mlcdn\.com\.br'))
                        image_urls = [img['src'] for img in imgs if 'src' in img.attrs][:5]

                    res_url = client.models.generate_content(
                        model='gemini-2.0-flash',
                        contents=f"Resuma os dados técnicos deste produto (código {code}). Comece com CÓDIGO CONFIRMADO: {code}\n\n{text_content[:15000]}"
                    )
                    result_text = get_text_safe(res_url)
            except:
                pass

        if not result_text or len(result_text.strip()) < 50:
             result_text = f"⚠️ EXTRAÇÃO AUTOMÁTICA FALHOU: SKU {code}. Cole a ficha manualmente."

        # Limpeza de duplicatas nas URLs
        image_urls = list(dict.fromkeys(image_urls))

        return {"text": result_text, "image_urls": image_urls}
    except Exception as e:
        return {"text": f"❌ Erro Crítico no Scraper: {str(e)}", "image_urls": []}

def parse_codes(raw_input: str) -> list[str]:
    """Parseia códigos separados por vírgula, espaço ou nova linha (legado)."""
    return [c.strip() for c in re.split(r'[,\s\n]+', raw_input.strip()) if c.strip()]


def parse_grouped_input(raw_input: str) -> list[dict]:
    """
    Parseia input agrupado onde cada linha = 1 roteiro.
    Códigos na mesma linha = variantes do mesmo produto.
    URLs (http...) = link de vídeo do fornecedor.
    
    Retorna lista de dicts:
      [{"codes": ["232878800"], "video": None},
       {"codes": ["232879000", "232879500"], "video": "https://..."}]
    """
    groups = []
    for line in raw_input.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        
        tokens = re.split(r'[,\s]+', line)
        codes = []
        video = None
        
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            if token.startswith('http'):
                video = token
            else:
                clean = re.sub(r'[^0-9a-zA-Z]', '', token)
                if len(clean) >= 3:
                    codes.append(clean)
        
        if codes:
            groups.append({"codes": codes, "video": video})
    
    return groups


def detect_variants(dict_fichas: dict[str, dict]) -> dict:
    """
    Compara fichas técnicas de múltiplos SKUs do mesmo produto.
    Detecta o que varia entre eles (cor, tamanho, voltagem).
    """
    if len(dict_fichas) <= 1:
        return {"tipo_variante": None, "resumo": "", "detalhes": {}}
    
    sku_data = {}
    for codigo, data in dict_fichas.items():
        texto = data.get("text", "") if isinstance(data, dict) else str(data)
        info = {"codigo": codigo}
        
        # Extração precisa
        v_match = re.search(r'VOLTAGEM:\s*([^\n]+)', texto, re.IGNORECASE)
        if v_match: info["voltagem"] = v_match.group(1).strip()
            
        c_match = re.search(r'^- (?:Cor|Color)[\s:]+([^\n]+)', texto, re.MULTILINE | re.IGNORECASE)
        if not c_match: c_match = re.search(r'CORES DISPONÍVEIS:\s*(?:Apenas\s+)?([^\n]+)', texto, re.IGNORECASE)
        if c_match:
            cor_val = c_match.group(1).strip()
            # Filtro: se for muito longo ou contiver 'Pintura', geralmente não é o nome da cor isolado
            if len(cor_val) < 30:
                info["cor"] = cor_val

        t_match = re.search(r'^- (?:Tamanho|Dimensões|Medidas|Peso)[\s:]+([^\n]+)', texto, re.MULTILINE | re.IGNORECASE)
        if t_match: info["tamanho"] = t_match.group(1).strip()
            
        sku_data[codigo] = info

    # Só é variante se for DIFERENTE
    sets = {"cor": set(), "tamanho": set(), "voltagem": set()}
    for info in sku_data.values():
        for k in sets:
            if k in info: sets[k].add(info[k])
        
    tipos = []
    resumos = []
    if len(sets["cor"]) > 1:
        tipos.append("cor")
        resumos.append(f"Disponível em {len(sets['cor'])} cores: {', '.join(sorted(list(sets['cor'])))}")
    if len(sets["tamanho"]) > 1:
        tipos.append("tamanho")
        resumos.append(f"Disponível em {len(sets['tamanho'])} variações de tamanho/peso")
    if len(sets["voltagem"]) > 1:
        tipos.append("voltagem")
        resumos.append(f"Disponível em {len(sets['voltagem'])} voltagens")

    return {
        "tipo_variante": "|".join(tipos) if tipos else None,
        "resumo": " / ".join(resumos) if resumos else "",
        "detalhes": sku_data
    }
