const fs = require('fs');
const path = require('path');
const matter = require('gray-matter');

const contentDir = path.join(__dirname, '../content/reviews');
const files = fs.readdirSync(contentDir).filter(f => f.endsWith('.mdx'));

console.log('🔍 Iniciando Auditoria Avançada de SEO (AEO, Schema, Metadados)...\n');

let issuesFound = 0;

files.forEach(file => {
    const filePath = path.join(contentDir, file);
    const content = fs.readFileSync(filePath, 'utf8');
    const { data, content: body } = matter(content);

    const report = [];

    // 1. Verificação de Conteúdo Rico (Rich Snippets / Schema)
    // Para reviews, esperamos dados estruturados de produto
    const hasSchemaData = data.rating && data.brand && data.model && data.price;
    if (!hasSchemaData) {
        // Se for um review de produto (geralmente tem ID numérico e não é guia genérico)
        // Vamos ser flexíveis: se tem "vs" ou marca no título, deveria ter schema
        if (!data.id || (String(data.id).length === 3 && !file.includes('guia'))) {
            report.push('⚠️ Falta dados de Schema (Rich Snippets): rating, brand, model ou price.');
        }
    }

    // 2. Verificação AEO (Perguntas Frequentes)
    // AEO exige responder perguntas diretas. Procuramos por seção de FAQ.
    const hasFAQ = body.includes('## Perguntas Frequentes') || body.includes('## FAQ') || body.includes('<FAQ');
    if (!hasFAQ) {
        report.push('⚠️ AEO: O artigo não tem seção de "Perguntas Frequentes" (FAQ). Importante para Voice Search.');
    }

    // 3. Verificação de Frontmatter (Metadados Básicos)
    if (!data.title) report.push('❌ Frontmatter: Título ausente.');
    if (data.title && data.title.length > 60) report.push(`⚠️ SEO Title: Título muito longo (${data.title.length} chars). Ideal < 60.`);

    if (!data.excerpt) report.push('❌ Frontmatter: Meta Description (excerpt) ausente.');
    if (data.excerpt && data.excerpt.length > 160) report.push(`⚠️ SEO Desc: Meta description muito longa (${data.excerpt.length} chars). Ideal < 160.`);

    if (!data.coverImage) report.push('❌ Visual: Capa (coverImage) ausente.');

    // 4. Verificação de Densidade / Tamanho (E-E-A-T)
    // Artigos curtos demais são considerados "Thin Content" pelo Google
    if (body.length < 2000) {
        report.push(`⚠️ E-E-A-T: Conteúdo muito curto (${body.length} chars). Recomendado > 2000 para rankear.`);
    }

    // Se houver problemas, imprime
    if (report.length > 0) {
        console.log(`📄 Arquivo: ${file}`);
        report.forEach(msg => console.log(`   ${msg}`));
        console.log('');
        issuesFound++;
    }
});

if (issuesFound === 0) {
    console.log('✅ Tudo certo! Nenhum problema crítico de SEO encontrado.');
} else {
    console.log(`🏁 Auditoria finalizada. Encontrados problemas em ${issuesFound} arquivos.`);
}
