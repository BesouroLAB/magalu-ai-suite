import requests
from bs4 import BeautifulSoup
import re

def scrape_magalu_product(url):
    """
    Raspa os dados essenciais de uma página de produto do Magalu.
    Foca no Título, Descrição e Ficha Técnica, ignorando headers, footers e comentários.
    """
    try:
        # Headers para simular um navegador comum e evitar bloqueios imediatos
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Extrair Título (Geralmente em um h1 com um data-testid específico)
        title_element = soup.find('h1', {'data-testid': 'heading-product-title'})
        title = title_element.get_text(strip=True) if title_element else "Título não encontrado"
        
        # 2. Extrair Descrição
        # A descrição no magalu geralmente fica dentro de uma div com data-testid='rich-content-container'
        desc_element = soup.find('div', {'data-testid': 'rich-content-container'})
        description = desc_element.get_text(separator='\n', strip=True) if desc_element else ""
        
        # 3. Extrair Ficha Técnica (Features)
        features = {}
        # As especificações geralmente estão em uma tabela em uma div específica
        specs_table = soup.find('table', {'data-testid': 'product-specs-table'})
        if specs_table:
            rows = specs_table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) == 2:
                    key = cols[0].get_text(strip=True)
                    val = cols[1].get_text(strip=True)
                    features[key] = val
                    
        # Se as classes exatas do magalu falharem ou mudarem, fallback heurístico:
        if not description:
            # Procura qualquer coisa que pareça a descrição
            possible_desc = soup.find(text=re.compile('Descrição', re.IGNORECASE))
            if possible_desc and possible_desc.parent:
                desc_container = possible_desc.parent.find_next_sibling()
                if desc_container:
                     description = desc_container.get_text(separator=' ', strip=True)[:1000] # Pega primeiros 1000 chars
                     
        result = f"TÍTULO DO PRODUTO: {title}\n\n"
        result += f"DESCRIÇÃO DO FABRICANTE:\n{description[:1500]}\n\n" # Limitamos tamanho
        
        result += "FICHA TÉCNICA PRINCIPAL:\n"
        for k, v in list(features.items())[:15]: # Limitamos a 15 specs mais importantes
            result += f"- {k}: {v}\n"
            
        return result
        
    except Exception as e:
        return f"Erro ao raspar a URL: {str(e)}\nCertifique-se de que é um link válido de produto."

if __name__ == "__main__":
    # Teste rápido se rodar o arquivo direto
    test_url = input("Cole uma URL de produto do magalu para testar o scraper: ")
    print("\nIniciando scraping...\n")
    print(scrape_magalu_product(test_url))
