const fs = require('fs');
const path = require('path');
const matter = require('gray-matter');

const contentDir = path.join(__dirname, '../content/reviews');

// Mapeamento de imagens reais (Links diretos da Amazon/Mercado Livre/Fabricantes)
// ATENÇÃO: Links de CDN como media-amazon.com são estáveis, mas podem expirar.
// Para produção a longo prazo, replace por arquivos locais.
const productImages = {
    // 🚚 Caminhão (Resfriar / Elber)
    '102': 'https://m.media-amazon.com/images/I/61k1T+5-KyL._AC_SX679_.jpg', // Resfriar 31L
    '103': 'https://http2.mlstatic.com/D_NQ_NP_724905-MLB70550882142_072023-O.webp', // Elber 65L (Bigber)
    '107': 'https://http2.mlstatic.com/D_NQ_NP_934509-MLB71060934177_082023-O.webp', // Elber 31L (RC31)
    '106': 'https://resfriar.com.br/wp-content/uploads/2021/03/geladeira-gaveta-scania.jpg', // Gaveta Scania

    // 🚗 Portáteis 12v
    '204': 'https://m.media-amazon.com/images/I/61a+Zgqf3TL._AC_SX679_.jpg', // Resfriar 18L
    '205': 'https://m.media-amazon.com/images/I/61r-CjL-cSL._AC_SX679_.jpg', // Hent 30L (Visual robusto)
    '206': 'https://m.media-amazon.com/images/I/51+5Z+Q-mLL._AC_SX679_.jpg', // Dreiha (Visual premium)
    '502': 'https://m.media-amazon.com/images/I/61P0+-+f+L._AC_SX679_.jpg', // Black+Decker 24L

    // 🔧 Guias e Tutoriais (Conceituais)
    '601': 'https://blog.tabelafipe.com/wp-content/uploads/2019/07/shutterstock_1120000000.jpg', // Inspeção (Motorista olhando motor)
    '501': 'https://images.unsplash.com/photo-1523987355523-c7b5b0dd90a7?auto=format&fit=crop&q=80', // Vanlife / Motorhome
    '503': 'https://images.unsplash.com/photo-1509391366360-2e959784a276?auto=format&fit=crop&q=80', // Placa Solar
};

const files = fs.readdirSync(contentDir).filter(f => f.endsWith('.mdx'));

files.forEach(file => {
    const filePath = path.join(contentDir, file);
    const content = fs.readFileSync(filePath, 'utf8');
    const { data } = matter(content);

    // Se temos uma imagem mapeada para este ID
    if (productImages[String(data.id)]) {
        // Substitui a linha coverImage
        // Regex procura: coverImage: "..."
        const newContent = content.replace(
            /coverImage: ".*?"/,
            `coverImage: "${productImages[String(data.id)]}"`
        );

        // Se houve alteração (arquivo original era diferente), salva
        if (content !== newContent) {
            fs.writeFileSync(filePath, newContent);
            console.log(`✅ Imagem atualizada para: ${file}`);
        }
    }
});
