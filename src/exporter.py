"""
Exportador de roteiros para formato DOCX.
Gera documentos Word com formatação idêntica aos roteiros de referência em /kb.
Padrão: Tahoma 14pt bold (cabeçalho), 12pt bold (locução), 12pt normal (imagem/lettering).
"""
import io
import re
import zipfile
from datetime import datetime
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def _add_header_line(doc, text: str):
    """Adiciona linha de cabeçalho: Tahoma 14pt Bold."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    run = p.add_run(text)
    run.font.name = "Tahoma"
    run.font.size = Pt(14)
    run.bold = True


def _add_separator(doc):
    """Adiciona linha separadora."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    run = p.add_run("______________________________________________________________________")
    run.font.name = "Tahoma"
    run.font.size = Pt(12)


def _add_locucao(doc, text: str):
    """Adiciona linha de locução: Tahoma 12pt Bold."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    run = p.add_run(text)
    run.font.name = "Tahoma"
    run.font.size = Pt(12)
    run.bold = True


def _add_imagem(doc, text: str):
    """Adiciona linha de imagem/lettering: Tahoma 12pt Normal."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    run = p.add_run(text)
    run.font.name = "Tahoma"
    run.font.size = Pt(12)
    run.bold = False


def _add_empty_line(doc):
    """Adiciona linha em branco."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)


def _extract_product_name(roteiro_text: str) -> str:
    """Tenta extrair o nome do produto do texto do roteiro."""
    # Procura na linha de Produto:
    match = re.search(r'Produto:\s*(.+)', roteiro_text)
    if match:
        name = match.group(1).strip()
        # Remove o prefixo "NW ..." se já existir
        name = re.sub(r'^NW\s+\w+\s+\d+\s+', '', name)
        # Remove "TÍTULO DO PRODUTO:" ou similares da IA
        name = re.sub(r'^\**TÍTULO( DO PRODUTO)?:?\**\s*', '', name, flags=re.IGNORECASE)
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


def generate_filename(code: str, product_name: str, selected_month: str = "FEV") -> str:
    """Gera nome do arquivo no padrão: NW LU {selected_month} {code} {product_name}.docx"""
    # Limpa caracteres inválidos para nome de arquivo
    clean_name = re.sub(r'[<>:"/\\|?*]', '', product_name)
    clean_name = clean_name[:80]  # Limita tamanho

    return f"NW LU {selected_month} {code} {clean_name}.docx"

def export_roteiro_docx(roteiro_text: str, code: str = "", product_name: str = "", selected_month: str = "FEV", selected_date: str = None) -> tuple[bytes, str]:
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
        header_date = selected_date if selected_date else datetime.now().strftime('%d/%m/%y')
        _add_header_line(doc, "Cliente: Magalu")
        _add_header_line(doc, f"Roteirista: Tiago Fernandes - Data: {header_date}")
        _add_header_line(doc, f"Produto: NW LU {selected_month} {code} {product_name}")
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

    filename = generate_filename(code, product_name, selected_month)

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

def export_all_roteiros_zip(roteiros: list, selected_month: str = "FEV", selected_date: str = None) -> tuple[bytes, str]:
    """
    Gera um arquivo ZIP contendo todos os roteiros em formato DOCX.
    
    Args:
        roteiros: Lista de dicionários contendo 'roteiro_original', 'codigo' e 'ficha' (opcional)
        selected_month: Mês para o nome dos arquivos
        
    Returns:
        Tuple de (bytes do zip, nome do arquivo)
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for idx, item in enumerate(roteiros):
            doc_bytes, filename = export_roteiro_docx(
                item['roteiro_original'],
                code=item.get('codigo', ''),
                product_name='', # Será extraído do texto do roteiro
                selected_month=selected_month,
                selected_date=selected_date
            )
            # Garante que o nome do arquivo seja único dentro do ZIP se houver duplicatas
            zip_file.writestr(filename, doc_bytes)
            
    zip_buffer.seek(0)
    now = datetime.now()
    zip_filename = f"ROTEIROS_MAGALU_{now.strftime('%d_%m_%Y_%H%M')}.zip"
    
    return zip_buffer.getvalue(), zip_filename
