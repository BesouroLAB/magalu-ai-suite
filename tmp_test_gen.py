
import os
import sys
from dotenv import load_dotenv

# Carrega as variáveis de ambiente antes de qualquer import do projeto
load_dotenv()

sys.path.append(os.path.join(os.getcwd(), 'src'))
from agent import RoteiristaAgent

def test_generation():
    agent = RoteiristaAgent(model_id='gemini-3-flash-preview')
    
    scraped_data = {
        'text': """TÍTULO: Liquidificador Oster 1400 Full OLIQ610 Preto 15 Velocidades + Pulsar 1400W
MARCA: Oster
LINHA/NOME COMERCIAL: 1400 Full
DESCRIÇÃO: Este liquidificador da Oster oferece alta potência de 1400W, ideal para o preparo de diversas receitas. Ele é equipado com 4 lâminas de inox que garantem um corte eficiente e uma mistura homogênea. O aparelho conta com 15 velocidades e função pulsar, e seu copo de plástico possui capacidade útil de 2 litros.
FICHA TÉCNICA:
- Potência: 1400W
- Lâminas: 4, em inox
- Velocidades: 15 + Pulsar
- Capacidade útil do copo: 2 litros
- Material do copo: Plástico

VOLTAGEM: 110V
CORES DISPONÍVEIS: Apenas Preto
FEATURES PRÁTICAS: As lâminas de inox são resistentes, possuem alto poder de corte e mistura, e não enferrujam.""",
        'images': []
    }
    
    result = agent.gerar_roteiro(
        scraped_data, 
        modo_trabalho='NW LU', 
        mes='MAR', 
        data_roteiro='07/03/26', 
        codigo='021798900', 
        nome_produto='Liquidificador Oster 1400 Full',
        com_lu=True
    )
    
    print(result['roteiro'])

if __name__ == "__main__":
    test_generation()
