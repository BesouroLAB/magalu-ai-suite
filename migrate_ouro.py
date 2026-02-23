import json
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def migrate_few_shot_to_supabase():
    # 1. Configurações
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("❌ Erro: SUPABASE_URL ou SUPABASE_KEY não configurados no .env")
        return

    sp = create_client(url, key)

    # 2. Carrega o arquivo JSON local
    kb_path = os.path.join(os.getcwd(), "kb", "few_shot_breno.json")
    if not os.path.exists(kb_path):
        print(f"⚠️ Arquivo não encontrado: {kb_path}")
        return

    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            examples = json.load(f)
    except Exception as e:
        print(f"❌ Erro ao ler JSON: {e}")
        return

    print(f"🚀 Iniciando migração de {len(examples)} roteiros para a tabela 'roteiros_ouro'...")

    success_count = 0
    for ex in examples:
        # Mapeia os campos do JSON para o banco
        # No JSON os campos eram 'produto' e 'output_depois_breno_aprovado'
        # No Banco são 'titulo_produto' e 'roteiro_perfeito'
        
        data = {
            "categoria_id": 1, # Default para migração
            "titulo_produto": ex.get("produto", "Sem Título"),
            "roteiro_perfeito": ex.get("output_depois_breno_aprovado", ""),
            "codigo_produto": "MIGRACAO_JSON"
        }

        try:
            res = sp.table("nw_roteiros_ouro").insert(data).execute()
            if hasattr(res, 'data') and len(res.data) > 0:
                success_count += 1
                print(f"✅ Migrado: {data['titulo_produto']}")
        except Exception as e:
            print(f"❌ Falha ao migrar {data['titulo_produto']}: {e}")

    print(f"\n✨ Migração concluída: {success_count}/{len(examples)} roteiros salvos no Supabase.")
    print("💡 Você já pode deletar o arquivo 'kb/few_shot_breno.json' se desejar.")

if __name__ == "__main__":
    migrate_few_shot_to_supabase()
