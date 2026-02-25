import os

app_path = r"c:\Users\Tiago\Desktop\PROJETOS\magalu-ai-suite\src\app.py"
with open(app_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Substitui as ocorrências da fonética dinâmica pela fonética fixa
old_str = f'f"{{st.session_state.get(\'table_prefix\', \'nw_\')}}treinamento_fonetica"'
new_str = '"nw_treinamento_fonetica"'

text = text.replace(old_str, new_str)

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Fonetica references reverted to static.")
