const fs = require('fs');
const path = require('path');

const contentDir = path.join(__dirname, '../content/reviews');

const newFaqs = {
    // Artigo sobre Caixas de Cozinha (Alta demanda no Semrush)
    '401-guia-caixa-cozinha-caminhao.mdx': `
---

### Perguntas Frequentes sobre Caixa de Cozinha

<FAQBox 
  questions={[
    {
      question: "Qual o tamanho padrão de caixa de cozinha para caminhão?",
      answer: "A medida mais comercializada (Padrão Randon/Facchini) é de 1,20m de comprimento x 0,60m de altura x 0,60m de profundidade. Existem modelos menores (90cm) para caminhões toco e maiores (1,60m) para carretas vanderleia."
    },
    {
      question: "Caixa de cozinha de madeira ou plástico: qual a melhor?",
      answer: "A de Plástico (Polipropileno) é mais leve, não absorve cheiro e é moderna, mas pode ressecar com o sol após anos. A de Madeira (Compensado Naval) é mais barata e fácil de consertar, mas pesa muito mais e pode estufar se não for bem vedada."
    },
    {
      question: "Como fazer uma caixa de cozinha caseira resistente?",
      answer: "O segredo é usar Compensado Naval de 18mm ou 20mm (nunca use MDF, pois desmancha com umidade) e revestir com fórmica. Use cantoneiras de alumínio para reforçar a estrutura contra a vibração da estrada."
    }
  ]}
/>
`,
    // Artigo sobre Defeitos (Alta demanda no GSC: "geladeira não gela")
    '305-geladeira-liga-mas-nao-gela.mdx': `
---

### Dúvidas Comuns de Manutenção

<FAQBox 
  questions={[
    {
      question: "Minha geladeira Elber ou Resfriar liga o painel mas não gela. O que é?",
      answer: "90% dos casos é falha na ventoinha (cooler) que refrigera o compressor ou insuficiência de gás. Se ouvir o motor tentando partir (tec-tec) e parando, pode ser o módulo controlador com defeito ou falta de bateria (voltagem baixa)."
    },
    {
      question: "Qual a temperatura ideal para economizar bateria?",
      answer: "Mantenha entre -2ºC e +2ºC para conservação diária. Forçar -10ºC ou menos exige que o compressor trabalhe 100% do tempo, drenando suas baterias rapidamente sem necessidade real para carnes e bebidas comuns."
    },
    {
      question: "Posso completar o gás da geladeira em casa?",
      answer: "Não recomendado. Diferente de pneus, o sistema de refrigeração é lacrado. Se falta gás, há um vazamento (furo). Apenas colocar gás sem soldar o furo é jogar dinheiro fora, pois vai vazar tudo novamente em dias."
    }
  ]}
/>
`
};

Object.entries(newFaqs).forEach(([filename, faqContent]) => {
    const filePath = path.join(contentDir, filename);
    if (fs.existsSync(filePath)) {
        const currentContent = fs.readFileSync(filePath, 'utf8');

        // Verifica duplicidade
        if (!currentContent.includes('<FAQBox') && !currentContent.includes('Perguntas Frequentes')) {
            fs.appendFileSync(filePath, faqContent);
            console.log(`✅ FAQ estratégico adicionado em: ${filename}`);
        } else {
            console.log(`ℹ️ FAQ já existia em: ${filename}`);
        }
    } else {
        console.log(`❌ Arquivo não encontrado: ${filename}`);
    }
});
