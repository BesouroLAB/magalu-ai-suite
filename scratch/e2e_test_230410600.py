import os
import sys
from dotenv import load_dotenv

# Adiciona o diretório src ao path para importar os módulos
sys.path.append(os.path.join(os.getcwd(), 'src'))

from scraper import scrape_with_gemini
from agent import RoteiristaAgent
from exporter import export_roteiro_docx

def test_e2e(code):
    try:
        # Força utf-8 no stdout para evitar erros de charmap no Windows
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

    print(f"--- Iniciando teste E2E para o codigo: {code} ---")

    # 1. Scraper
    print("\n1. Executando Scraper...")
    scraped_data = scrape_with_gemini(code)
    if "❌" in scraped_data['text'] or "⚠️" in scraped_data['text']:
        print(f"Erro no Scraper: {scraped_data['text']}")
        return
    print("Scraper concluido com sucesso.")

    # 2. Geracao de Roteiro
    print("\n2. Gerando Roteiro...")
    try:
        agent = RoteiristaAgent(model_id="gemini-3-flash-preview")
        result = agent.gerar_roteiro(
            scraped_data,
            modo_trabalho="NW (NewWeb)",
            mes="MAR",
            codigo=code,
            com_lu=True
        )

        roteiro_text = result['roteiro']
        print("Roteiro gerado com sucesso.")
    except Exception as e:
        print(f"Erro na geracao do roteiro: {e}")
        return

    # 3. Exportacao e Nome do Arquivo
    print("\n3. Exportando para DOCX e Verificando Nome do Arquivo...")
    try:
        docx_bytes, filename = export_roteiro_docx(
            roteiro_text,
            code=code,
            selected_month="MAR",
            model_id="gemini-3-flash-preview",
            com_lu=True
        )

        print(f"Nome do arquivo gerado: {filename}")

        # Validacao do nome do arquivo
        if filename.startswith("NW LU MAR") and code in filename:
            print("[OK] Nome do arquivo segue o padrao correto.")
        else:
            print("[ERRO] Nome do arquivo NAO segue o padrao esperado.")

        # Salva o arquivo localmente para inspecao
        output_dir = os.path.join(os.getcwd(), "artifacts")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)
        with open(output_path, "wb") as f:
            f.write(docx_bytes)
        print(f"Arquivo salvo em: {output_path}")

        # Verifica se o arquivo existe
        if os.path.exists(output_path):
            print("[OK] Arquivo salvo fisicamente com sucesso.")
        else:
            print("[ERRO] Arquivo nao encontrado apos salvamento.")

    except Exception as e:
        print(f"Erro na exportacao: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    load_dotenv()
    test_e2e("230410600")
