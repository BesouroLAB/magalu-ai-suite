import os
import glob

# Try to import docx, if not found, we can't parse easily
try:
    from docx import Document
except ImportError:
    print("python-docx not installed. Please run: pip install python-docx")
    exit(1)

kb_dir = os.path.join(os.path.dirname(__file__), "..", "kb", "Roteiros de Referência")
out_file = os.path.join(os.path.dirname(__file__), "..", "kb", "Referencial_Roteiros_Antigos_Breno.md")

docx_files = glob.glob(os.path.join(kb_dir, "*.docx"))

if not docx_files:
    print("Nenhum arquivo .docx encontrado em kb/Roteiros de Referência")
    exit(0)

print(f"Lendo {len(docx_files)} scripts de referência...")

extracted_texts = []

# Pego só os primeiros 10 para não explodir o prompt da IA de uma vez só.
# E misturo bem a amostra.
num_files_to_use = min(15, len(docx_files)) 

for f_path in docx_files[:num_files_to_use]:
    try:
        doc = Document(f_path)
        text = "\n".join([p.text for p in doc.paragraphs if p.text.strip() != ""])
        if len(text) > 100:
            basename = os.path.basename(f_path)
            extracted_texts.append(f"--- SCRIPT REFERÊNCIA: {basename} ---\n{text}\n")
    except Exception as e:
        print(f"Erro ao ler {f_path}: {e}")

if extracted_texts:
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write("# ROTEIROS DE REFERÊNCIA (APROVADOS PELO BRENO ANTERIORMENTE)\n\n")
        f.write("Abaixo estão dezenas de exemplos reais de roteiros finalizados. Copie o tom de voz e o formato.\n\n")
        
        for text in extracted_texts:
            f.write(text + "\n")
            
    print(f"Criado {out_file} com sucesso, contendo {len(extracted_texts)} exemplos.")
else:
    print("Nenhum texto extraído.")
