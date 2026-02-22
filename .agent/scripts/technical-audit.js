const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const SITE_URL = process.argv[2] || 'http://localhost:3000';
const REPORT_DIR = path.join(__dirname, '../reports');

if (!fs.existsSync(REPORT_DIR)) {
    fs.mkdirSync(REPORT_DIR);
}

async function runLighthouse() {
    console.log(`🚀 Iniciando Auditoria Lighthouse para: ${SITE_URL}`);

    try {
        // Usando o comando npx para rodar o lighthouse que instalamos
        // --quiet: reduz logs desnecessários
        // --chrome-flags="--headless": roda sem abrir janela do chrome
        const command = `npx lighthouse ${SITE_URL} --quiet --chrome-flags="--headless" --output json --output html --output-path ${REPORT_DIR}/lighthouse-report`;

        console.log('⏳ Executando testes técnicos (isso pode levar uns segundos)...');
        execSync(command);

        const reportRaw = fs.readFileSync(`${REPORT_DIR}/lighthouse-report.report.json`, 'utf8');
        const report = JSON.parse(reportRaw);

        const scores = report.categories;

        console.log('\n📊 RESULTADOS TÉCNICOS:');
        console.log(`- Desempenho: ${scores.performance.score * 100}%`);
        console.log(`- Acessibilidade: ${scores.accessibility.score * 100}%`);
        console.log(`- Melhores Práticas: ${scores['best-practices'].score * 100}%`);
        console.log(`- SEO: ${scores.seo.score * 100}%`);

        console.log(`\n📄 Relatório detalhado salvo em: ${path.join(REPORT_DIR, 'lighthouse-report.report.html')}`);

    } catch (error) {
        console.error('❌ Erro ao rodar Lighthouse:', error.message);
        console.log('Dica: Verifique se o site está rodando no localhost:3000 antes de iniciar.');
    }
}

runLighthouse();
