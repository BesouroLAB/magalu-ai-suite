
import os
from supabase import create_client
from dotenv import load_dotenv
import datetime
import pytz

# Carrega variáveis de ambiente
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERROR] SUPABASE_URL ou SUPABASE_KEY não encontrados no .env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fuso horário de SP
sp_tz = pytz.timezone('America/Sao_Paulo')
now_sp = datetime.datetime.now(sp_tz)

roteiros = [
    {
        "codigo": "237724800",
        "title": "Colchão Casal Gazin de Espuma D33 14x138x188cm",
        "content": """Cliente: Magalu
Roteirista: Tiago Fernandes – Data: 27/01/2026
Produto: NW 3D FEV 237724800 Colchão Casal Gazin de Espuma D33 14x138x188cm

- O Colchão Casal Supreme, da Gazin, tem espuma D33 pra garantir um sono muito mais confortável.
Imagem: Colocar régua de medidas + Câmera orbitando o colchão inteiro em um ambiente clean e iluminado.

- A lateral em tecido plano e poliéster não acumula poeira e é fácil de limpar.
Imagem: Close na lateral do colchão, destacando a textura lisa do tecido plano.

- Inclusive, ele tem proteção antialérgica, viu?
Imagem: mostrar detalhe do colchão mais de perto 

- E com nível de conforto intermediário, ele aguenta até 100kg por pessoa.
Imagem: A câmera desce levemente, focando na superfície do colchão para mostrar a firmeza da espuma.

- E uma dica pra aumentar a durabilidade do colchão é virar e girar ele de tempos em tempos.
Imagem: A câmera se afasta para mostrar o colchão de perfil, enfatizando a altura e as dimensões totais.

- Conforto e qualidade pro seu sono, tem no Magalu!
Lettering: #TemnoMagalu"""
    },
    {
        "codigo": "237725200",
        "title": "Colchão Solteiro Gazin de Espuma D33 15x88x188cm",
        "content": """Cliente: Magalu
Roteirista: Tiago Fernandes – Data: 27/01/2026
Produto: NW 3D FEV 237725200 Colchão Solteiro Gazin de Espuma D33 15x88x188cm

- Com densidade D33, o Colchão Solteiro Supreme, da Gazin, é a escolha certa pra quem busca um sono tranquilo e de qualidade.
Imagem: colocar régua de medida + Câmera viaja pela superfície do colchão, destacando a textura do tecido.

- Ele é feito 100% em espuma e oferece um nível de conforto intermediário, ou seja, tem o suporte ideal pra sua coluna descansar.
Imagem: fazer uma leve pressão sob o colchão mostrando a espuma cedendo levemente e voltando.

- O revestimento lateral é em tecido plano que não acumula poeira e é super fácil de limpar. Já o tecido é poliéster com proteção antialérgica.
Imagem: Zoom macro na trama do tecido - ícone antialérgico.

- Ah, e ele suporta até 100kg tranquilamente. Mesmo assim, uma dica é virar e girar o colchão regularmente pra aumentar a durabilidade dele.
Imagem: Linhas de cota aparecem medindo a altura (15cm) e a largura (88cm).

- Tudo pra melhorar a qualidade do seu sono, tem no Magalu!
Lettering: #TemnoMagalu"""
    }
]

def insert_roteiros():
    success_count = 0
    for r in roteiros:
        record = {
            "codigo_produto": r["codigo"],
            "modo_trabalho": "NW 3D",
            "roteiro_gerado": r["content"],
            "ficha_extraida": f"Importação Manual: {r['title']}",
            "modelo_llm": "Manual Import",
            "tokens_entrada": 0,
            "tokens_saida": 0,
            "custo_estimado_brl": 0.0,
            "status": "gerado"
        }
        
        try:
            supabase.table("nw3d_historico_roteiros").insert(record).execute()
            print(f"[OK] Inserido: {r['codigo']} - {r['title']}")
            success_count += 1
        except Exception as e:
            print(f"[ERROR] Falha ao inserir {r['codigo']}: {e}")
            
    print(f"\nConcluído. {success_count} de {len(roteiros)} roteiros inseridos na base NW 3D.")

if __name__ == "__main__":
    insert_roteiros()
