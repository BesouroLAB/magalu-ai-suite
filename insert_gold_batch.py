
import os
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

scripts = [
    # Batch 1
    {
        "titulo": "Echo Dot 5ª Geração Amazon",
        "cat_id": 60,
        "sku": "236402100", # Example Magalu SKU for Echo Dot 5
        "content": """- Esse Echo Dot (écou dót) de quinta geração, da Amazon, tem som com vocais nítidos e graves potentes pra ouvir suas músicas em qualquer lugar da casa.
Imagem: echodtot em mesa de sala clean.

- Com a Alexa integrada, dá pra pedir músicas e podcasts do Spotify ou Amazon Music, além de criar timers e tirar dúvidas por comando de voz.
TL: Verifique a compatibilidade de apps e sistemas
Imagem: Close no topo do aparelho com o anel de luz azul aceso e ícones flutuantes de serviços de streaming.

- Ah, e ele também funciona como um hub (rãb) de casa inteligente. Os sensores internos de movimento e temperatura podem ligar as luzes ou o ar-condicionado de um jeito prático.
Imagem: Animação gráfica mostrando o Echo Dot conectando a ícones de lâmpada e termostato.

- Pra completar, um simples toque no topo do aparelho já adia o alarme, o que ajuda muito naquelas manhãs de preguiça.
Imagem: Close na parte superior do Echo Dot com uma indicação gráfica de toque.

- Caixa de som inteligente pro seu dia a dia, tem no Magalu!
Lettering: #TemNoMagalu"""
    },
    {
        "titulo": "PlayStation 5 Slim Sony",
        "cat_id": 68,
        "sku": "237905200", # Example SKU
        "content": """- Este PlayStation 5 Slim, da Sony, tem SSD de 1 tera (téra) de altíssima velocidade que acaba com aquelas telas de carregamento demoradas.
Imagem: mostrar pack do console + animação de carregamento (loading).

- E o controle DualSense (duól l-sénse) traz uma imersão real com vibrações que mudam conforme o jogo e gatilhos que respondem a cada ação.
Imagem: Close no controle DualSense mostrando detalhes dos botões e gatilhos.
Ver cenas dos vídeos.
0’44” do vídeo https://www.youtube.com/watch?v=lu5VXrEqgco mostra uma interação.

- Já a resolução 4K entrega gráficos nítidos e detalhados. Ah, e esse modelo aceita mídia física, ou seja, dá pra usar seus discos de jogos favoritos.
Imagem: Close na entrada de disco do console e depois um plano detalhe da carcaça branca e compacta.

- Pra completar, ele já vem com o jogo ASTRO's PLAYROOM (ástros plêi-rum) pré-instalado.
Imagem: Interface do console na TV mostrando o ícone do jogo Astro's Playroom + gameplay
https://www.youtube.com/watch?v=lu5VXrEqgco


- Tudo do mundo game, tem no Magalu!
Lettering: #TemNoMagalu"""
    },
    {
        "titulo": "Dell All in One Intel Core i5 13ª Geração",
        "cat_id": 69,
        "sku": "237305900", # Example SKU
        "content": """- Este All in One (al-in-uân), da Dell, integra monitor e CPU num design fino que deixa sua mesa organizada e moderna.
Imagem: plano geral em mesa de escritório.

- O processador Intel Core i5 (í cinco) de 13ª (décima terceira) geração trabalhando junto com 1TB (um téra) de SSD é rápido pra abrir arquivos e programas sem travar.
Imagem: Close no produto mostrando o perfil fino e depois uma animação gráfica destacando o processador i5 e o armazenamento de 1TB.

- Já a tela Full HD de 23,8 polegadas tem bordas infinitas e a tecnologia que reduz a luz azul e traz mais conforto pros olhos.
Imagem: Close na tela com bordas finas exibindo uma imagem vibrante e depois um ícone representando a proteção ocular.

- Ah, e ele já vem com teclado e mouse sem fio, e ainda dá pra ajustar a inclinação da tela em até vinte e cinco graus.
TL: Verifique a compatibilidade com seu dispositivo
Imagem: Plano detalhe do teclado e mouse branco gelo e um movimento lateral mostrando a tela inclinando.

- O computador potente e organizado pro seu dia, tem no Magalu!
Lettering: #TemNoMagalu"""
    },
    {
        "titulo": "Freezer Horizontal Consul 142L",
        "cat_id": 64,
        "sku": "226505000", # Example SKU
        "content": """- Esse Freezer Horizontal, da Consul, vira geladeira com apenas um botão, ou seja, se adapta ao que você precisa guardar no dia.
Imagem: plano geral em ambiente comercial ou área de lazer.

- Com 142 litros de capacidade, ele é ideal pra lugares menores, entregando o espaço certo sem ocupar muito do ambiente, seja em casa ou em pequenos comércios.
Imagem: Close do interior do freezer aberto mostrando o espaço interno bem organizado com alimentos.

- Ah, e ele tem classificação A de eficiência energética pra ajudar na economia da conta de luz.
Imagem: Animação gráfica destacando o selo de eficiência energética classe A sobre o produto.
TL: Verifique a voltagem do produto antes de comprar.

- O freezer compacto e versátil pra sua rotina, tem no Magalu!
Lettering: #TemNoMagalu"""
    },
    {
        "titulo": "Fone JBL Soundgear Clips Open Ear",
        "cat_id": 52,
        "sku": "237805100", # Example SKU
        "content": """- Este Fone de Ouvido Soundgear Clips (sánd-guir clí-pis), da JBL, tem o design Open Ear (ô-pen í-er) pra você ouvir seu som ou podcast com clareza sem se desligar do que acontece ao redor.
Imagem: pack com os fones.

- O som tem graves reforçados e os quatro microfones integrados usam inteligência artificial que deixa a voz nítida nas chamadas, diminuindo o barulho de fora.
Imagem: Close nos detalhes dos microfones e animação gráfica indicando a captação de voz.

- A bateria dura até 32 horas no total e ele ainda é resistente à água e poeira.
Imagem: Detalhe do fone com grafismo de bateria "32h" e ícone de proteção contra água.

- E dá pra alternar entre o celular e o notebook rapidinho com a conexão multiponto. 
Imagem: Transição mostrando o fone próximo a diferentes dispositivos e depois as três opções de cores.

- Ah, e ele tá disponível em diferentes cores.
TL.: Disponível em diferentes cores
Imagem: pack com cores.

- O fone tecnológico que você procura, tem no Magalu!
Lettering: #TemNoMagalu"""
    },
    # Batch 2
    {
        "titulo": "Monitor AOC 310Hz 0.3ms",
        "cat_id": 69,
        "sku": "237004100",
        "content": """– Com trezentos e dez hertz de frequência e zero vírgula três milissegundos de tempo de resposta, esse Monitor, da AOC (á ó cê), entrega a fluidez que todo gamer precisa! 
Imagem: Plano geral e um close na tela com um jogo de FPS ou corrida, mostrando a transição de quadros ultra suave.

– Ele tem vinte e quatro polegadas e meia com painel IPS e resolução Full HD, garantindo cores vibrantes e ângulos de visão perfeitos.
Imagem: Ângulo lateral do monitor mostrando que as cores permanecem nítidas.

– Já a tecnologia NVIDIA G-Sync (Enivídia Jí-Sinqui) elimina aqueles cortes chatos na imagem.
Imagem: Detalhe da tela lisa, sem quebras de imagem. 

– E como a base é ajustável, você pode deixar ela da maneira mais confortável pra jogar durante horas. 
Imagem: Mostrar a inclinação do monitor. 

– Ah, e ele ainda tem conexões HDMI e DisplayPort (Displêi Pórti), ou seja, é o setup (setãp) ideal pra quem busca performance de nível profissional. 
Imagem: Mostrar as entradas na parte de trás.

– A velocidade que você merece, pra você dominar qualquer partida , tem no Magalu! 
Lettering: #TemnoMagalu"""
    },
    {
        "titulo": "LG Styler Sistema de Cuidado com Roupas",
        "cat_id": 64,
        "sku": "226509900",
        "content": """- Este Styler, da LG, tem a tecnologia de vapor que higieniza e renova roupas sem precisar lavar, acabando com cheiros e bactérias.
Imagem: Lu ao lado do Styler LG com acabamento espelhado, mostrando como fica no ambiente.

- Ele elimina noventa e nove vírgula nove por cento das bactérias e alérgenos, garantindo que ternos, casacos e até roupas de cama fiquem sempre protegidos e prontos pra usar.
Imagem: Animação gráfica destacando o vapor penetrando nas fibras do tecido e o selo de eliminação de microrganismos.
Cenas o vídeo:
https://www.youtube.com/watch?v=hn8V_tzivsE


- E pra facilitar sua rotina, o vapor também suaviza os amassados e faz a desodorização das peças.
Imagem: Close nel interior do Styler com as roupas balançando suavemente enquanto o vapor age.

- Ah, e ele tem secagem suave e delicada pra cuidar ainda mais das suas roupas. E tem também um suporte exclusivo que mantém o vinco das calças impecável.
Imagem: Detalhe do cabide de calças na porta e da prateleira interna para itens menores.

- São várias tecnologias e ciclos pré-definidos pra você escolher no painel touch e cuidar com todo carinho das suas roupas.
Imagem: mostrar o painel touch

- A melhor solução pra cuidar bem das roupas, tem no Magalu!
Lettering: #TemNoMagalu"""
    },
    {
        "titulo": "Samsung Galaxy M53 5G 128GB",
        "cat_id": 61,
        "sku": "234905100",
        "content": """- Este Smartphone Galaxy M53, da Samsung, tem câmera traseira quádrupla com sensor principal de 108 megapixels, então dá pra fazer fotos com nível de detalhes impressionante, mesmo se precisar ampliar a imagem.
Imagem: plano geral do aparelho.

- Já a câmera de selfie tem 32 megapixels pra garantir fotos nítidas e prontas pra postar. E pra guardar tudo isso, são 128GB de espaço interno.
Imagem: Close na parte frontal do aparelho destacando a câmera de selfie e depois um gráfico de armazenamento.

- Ah, e o processador Octa-core (cór) junto com os 8 giga de memória RAM abre seus apps (éps) rapidinho e sem travar. E com a tecnologia 5G, seus downloads e vídeos carregam num instante.
Imagem: Animação gráfica destacando os "8GB de RAM" e o ícone da tecnologia 5G sobre o aparelho.

- A tela Super AMOLED Plus (amô-léd plãs) tem seis vírgula sete polegadas e 120Hz (cento e vinte rértz) de atualização pra entregar cores vivas e movimentos bem fluidos pra você navegar ou jogar com qualidade.
Imagem: Close na tela do aparelho exibindo uma transição de imagens coloridas e fluidas.

- A bateria de cinco mil miliampéres hora foi feita pra durar o dia inteiro e te acompanhar em tudo o que você tiver que fazer.
Imagem: Giro 360 graus no aparelho azul, mostrando o design com bordas suaves e moldura fina.
TL: A duração da bateria pode variar de acordo com o uso

- O smartphone certo pra você, tem no Magalu!
Lettering: #TemNoMagalu"""
    },
    {
        "titulo": "Mesa de Escritório Indusat com 4 Prateleiras",
        "cat_id": 72,
        "sku": "237009100",
        "content": """– Essa mesa de escritório, da Indusat, vem com tampo e 4 prateleiras com ótimo espaço pra você organizar seu cantinho de home office!.
Imagem: Plano aberto da mesa em um ambiente de escritório, mostrando o espaço do tampo com um notebook + régua de medida. 

– Dá pra colocar seus livros, caixas e até aquela decoração que deixa o escritório com a sua cara, já que tanto as prateleiras quanto a mesa suportam 10Kg.
Imagem: mostrar o móvel decorado.

- E com estrutura em aço , o tampo em MDP de 12 milímetros e esse visual industrial, ela combina com qualquer ambiente. 
Imagem: Close nas prateleiras sendo decoradas e detalhe do acabamento resistente do tampo.

– Ah, e ainda tá disponível nas cores branca, preta e amadeirada, pra você escolher a que mais combina com a sua decoração!
TL: Verifique a disponibilidade das cores.
Imagem: Fotos das três versões de cores aparecendo na tela.

– Espaço e organização pra sua rotina de trabalho, tem no Magalu!
Lettering: #TemnoMagalu"""
    },
    {
        "titulo": "Mesa de Escritório Indusat com 2 Prateleiras",
        "cat_id": 72,
        "sku": "237009200",
        "content": """– Essa mesa de escritório, da Indusat, tem design industrial que se encaixa perfeitamente no seu escritório ou home office.
Imagem: Plano aberto da mesa em um canto do quarto ou sala, mostrando como ela ocupa pouco espaço físico + régua de medida.

– Ela vem com duas prateleiras na lateral, que são ótimas pra você organizar seus livros e materiais, deixando o tampo livre pro que realmente importa na hora de produzir.
Imagem: Close nas duas prateleiras embaixo do tampo com alguns objetos e depois mostrar o notebook na mesa.

– E ela tem a estrutura em aço, o tampo em MDP de 12 milímetros e é muito fácil de montar, então você mesmo já deixa ela prontinha pra começar a usar!
Imagem: Take da mulher montando facilmente. 

– E pra combinar com o seu estilo, ela também tá disponível em diferentes cores, como branca, preta e amadeirada. É só escolher a sua favorita!
TL: Verifique a disponibilidade das cores.
Imagem: Mostra rápido as três opções de cores (branca, preta e amadeirada). 

– Espaço e organização que a sua rotina pede, tem no Magalu!
Lettering: #TemnoMagalu"""
    }
]

def insert():
    success = 0
    for s in scripts:
        data = {
            "categoria_id": s["cat_id"],
            "titulo_produto": s["titulo"],
            "roteiro_perfeito": s["content"],
            "codigo_produto": s["sku"]
        }
        try:
            supabase.table("nw_roteiros_ouro").insert(data).execute()
            print(f"✅ Inserido: {s['titulo']}")
            success += 1
        except Exception as e:
            print(f"❌ Erro ao inserir {s['titulo']}: {e}")
    print(f"\nFim. {success} de {len(scripts)} roteiros adicionados à base Ouro.")

if __name__ == "__main__":
    insert()
