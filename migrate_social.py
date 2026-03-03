import os
import re
import uuid
import datetime
import docx
from supabase import create_client, Client
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ Erro: SUPABASE_URL ou SUPABASE_KEY não encontrados no .env")
    exit(1)

sp: Client = create_client(url, key)

ASSETS_DIR = r"c:\Users\Tiago\Desktop\PROJETOS\magalu-ai-suite\assets"

def get_docx_text(path):
    doc = docx.Document(path)
    fullText = []
    for para in doc.paragraphs:
        fullText.append(para.text)
    return '\n'.join(fullText)

def parse_filename(filename):
    # SOCIAL JAN 231203400 231203300 Ventilador de Mesa Mondial Super Power VSP-30-W.docx
    # SOCIAL LU JAN 108515500 108515400 Secador de Cabelo Taiff Style Red Vermelho 2000W.docx
    
    name = filename.replace(".docx", "")
    
    modo = "SOCIAL"
    is_lu = "LU" in name
    
    # Regex para pegar o mês (palavra em maiúsculo após SOCIAL/LU)
    # Supondo meses como JAN, FEV, MAR, etc.
    res_mes = re.search(r"(?:SOCIAL|LU)\s+([A-Z]{3})", name)
    mes = res_mes.group(1) if res_mes else ""
    
    # Regex para pegar os códigos (sequência de 9 dígitos)
    codigos = re.findall(r"\d{9}", name)
    primary_code = codigos[0] if codigos else "000000000"
    
    # Produto: o que sobra depois dos códigos
    # Encontra a posição do último código e pega o resto
    if codigos:
        last_code = codigos[-1]
        idx = name.find(last_code) + len(last_code)
        produto = name[idx:].strip()
    else:
        produto = name
        
    return {
        "modo": modo,
        "is_lu": is_lu,
        "mes": mes,
        "codigo": primary_code,
        "produto": produto,
        "todos_codigos": " ".join(codigos)
    }

def migrate():
    files = [f for f in os.listdir(ASSETS_DIR) if f.endswith(".docx") and f.startswith("SOCIAL")]
    print(f"Total de arquivos SOCIAL encontrados: {len(files)}")
    
    for f in files:
        path = os.path.join(ASSETS_DIR, f)
        info = parse_filename(f)
        content = get_docx_text(path)
        
        print(f"Processando: {f} -> Código: {info['codigo']}, Produto: {info['produto']}")
        
        try:
            # Insere no histórico
            # Campos: criado_em, codigo_produto, modo_trabalho, roteiro_gerado, modelo_llm, categoria_id (usaremos 77 Genérico por enquanto)
            data = {
                "codigo_produto": info['codigo'],
                "modo_trabalho": info['modo'],
                "roteiro_gerado": content,
                "ficha_extraida": f"Produto: {info['produto']}\nCodes: {info['todos_codigos']}\nMes: {info['mes']}\nLU: {info['is_lu']}",
                "modelo_llm": "Manual-Import",
                "tokens_entrada": 0,
                "tokens_saida": 0,
                "custo_estimado_brl": 0.0,
                "categoria_id": 77, # Genérico como fallback
                "criado_em": datetime.datetime.now().isoformat()
            }
            
            res = sp.table("nw_historico_roteiros").insert(data).execute()
            print(f"✅ Salvo com sucesso")
        except Exception as e:
            print(f"❌ Erro ao salvar {f}: {e}")

if __name__ == "__main__":
    migrate()
