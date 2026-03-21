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

🚨 REGRA ANTI-TROCA DE PRODUTO (CRÍTICO):
- Você DEVE encontrar o produto EXATO que corresponde ao código "{code}".
- Se o código não aparecer na URL ou na página encontrada, responda: "ERRO: Produto não encontrado ou dados indisponíveis."
- NÃO substitua por um produto parecido, similar ou da mesma marca. É ESTE código ou ERRO.
- Se a pesquisa retornar vários resultados, escolha APENAS o que contém exatamente o código "{code}".

**FORMATO DE SAÍDA OBRIGATÓRIO:**
CÓDIGO CONFIRMADO: {code}
TÍTULO: [Nome completo do produto]
MARCA: [Fabricante]
LINHA/NOME COMERCIAL: [Nome de marketing da linha, ex: "UltraGear", "Galaxy M53", "Soundgear Clips", "Force". Se não houver, escreva "N/A"]
DESCRIÇÃO: [Resumo das funcionalidades principais]
FICHA TÉCNICA:
- [Item]: [Valor]
...

VOLTAGEM: [110V / 220V / Bivolt / Não se aplica]
CORES DISPONÍVEIS: [Liste TODAS as cores/variantes visíveis na página do produto ou em SKUs relacionados. Se houver apenas uma cor, informe "Apenas [cor]". Se não encontrar, escreva "Não informado"]
FEATURES PRÁTICAS: [Liste recursos "escondidos" que costumam ficar no final da ficha ou na descrição longa, como: dreno, rodízios, fechadura, painel de controle, suportes, bandejas, grades organizadoras, tipo de pé/base, classificação energética, certificações. Se não encontrar nenhum, escreva "Nenhum identificado"]

**REGRAS DE PESQUISA E REDAÇÃO:**
- Use a ferramenta de busca do Google para encontrar a ficha técnica real.
- Tente pesquisar exatamente por: site:magazineluiza.com.br "{code}"
- Se não achar, tente pesquisar por: "{code}" magazineluiza
- 🚨 REGRA ANTI-PLÁGIO (MUITO IMPORTANTE): Você NÃO DEVE copiar textos inteiros da internet palavra por palavra.
- RESUMA E PARAFRASEIE a "DESCRIÇÃO" com suas próprias palavras, mantendo apenas os fatos técnicos importantes. Sintetize a informação para evitar bloqueios de direitos autorais.
- Na "FICHA TÉCNICA", organize os dados brutos de forma concisa.
- Para CORES DISPONÍVEIS, verifique se a página mostra seletores de cor ou SKUs irmãos com variações. Isso é importante para o roteiro.
- Para FEATURES PRÁTICAS, leia a descrição ATÉ O FINAL — os diferenciais práticos costumam estar escondidos no meio ou no fim do texto.
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
            # Fallback 1: Prompt Direto sem Tools — COM ANCORAGEM DE CÓDIGO
            fallback_prompt = (
                f"Extraia a ficha técnica do produto do Magazine Luiza com o código EXATO: {code}.\n"
                f"🚨 NÃO retorne dados de outro produto. Se não souber dados desse código específico, retorne apenas 'FALHA_TOTAL'.\n"
                f"Comece a resposta com: CÓDIGO CONFIRMADO: {code}"
            )
            try:
                response_fallback = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=fallback_prompt,
                )
            except:
                response_fallback = client.models.generate_content(
                    model='gemini-3.1-pro-preview',
                    contents=fallback_prompt,
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
                            contents=f"Resuma os dados técnicos deste produto Magalu (código {code}) a partir do conteúdo bruto abaixo. Comece com CÓDIGO CONFIRMADO: {code}\n\n{text_content[:15000]}"
                        )
                    except:
                        res_url = client.models.generate_content(
                            model='gemini-3.1-pro-preview',
                            contents=f"Resuma os dados técnicos deste produto Magalu (código {code}) a partir do conteúdo bruto abaixo. Comece com CÓDIGO CONFIRMADO: {code}\n\n{text_content[:15000]}"
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
