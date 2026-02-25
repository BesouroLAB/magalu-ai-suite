import os

app_path = r"c:\Users\Tiago\Desktop\PROJETOS\magalu-ai-suite\src\app.py"
with open(app_path, 'r', encoding='utf-8') as f:
    text = f.read()

tables = [
    'nw_historico_roteiros', 
    'nw_roteiros_ouro', 
    'nw_treinamento_fonetica', 
    'nw_treinamento_estruturas', 
    'nw_treinamento_nuances'
]

# Substitui ocorrências em aspas duplas e simples
for t in tables:
    base = t.replace("nw_", "")
    text = text.replace(f'"{t}"', f'f"{{st.session_state.get(\'table_prefix\', \'nw_\')}}{base}"')
    text = text.replace(f"'{t}'", f'f"{{st.session_state.get(\'table_prefix\', \'nw_\')}}{base}"')

# Adiciona o prefixo no RoteiristaAgent
text = text.replace(
    "RoteiristaAgent(model_id=modelo_id_selecionado)", 
    "RoteiristaAgent(model_id=modelo_id_selecionado, table_prefix=st.session_state.get('table_prefix', 'nw_'))"
)

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Tables replaced.")
