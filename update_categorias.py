import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')

if not url or not key:
    print('Erro: Credenciais Supabase ausentes.')
    exit()

supabase = create_client(url, key)

# Lista exata fornecida pelo usuário + Tom de Voz Estratégico Magalu
categorias_novas = [
    {"nome": "Áudio", "tom_de_voz": "Experiência Sonora; Foco em imersão, qualidade de som e entretenimento."},
    {"nome": "Ar e Ventilação", "tom_de_voz": "Conforto Térmico; Foco em bem-estar e eficiência para a casa."},
    {"nome": "Bebês", "tom_de_voz": "Cuidado e Segurança; Tom acolhedor para o desenvolvimento e paz dos pais."},
    {"nome": "Beleza e Perfumaria", "tom_de_voz": "Autocuidado; Foco em autoestima, fragrâncias e frescor."},
    {"nome": "Beleza e Saúde", "tom_de_voz": "Bem-estar; Foco em cuidados pessoais e rotina saudável."},
    {"nome": "Brinquedos", "tom_de_voz": "Diversão e Aprendizado; Tom lúdico, seguro e criativo."},
    {"nome": "Casa e Construção", "tom_de_voz": "Transformação; Foco em reforma, qualidade e segurança da obra."},
    {"nome": "Casa Conectada", "tom_de_voz": "Modernidade; Foco em automação e facilidade digital."},
    {"nome": "Casa Inteligente", "tom_de_voz": "Tecnologia Prática; Descomplicar a automação para o dia a dia."},
    {"nome": "Celulares e Smartphones", "tom_de_voz": "Conectividade; Foco em câmeras, bateria e produtividade."},
    {"nome": "Colchões", "tom_de_voz": "Descanso Master; Enfatizar qualidade do sono e saúde da coluna."},
    {"nome": "Comércio e Indústria", "tom_de_voz": "Profissional; Foco em eficiência, durabilidade e produtividade."},
    {"nome": "Eletrodomésticos", "tom_de_voz": "Cozinha e Lavanderia; Foco em economia de energia e praticidade."},
    {"nome": "Eletroportáteis", "tom_de_voz": "Facilidade; Pequenos itens que salvam a rotina doméstica."},
    {"nome": "Esporte e Lazer", "tom_de_voz": "Vida Ativa; Motivação, saúde e resistência dos materiais."},
    {"nome": "Ferramentas", "tom_de_voz": "Resolutivo; Foco no 'faça você mesmo' com precisão."},
    {"nome": "Games", "tom_de_voz": "Imersão Gamer; Linguagem técnica, mas fluida (FPS, specs, latência)."},
    {"nome": "Informática", "tom_de_voz": "Produtividade; Foco em trabalho e estudos sem complicação."},
    {"nome": "Mercado", "tom_de_voz": "Conveniência; Foco em abastecimento, frescor e economia."},
    {"nome": "Moda", "tom_de_voz": "Estilo Próprio; Foco em tendências, conforto e caimento."},
    {"nome": "Móveis", "tom_de_voz": "Lar Doce Lar; Foco em design, espaço e durabilidade."},
    {"nome": "Tablets", "tom_de_voz": "Mobilidade; Foco em leitura, estudo e entretenimento portátil."},
    {"nome": "Tablets, iPads e E-reader", "tom_de_voz": "Conexão Digital; Foco em telas de qualidade e versatilidade."},
    {"nome": "TV e Vídeo", "tom_de_voz": "Entretenimento; Foco em resolução, som e experiência de cinema."},
    {"nome": "Utilidades Domésticas", "tom_de_voz": "Organização; Detalhes que facilitam a vida na cozinha."},
    {"nome": "Genérico", "tom_de_voz": "Otimismo Prudente; Padrão Lu do Magalu para diversos itens."}
]

print(f"Atualizando nw_categorias com a lista exata do usuário...")
try:
    # Remove as antigas para manter apenas a lista oficial
    supabase.table("nw_categorias").delete().neq("id", 0).execute() 
    
    for cat in categorias_novas:
        supabase.table("nw_categorias").insert(cat).execute()
    print(f"Sucesso! {len(categorias_novas)} Categorias atualizadas!")
except Exception as e:
    print(f"Erro ao atualizar: {e}")
