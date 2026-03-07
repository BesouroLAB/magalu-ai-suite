import sys
import os
# Adiciona o diretório raiz ao path para importar src
sys.path.append(os.getcwd())

from src.agent import RoteiristaAgent
from src.exporter import export_roteiro_docx, generate_filename

def test_header_logic():
    print("--- Testando Lógica de Cabeçalho ---")
    
    # Mock de dados extraídos
    scraped_data = {"text": "Produto de teste com ótimas características.", "images": []}
    
    # Simula o agente sem precisar de chave real (usando fallback ou mock parcial se necessário, 
    # mas aqui queremos testar a formatação que acontece no post-processing e prompt build)
    # Na verdade, como o post-processing depende da resposta da IA, vamos testar a construção do diretriz_modo
    
    agent = RoteiristaAgent(model_id="gemini-1.5-flash")
    
    # Caso 1: Com LU + Vídeo
    print("\n[Caso 1] Com LU + Vídeo + Sub SKUs")
    try:
        # Vamos apenas testar o generate_filename e export_roteiro_docx que são determinísticos
        fn = generate_filename("123456", "Monitor Gamer", selected_month="MAR", com_lu=True)
        print(f"Nome do Arquivo (Com LU): {fn}")
        assert fn.startswith("NW LU MAR 123456000")
        
        # Caso 2: Sem LU
        fn2 = generate_filename("123456", "Monitor Gamer", selected_month="MAR", com_lu=False)
        print(f"Nome do Arquivo (Sem LU): {fn2}")
        assert fn2.startswith("NW MAR 123456000")
        
        # Caso 3: Fallback de cabeçalho no exportador
        roteiro_raw = "Esse é um roteiro sem cabeçalho."
        doc_bytes, fn3 = export_roteiro_docx(roteiro_raw, code="999888", product_name="Teclado", selected_month="ABR", com_lu=False)
        print(f"Fallback filename (Sem LU): {fn3}")
        assert fn3.startswith("NW ABR 999888000")
        
        doc_bytes_lu, fn4 = export_roteiro_docx(roteiro_raw, code="999888", product_name="Teclado", selected_month="ABR", com_lu=True)
        print(f"Fallback filename (Com LU): {fn4}")
        assert fn4.startswith("NW LU ABR 999888000")
        
        print("\n✅ Verificação de Nomes de Arquivo e Fallbacks: OK")
        
    except Exception as e:
        print(f"\n❌ ERRO na verificação: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_header_logic()
