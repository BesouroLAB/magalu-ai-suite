# Plano de Implementação: Schema SQL e Integração JSON-LD

## 1. Objetivo
Revisar o schema atual do Supabase (`supabase_schema.sql`) e estabelecer uma arquitetura preparada para exportação estruturada via **JSON-LD**.
Isso permitirá que os Roteiros Gerados (e Roteiros Ouro) não sejam apenas textos, mas objetos de dados ricos e padronizados, prontos para injeção direta em páginas HTML, plataformas de e-commerce (como a Magalu), ou consumo via API por outros sistemas.

## 2. Conceito: Por que JSON-LD?
JSON-LD (JavaScript Object Notation for Linked Data) é o formato recomendado pelo Google para estruturar dados.
Ao invés de salvarmos apenas um grande bloco de texto, se estruturarmos as tabelas corretamente, podemos facilmente gerar um payload JSON-LD do tipo `Product` ou `CreativeWork` (ou até ambos) contendo:
*   `sku` / Código do Produto
*   `description` (Roteiro Ouro Finalizado)
*   `category` (Departamento/Categoria)
*   `author` (AI Suite Breno)
*   `datePublished` (Timestamp de criação)

Isso facilita absurdamente a indexação de SEO e a integração com outros softwares.

## 3. Revisão do Schema Atual (`supabase_schema.sql`)

Atualmente temos as seguintes tabelas:
1.  `categorias`: `id`, `nome`, `tom_de_voz`, `criado_em`
2.  `treinamento_estruturas`: `id`, `tipo_estrutura`, `texto_ouro`, `criado_em`
3.  `treinamento_fonetica`: `id`, `termo_errado`, `termo_corrigido`, `tipo_regra`, `criado_em`
4.  `roteiros_ouro`: `id`, `categoria_id`, `titulo_produto`, `roteiro_perfeito`, `criado_em`
5.  `feedback_roteiros`: `id`, `categoria_id`, `ficha_produto`, `roteiro_ia_input`, `roteiro_breno_input`, `avaliacao`, `comentarios`, `criado_em`
6.  `historico_roteiros`: `id`, `codigo_produto`, `modo_trabalho`, `roteiro_gerado`, `criado_em`

*(Aba/Entidade Persona Lu foi pensada para o futuro e pode virar tabela depois)*

## 4. O que Podemos Melhorar (Ações Propostas)

### Fase A: Evolução do Schema
Para sustentar a geração de um JSON-LD rico, precisamos expandir algumas colunas ou criar visões (Views):

1.  **Na tabela `roteiros_ouro` (O principal alvo do JSON-LD):**
    *   Temos `titulo_produto`, mas falta `codigo_produto` (SKU / ID Magalu). Isso é vital para "linkar" o roteiro ao produto exato.
    *   *Alteração Necessária:* Adicionar coluna `codigo_produto` (varchar) na tabela `roteiros_ouro`.

2.  **Na tabela `categorias`:**
    *   Para o JSON-LD, é útil ter um slug ou identificador sem espaços. (Ex: `"nome": "Móveis e Colchões"`, `"slug": "moveis-e-colchoes"`). Opcional, mas recomendado para URLs.

### Fase B: O Motor JSON-LD no Python (Amanhã)
A verdadeira "mágica" acontecerá no código Python (Streamlit local ou API futura).
Podemos construir uma função `generate_json_ld(roteiro_id)` que faz um JOIN entre `roteiros_ouro` e `categorias`, gerando algo como:

```json
{
  "@context": "https://schema.org/",
  "@type": "Product",
  "name": "{titulo_produto}",
  "sku": "{codigo_produto}",
  "category": "{categorias.nome}",
  "description": "{roteiro_perfeito}",
  "review": {
    "@type": "Review",
    "author": {
      "@type": "Person",
      "name": "Breno_AI_Suite"
    }
  }
}
```

## 5. Próximos Passos (Aprovação do Tiago)

1.  **[ ] Aceite da Alteração do Schema:** Você aprova a adição de `codigo_produto` na tabela `roteiros_ouro` para podermos fazer o "match" exato do JSON-LD amanhã?
2.  **[ ] Revisão:** O conceito de transformar os Roteiros Ouro em "Packages" de JSON-LD atende à sua visão? (Se sim, amanhã, além de corrigir o scraper, implementamos um botão "Exportar JSON-LD" do lado de cada roteiro ouro).
