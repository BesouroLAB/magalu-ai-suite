# Docs Técnicos SOTA V3.0 (Magalu AI Suite)
## 💡 Visão Geral do Sistema de Calibragem

A **Calibragem de IA (SOTA V3.0)** é a engenharia core do Magalu AI Suite responsável por criar um ciclo contínuo de aprendizado. Ela não apenas avalia a similaridade entre textos, mas atua como uma malha fina que extrai aprendizados táticos, padronizações de oralidade, fonéticas, e a própria estrutura narrativa dos roteiros.

### Timeline de Evolução (Até V3.0 State of the Art)

*   **V1.0 - O Roteirista Base:** O sistema foi construído. A IA gerava o roteiro apenas se baseando em Prompts Estáticos (System Prompts). Modelos sofriam com alucinação e jargões robóticos.
*   **V2.0 - Memória e Nuance (Fine Tuning In-Prompt):** Foi integrado o Supabase com as tabelas de `nw_treinamento_persona_lu`, `nw_treinamento_fonetica`, `nw_treinamento_estruturas`, e roteiros "Ouro". O agente principal (`agent.py`) passou a injetar esse contexto (os últimos aprendizados) nos seus prompts, garantindo alinhamento progressivo.
*   **V2.5 - UI Feedback Loop:** Construção do componente de interface de calibragem (`app.py`), onde redatores passaram a colar o "Antes (IA)" e o "Depois (Humano)" e gerar diagnósticos qualitativos (Aproveitamento Total, Direção Criativa, Notas em %).
*   **V3.0 SOTA (State of the Art):** Padronização rígida de dados. Forçamento de extração literal. Refatoramento de prompt (`agent.py:530-555`) para eliminação de "Nones" e `null` salvos indevidamente. Unificação pragmática do motor NW e NW 3D. Expansão das 'Estruturas' para aceitar também _"Desenvolvimento (Venda)"_ além dos tradicionais _hook_ e _CTA_. Fallback chain entre modelos para alta disponibilidade sem atrito de custos (Grok -> DeepSeek -> Gemini).

### Funcionamento do Fallback Chain
A função inferencial de calibragem tem o desafio de parsear dados JSON de descrições sutis da formatação de texto. Como o custo seria exorbitante usando top-tier pago constantemente, utilizamos:
1.  **Grok 4.1 Fast (Puter):** Tentativa primária, rápido.
2.  **DeepSeek R1 (OpenRouter):** Back-up confiável.
3.  **Gemini 3 Flash (Google API):** Last resort, extremamente capaz, porém sujeito a limits quota. 

### Schema e Modelagem do BD (Supabase)
O design atual obedece a um isolamento flexível:
- `nw_roteiros_ouro`: Onde salva-se o script limpo humano (referência absoluta) e seu `aprendizado` (resumo).
- `nw_treinamento_estruturas`: Foca em grandes blocos lógicos (`texto_ouro` e `texto_ia_rejeitado`). Tipos: _"Abertura (Gancho)", "Fechamento (CTA)", "Desenvolvimento (Venda)"_.
- `nw_treinamento_persona_lu`: Armazena a transição da linguagem máquina (`texto_gerado_ia`) para a fala humana (`texto_corrigido_humano`).
- `nw_treinamento_fonetica`: Traduz termos técnicos proibidos em dicção correta locucionada (e.g. "85W" para "3 velocidades").
- `nw_treinamento_imagens`: Acompanha a redução ou mutação das descrições imagéticas do editor.

**NOTA TÉCNICA (Unificação V3.0):** Para `Fonética` e `Persona`, convencionamos que eles derivam da "Alma da Marca" não do "Formato". Logo, a calibração de roteiros *NW 3D* e *NW Standard* alimentam o mesmo pool no Supabase (as tabelas `nw_...` primárias).
