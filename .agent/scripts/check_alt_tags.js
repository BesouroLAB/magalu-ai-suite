const fs = require('fs');
const path = require('path');
const matter = require('gray-matter');

const contentDir = path.join(__dirname, '../content/reviews');

function checkAltTags() {
    console.log('🖼️  Verificando acessibilidade de imagens (ALT Tags)...\n');

    const files = fs.readdirSync(contentDir).filter(f => f.endsWith('.mdx'));
    let issues = 0;

    files.forEach(file => {
        const filePath = path.join(contentDir, file);
        const content = fs.readFileSync(filePath, 'utf8');
        const { content: body } = matter(content);

        // Regex para encontrar imagens Markdown: ![alt](url)
        // Captura grupo 1: alt text
        const imageRegex = /!\[(.*?)\]\((.*?)\)/g;
        let match;

        while ((match = imageRegex.exec(body)) !== null) {
            const altText = match[1];
            const imageUrl = match[2];

            if (!altText || altText.trim() === '') {
                console.log(`❌ Arquivo: ${file}`);
                console.log(`   Imagem sem ALT: ${imageUrl}`);
                issues++;
            } else if (altText.length < 5) {
                console.log(`⚠️ Arquivo: ${file}`);
                console.log(`   ALT muito curto ("${altText}"): ${imageUrl}`);
                issues++;
            }
        }
    });

    if (issues === 0) {
        console.log('✅ Tudo certo! Todas as imagens no corpo do texto têm descrição ALT.');
    } else {
        console.log(`\n🏁 Encontrados ${issues} problemas de acessibilidade em imagens.`);
    }
}

checkAltTags();
