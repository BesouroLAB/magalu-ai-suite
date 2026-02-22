const { execSync } = require('child_process');

const SITE_URL = process.argv[2] || 'http://localhost:3000';

function checkLinks() {
    console.log(`🔗 Verificando links quebrados em: ${SITE_URL}`);
    console.log('⏳ Isso pode demorar dependendo do tamanho do site...\n');

    try {
        // blc = broken-link-checker
        // -r: recursivo
        // -o: apenas links externos (opcional, aqui vamos checar tudo)
        // --exclude youtube etc se precisar
        const command = `npx blc ${SITE_URL} -ro`;

        // Usando spawn ou apenas alertando que vai rodar
        console.log('Executando: ' + command);
        execSync(command, { stdio: 'inherit' });

    } catch (error) {
        // blc retorna erro se encontrar links quebrados, o que é normal no fluxo
        console.log('\n✅ Verificação finalizada (veja os resultados acima).');
    }
}

checkLinks();
