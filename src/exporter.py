"""
Exportador de roteiros para formato DOCX.
Gera documentos Word com formatação idêntica aos roteiros de referência em /kb.
Padrão: Tahoma 14pt bold (cabeçalho), 12pt bold (locução), 12pt normal (imagem/lettering).
"""
import io
import re
from datetime import datetime
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH


def _add_header_line(doc, text: str):
    """Adiciona linha de cabeçalho: Tahoma 14pt Bold."""
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Tahoma"
    run.font.size = Pt(14)
    run.bold = True


def _add_separator(doc):
    """Adiciona linha separadora."""
    p = doc.add_paragraph()
    run = p.add_run("______________________________________________________________________")
    run.font.name = "Tahoma"
    run.font.size = Pt(12)


def _add_locucao(doc, text: str):
    """Adiciona linha de locução: Tahoma 12pt Bold."""
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Tahoma"
    run.font.size = Pt(12)
    run.bold = True


def _add_imagem(doc, text: str):
    """Adiciona linha de imagem/lettering: Tahoma 12pt Normal."""
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Tahoma"
    run.font.size = Pt(12)
    run.bold = False


def _add_empty_line(doc):
    """Adiciona linha em branco."""
    doc.add_paragraph()


def _extract_product_name(roteiro_text: str) -> str:
    """Tenta extrair o nome do produto do texto do roteiro."""
    # Procura na linha de Produto:
    match = re.search(r'Produto:\s*(.+)', roteiro_text)
    if match:
        name = match.group(1).strip()
        # Remove o prefixo "NW ..." se já existir
        name = re.sub(r'^NW\s+\w+\s+\d+\s+', '', name)
        return name

    # Fallback: procura no título (primeiras palavras do roteiro que parecem nome de produto)
    lines = roteiro_text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('- ') and ('da ' in line or 'do ' in line):
            # Tenta extrair "Este [Produto], da [Marca]"
            match2 = re.search(r'Est[ea]\s+(.+?),\s+d[ao]', line)
            if match2:
                return match2.group(1).strip()

    return "Produto"


def _parse_roteiro(roteiro_text: str) -> list[dict]:
    """
    Parseia o texto bruto do roteiro em blocos estruturados.
    Retorna lista de dicts com tipo (header, separator, locucao, imagem, lettering, empty).
    """
    blocks = []
    lines = roteiro_text.strip().split('\n')

    for line in lines:
        stripped = line.strip()

        if not stripped:
            blocks.append({"type": "empty"})
        elif stripped.startswith("Cliente:"):
            blocks.append({"type": "header", "text": stripped})
        elif stripped.startswith("Roteirista:"):
            blocks.append({"type": "header", "text": stripped})
        elif stripped.startswith("Produto:"):
            blocks.append({"type": "header", "text": stripped})
        elif stripped.startswith("____"):
            blocks.append({"type": "separator"})
        elif stripped.startswith("Imagem:"):
            blocks.append({"type": "imagem", "text": stripped})
        elif stripped.startswith("Lettering:"):
            blocks.append({"type": "lettering", "text": stripped})
        elif stripped.startswith("- "):
            blocks.append({"type": "locucao", "text": stripped})
        elif stripped.startswith("**") and stripped.endswith("**"):
            # Markdown bold — remover asteriscos
            clean = stripped.strip("*").strip()
            if clean.startswith("- "):
                blocks.append({"type": "locucao", "text": clean})
            else:
                blocks.append({"type": "locucao", "text": f"- {clean}"})
        else:
            # Linhas genéricas — tratar como parte do corpo
            blocks.append({"type": "text", "text": stripped})

    return blocks


def generate_filename(code: str, product_name: str) -> str:
    """Gera nome do arquivo no padrão: NW FEV {code} {product_name}.docx"""
    now = datetime.now()
    month_map = {
        1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
        7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
    }
    month = month_map.get(now.month, "FEV")

    # Limpa caracteres inválidos para nome de arquivo
    clean_name = re.sub(r'[<>:"/\\|?*]', '', product_name)
    clean_name = clean_name[:80]  # Limita tamanho

    return f"NW {month} {code} {clean_name}.docx"


def export_roteiro_docx(roteiro_text: str, code: str = "", product_name: str = "") -> tuple[bytes, str]:
    """
    Gera um documento Word (.docx) com a formatação de referência.

    Args:
        roteiro_text: Texto completo do roteiro gerado pela IA
        code: Código do produto Magalu
        product_name: Nome do produto (extraído automaticamente se vazio)

    Returns:
        Tuple de (bytes do docx, nome do arquivo)
    """
    doc = Document()

    # Configura estilo padrão
    style = doc.styles['Normal']
    style.font.name = 'Tahoma'
    style.font.size = Pt(12)

    # Extrai nome do produto se não fornecido
    if not product_name:
        product_name = _extract_product_name(roteiro_text)

    # Parseia o roteiro
    blocks = _parse_roteiro(roteiro_text)

    # Verifica se já tem cabeçalho no texto
    has_header = any(b["type"] == "header" for b in blocks)

    if not has_header:
        # Gera cabeçalho padrão
        now = datetime.now()
        _add_header_line(doc, "Cliente: Magalu")
        _add_header_line(doc, f"Roteirista: IA Magalu -- Data: {now.strftime('%d/%m/%y')}")
        _add_header_line(doc, f"Produto: NW FEV {code} {product_name}")
        _add_separator(doc)
        _add_empty_line(doc)

    # Renderiza cada bloco
    for block in blocks:
        btype = block["type"]
        text = block.get("text", "")

        if btype == "header":
            # Corrige a data se necessário
            if "Data:" in text:
                now = datetime.now()
                text = re.sub(r'Data:\s*[\d/]+', f"Data: {now.strftime('%d/%m/%y')}", text)
            _add_header_line(doc, text)
        elif btype == "separator":
            _add_separator(doc)
        elif btype == "locucao":
            _add_locucao(doc, text)
        elif btype == "imagem":
            _add_imagem(doc, text)
        elif btype == "lettering":
            _add_imagem(doc, text)
        elif btype == "empty":
            _add_empty_line(doc)
        elif btype == "text":
            _add_imagem(doc, text)

    # Gera bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    filename = generate_filename(code, product_name)

    return buffer.getvalue(), filename


def format_for_display(roteiro_text: str) -> str:
    """
    Formata o roteiro para exibição no Streamlit com Markdown.
    Locução em **bold**, Imagem sem bold, com quebra de linha.
    """
    lines = roteiro_text.strip().split('\n')
    formatted = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            formatted.append("")
        elif stripped.startswith("Cliente:") or stripped.startswith("Roteirista:") or stripped.startswith("Produto:"):
            formatted.append(f"**{stripped}**")
        elif stripped.startswith("____"):
            formatted.append("---")
        elif stripped.startswith("- "):
            # Verifica se tem "Imagem:" inline (separar)
            if "Imagem:" in stripped:
                parts = stripped.split("Imagem:", 1)
                locucao = parts[0].strip()
                imagem = "Imagem:" + parts[1]
                formatted.append(f"**{locucao}**")
                formatted.append(f"\n{imagem}")
            else:
                formatted.append(f"**{stripped}**")
        elif stripped.startswith("Imagem:"):
            formatted.append(stripped)
        elif stripped.startswith("Lettering:"):
            formatted.append(stripped)
        else:
            formatted.append(stripped)

    return "\n".join(formatted)
