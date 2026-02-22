const fs = require('fs');
const path = require('path');

const contentDir = path.join(__dirname, '../content/reviews');

const faqs = {
    '102-geladeira-caminhao-resfriar-31-litros.mdx': `
---

### Perguntas Frequentes sobre a Resfriar 31L

<FAQBox 
  questions={[
    {
      question: "A Resfriar 31L cabe no Mercedes 1620?",
      answer: "Sim, ela foi desenhada com medidas universais que cabem tanto no banco do carona quanto no espaço entre bancos da maioria dos caminhões, incluindo a linha Mercedes e Volkswagen."
    },
    {
      question: "Quanto tempo ela segura gelada desligada?",
      answer: "Graças ao isolamento de poliuretano de alta densidade, ela mantém a temperatura por cerca de 4 a 6 horas desligada, dependendo do calor externo. Ideal para pernoites curtos."
    },
    {
      question: "O compressor faz muito barulho pra dormir?",
      answer: "Não. O nível de ruído é inferior a 40dB, o que é considerado silencioso (similar a um sussurro ou biblioteca). A maioria dos motoristas dorme com ela ao lado da cama sem problemas."
    }
  ]}
/>
`,
    '103-geladeira-caminhao-elber-65-litros.mdx': `
---

### Perguntas Frequentes sobre a Elber 65L (Bigber)

<FAQBox 
  questions={[
    {
      question: "Qual o consumo médio da Elber 65L?",
      answer: "O consumo médio gira em torno de 1.8Ah a 2.2Ah em 24v. Recomendamos ter ao menos duas baterias de 150Ah em bom estado para garantir autonomia total."
    },
    {
      question: "Ela cabe na caixa de cozinha Randon?",
      answer: "Sim, a Bigber RC65 tem medidas padrão para a maioria das caixas de cozinha de madeira e aço do mercado (Randon, Facchini, Librelato). Sempre confira as medidas do nicho antes."
    },
    {
      question: "A garantia da Elber cobre o compressor?",
      answer: "Sim, a Elber oferece 2 anos de garantia total no produto, incluindo o compressor hermético, o que é um dos maiores diferenciais da marca."
    }
  ]}
/>
`,
    '501-geladeira-12v-motorhome-vanlife-guia.mdx': `
---

### Perguntas Frequentes: Geladeira para Motorhome

<FAQBox 
  questions={[
    {
      question: "Quantos painéis solares preciso para uma geladeira 12v?",
      answer: "Para uma geladeira de 30-50L, recomendamos no mínimo 150W de painel solar e uma bateria estacionária de 100Ah. Isso garante autonomia mesmo em dias nublados."
    },
    {
      question: "Posso usar geladeira de frigobar 220v com inversor?",
      answer: "Pode, mas não recomendamos para sistemas pequenos. O inversor gasta 15-20% de energia só para ficar ligado. Uma geladeira 12v nativa é 30% mais eficiente e segura."
    },
    {
      question: "Qual o melhor lugar para instalar na Van?",
      answer: "Sempre em local ventilado. O compressor precisa 'respirar'. Evite locais fechados sem grelhas de ventilação, pois isso força o motor e aumenta o consumo drasticamente."
    }
  ]}
/>
`
};

Object.entries(faqs).forEach(([filename, faqContent]) => {
    const filePath = path.join(contentDir, filename);
    if (fs.existsSync(filePath)) {
        const currentContent = fs.readFileSync(filePath, 'utf8');

        // Verifica se já tem FAQ para não duplicar
        if (!currentContent.includes('<FAQBox') && !currentContent.includes('Perguntas Frequentes')) {
            fs.appendFileSync(filePath, faqContent);
            console.log(`✅ FAQ adicionado em: ${filename}`);
        } else {
            console.log(`ℹ️ FAQ já existe em: ${filename}`);
        }
    } else {
        console.log(`❌ Arquivo não encontrado: ${filename}`);
    }
});
