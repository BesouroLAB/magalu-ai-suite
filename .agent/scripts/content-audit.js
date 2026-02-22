const fs = require('fs');
const path = require('path');
const matter = require('gray-matter');

const CONTENT_DIR = path.join(__dirname, '../content/reviews');

/**
 * Script para auditar arquivos MDX em busca de problemas de SEO.
 */
function auditMDX() {
    console.log('🔍 Iniciando Auditoria de Conteúdo (MDX)...\n');

    const files = fs.readdirSync(CONTENT_DIR).filter(f => f.endsWith('.mdx'));
    const reports = [];

    files.forEach(file => {
        const filePath = path.join(CONTENT_DIR, file);
        const content = fs.readFileSync(filePath, 'utf8');
        const { data, content: textContent } = matter(content);

        const fileReport = {
            file,
            errors: [],
            warnings: []
        };

        // 1. Verificação de Frontmatter
        if (!data.title) fileReport.errors.push('Título (title) ausente no frontmatter.');
        if (data.title && data.title.length > 60) fileReport.warnings.push(`Título longo (${data.title.length} chars). Ideal < 60.`);

        if (!data.excerpt) fileReport.errors.push('Meta Description (excerpt) ausente.');
        if (data.excerpt && data.excerpt.length > 160) fileReport.warnings.push(`Excerpt longo (${data.excerpt.length} chars). Ideal < 160.`);

        if (!data.coverImage) fileReport.errors.push('Imagem de capa (coverImage) ausente.');

        // 2. Verificação de Conteúdo
        if (textContent.length < 1500) fileReport.warnings.push(`Conteúdo curto (${textContent.length} chars). SEO gosta de > 2000.`);

        // 3. Verificação de Imagens sem Alt (no markdown ou MDX)
        const imageRegex = /!\[(.*?)\]\((.*?)\)/g;
        let match;
        while ((match = imageRegex.exec(textContent)) !== null) {
            if (!match[1] || match[1].trim() === '') {
                fileReport.errors.push(`Imagem encontrada sem texto ALT: ${match[2]}`);
            }
        }

        // 4. Verificação de H1 duplicado no corpo (o title já vira H1 no layout)
        if (/^# /m.test(textContent)) {
            fileReport.errors.push('Evite usar "# Cabeçalho" (H1) dentro do texto. O título do frontmatter já é o H1.');
        }

        if (fileReport.errors.length > 0 || fileReport.warnings.length > 0) {
            reports.push(fileReport);
        }
    });

    if (reports.length === 0) {
        console.log('✅ Nenhum problema crítico encontrado nos arquivos MDX!');
    } else {
        reports.forEach(r => {
            console.log(`📄 Arquivo: ${r.file}`);
            r.errors.forEach(err => console.log(`   ❌ ERRO: ${err}`));
            r.warnings.forEach(warn => console.log(`   ⚠️ AVISO: ${warn}`));
            console.log('');
        });
    }
}

auditMDX();
