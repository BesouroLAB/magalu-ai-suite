import os

PROJECT_ROOT = 'c:/Users/Tiago/Desktop/PROJETOS/magalu-ai-suite'
files_to_update = ['src/app.py', 'src/agent.py', 'migrate_ouro.py', 'supabase_schema.sql']

replacements = {
    '"historico_roteiros"': '"nw_historico_roteiros"',
    '"roteiros_ouro"': '"nw_roteiros_ouro"',
    '"treinamento_persona_lu"': '"nw_treinamento_persona_lu"',
    '"treinamento_fonetica"': '"nw_treinamento_fonetica"',
    '"treinamento_estruturas"': '"nw_treinamento_estruturas"',
    '"treinamento_nuances"': '"nw_treinamento_nuances"',
    '"categorias"': '"nw_categorias"',
    'table historico_roteiros': 'table nw_historico_roteiros',
    'table roteiros_ouro': 'table nw_roteiros_ouro',
    'table treinamento_persona_lu': 'table nw_treinamento_persona_lu',
    'table treinamento_fonetica': 'table nw_treinamento_fonetica',
    'table treinamento_estruturas': 'table nw_treinamento_estruturas',
    'table treinamento_nuances': 'table nw_treinamento_nuances',
    'table categorias': 'table nw_categorias',
    'table if not exists historico_roteiros': 'table if not exists nw_historico_roteiros',
    'table if not exists roteiros_ouro': 'table if not exists nw_roteiros_ouro',
    'table if not exists treinamento_persona_lu': 'table if not exists nw_treinamento_persona_lu',
    'table if not exists treinamento_fonetica': 'table if not exists nw_treinamento_fonetica',
    'table if not exists treinamento_estruturas': 'table if not exists nw_treinamento_estruturas',
    'table if not exists treinamento_nuances': 'table if not exists nw_treinamento_nuances',
    'table if not exists categorias': 'table if not exists nw_categorias',
    'references categorias': 'references nw_categorias',
    'into categorias': 'into nw_categorias',
    'nw_nw_': 'nw_' # Previne rename duplo se rodar 2x
}

for fp in files_to_update:
    filepath = os.path.join(PROJECT_ROOT, fp)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for k, v in replacements.items():
        content = content.replace(k, v)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print('Renamed tables successfully in files!')
