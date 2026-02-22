const fs = require('fs');
const path = require('path');
const matter = require('gray-matter');

const contentDir = path.join(__dirname, '../content/reviews');

const replacements = {
    '103-geladeira-caminhao-elber-65-litros.mdx': 'Geladeira Elber 65 Litros: Análise Completa 2026',
    '104-comparativo-resfriar-vs-elber-vs-maxiclima.mdx': 'Resfriar vs Elber vs Maxiclima: A Melhor em 2026',
    '105-caixa-cozinha-vs-geladeira-interna.mdx': 'Caixa de Cozinha ou Geladeira Interna: Qual Escolher?',
    '107-geladeira-caminhao-elber-31-litros.mdx': 'Geladeira Elber 31L: Review da Concorrente Resfriar',
    '201-melhor-geladeira-portatil-12v-2026.mdx': 'Top 5 Geladeiras Portáteis 12v em 2026',
    '202-termoeletrica-vs-compressor.mdx': 'Termoelétrica vs Compressor: Guia Rápido',
    '203-geladeiras-portateis-baratas.mdx': 'Geladeira Portátil Barata: 3 Modelos Recomendados',
    '204-comparativo-resfriar-18l-vs-elber-18l.mdx': 'Resfriar 18L vs Elber 18L: Qual Gela Mais Rápido?',
    '204-review-resfriar-18l.mdx': 'Review: Geladeira Resfriar 18L Vale a Pena?',
    '205-geladeira-hent-e-boa.mdx': 'Geladeira Hent é Boa? Análise da Marca Chinesa',
    '206-dreiha-vs-hent.mdx': 'Dreiha vs Hent: Qual a Melhor Chinesa?',
    '301-como-instalar-geladeira-caminhao-passo-a-passo.mdx': 'Instalação de Geladeira no Caminhão: Guia Prático',
    '302-12v-24v-ou-quadrivolt.mdx': '12v, 24v ou Quadrivolt: Qual Escolher?',
    '303-geladeira-caminhao-descarregando-bateria.mdx': 'Geladeira Liga a Noite Toda Descarrega Bateria?',
    '304-codigos-erro-geladeira-resfriar-e1-e2-e3-manual.mdx': 'Erro E1 na Geladeira Resfriar: Como Resolver',
    '305-geladeira-liga-mas-nao-gela.mdx': 'Geladeira Liga mas Não Gela: Defeitos Comuns',
    '306-temperatura-ideal-e-configuracao.mdx': 'Temperatura Ideal da Geladeira: Economize Bateria',
    '401-como-consertar-geladeira-caminhao-guia-completo.mdx': 'Conserto de Geladeira de Caminhão: Vale a Pena?',
    '401-guia-caixa-cozinha-caminhao.mdx': 'Caixa de Cozinha para Caminhão: Guia de Materiais',
    '402-assistencia-tecnica-geladeira-resfriar-elber.mdx': 'Assistência Técnica Geladeira 12v: Onde Consertar',
    '402-o-que-levar-caixa-cozinha.mdx': 'O Que Levar na Caixa de Cozinha: Lista Completa'
};

Object.entries(replacements).forEach(([filename, newTitle]) => {
    const filePath = path.join(contentDir, filename);
    if (fs.existsSync(filePath)) {
        const fileContent = fs.readFileSync(filePath, 'utf8');
        // Usa regex para substituir apenas o title: "..."
        // A regex procura por title: "qualquer coisa" e substitui mantendo as aspas
        const newContent = fileContent.replace(/title: ".*?"/, `title: "${newTitle}"`);

        fs.writeFileSync(filePath, newContent);
        console.log(`✅ ${filename} atualizado.`);
    } else {
        console.log(`❌ ${filename} não encontrado.`);
    }
});
