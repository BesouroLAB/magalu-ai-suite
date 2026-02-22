# Planejamento: Roteirista Magalu AI (MVP)

Projeto: Sistema de Geração de Roteiros baseados em RAG e Few-Shot Prompting.
Pilar Tecnológico: Python, Streamlit, Google Gemini API, BeautifulSoup.

## Fases de Implementação
1. **Configuração do Ambiente Local**:
   - Bibliotecas: `streamlit`, `beautifulsoup4`, `requests`, `google-generativeai`, `python-dotenv`.
   - Organização: Pastas separadas para Inteligência (`.agents`, `kb`) e Sistema (`src`).
2. **Setup da Inteligência Fria (RAG local)**:
   - Inserir textos do Magalu na rotina.
   - Definir regras do Breno no Prompt de Sistema.
3. **Módulo de Scraper**:
   - `scraper.py`: Extração apenas do título e conteúdo principal, evitando rodapés.
4. **Módulo Gemini**:
   - Conexão e prompt builder juntando as fatias de contexto estático e dados rasgados.
5. **App (Streamlit)**:
   - Interface rápida para operação do Head / Editor, visualização de resultado e "Aprovar" (gerando Feedback logs).
