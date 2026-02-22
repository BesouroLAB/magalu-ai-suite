import requests
from bs4 import BeautifulSoup

url = 'https://www.magazineluiza.com.br/boneco-de-vinil-gigante-marvel-hulk-comics-45-cm-tcs/p/agga8ad40g/br/bnco/'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.content, 'html.parser')

title = soup.find('title')
print(f"TITLE TAG: {title.string if title else None}")

h1s = soup.find_all('h1')
print(f"H1s encontrados: {len(h1s)}")
for h in h1s:
    print(f"  H1: {h.get_text(strip=True)[:100]}")

scripts = soup.find_all('script')
print(f"Total scripts: {len(scripts)}")
for s in scripts[:20]:
    sid = s.get('id', '')
    src = s.get('src', '')[:80]
    has_text = len(s.string) if s.string else 0
    print(f"  id={sid} src={src} textlen={has_text}")

# Procura dados embutidos em scripts inline
for s in scripts:
    if s.string and ('product' in s.string.lower()[:200] or 'titulo' in s.string.lower()[:200]):
        print(f"\n=== SCRIPT COM PRODUCT DATA (primeiros 600 chars) ===")
        print(s.string[:600])
        print("===")
        break

# Procura meta tags
metas = soup.find_all('meta')
for m in metas:
    prop = m.get('property', '') or m.get('name', '')
    if 'title' in prop.lower() or 'description' in prop.lower() or 'product' in prop.lower():
        print(f"META: {prop} = {m.get('content', '')[:150]}")
