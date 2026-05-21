import sys
import os

# Adiciona o diretório src ao path para importar os módulos
sys.path.append(os.path.join(os.getcwd(), 'src'))

from exporter import _clean_product_name, _extract_product_name

def test_cleaning():
    test_cases = [
        "NW LU MAR 230410600 Notebook Compaq",
        "NW 3D LU ABR 123456789 Geladeira Brastemp",
        "SOCIAL MAI 987654321 iPhone 15",
        "230410600 Notebook Compaq",
        "NW LU MAR [NOME DO PRODUTO]",
    ]

    print("--- Testando _clean_product_name ---")
    for tc in test_cases:
        res = _clean_product_name(tc)
        print(f"Input:  '{tc}'")
        print(f"Output: '{res}'")
        print("-" * 20)

    print("\n--- Testando _extract_product_name ---")
    roteiro_mock = "Cliente: Magalu\nProduto: NW LU MAR 230410600 Notebook Compaq\n- Este notebook..."
    res = _extract_product_name(roteiro_mock)
    print(f"Roteiro:\n{roteiro_mock}")
    print(f"Extracted: '{res}'")
    print(f"Cleaned Extracted: '{_clean_product_name(res)}'")

if __name__ == "__main__":
    test_cleaning()
