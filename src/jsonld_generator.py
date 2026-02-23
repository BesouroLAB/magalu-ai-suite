"""
Gerador de JSON-LD para Roteiros Ouro.
Transforma registros do Supabase em payloads Schema.org (Product/CreativeWork).
"""
import json
from datetime import datetime


def generate_product_jsonld(roteiro: dict, categoria_nome: str = "Genérico") -> dict:
    """
    Gera um payload JSON-LD do tipo Product a partir de um registro de roteiro_ouro.
    
    Args:
        roteiro: dict com keys: titulo_produto, codigo_produto, roteiro_perfeito, criado_em
        categoria_nome: nome da categoria associada
    
    Returns:
        dict representando o JSON-LD
    """
    sku = roteiro.get("codigo_produto", "") or ""
    titulo = roteiro.get("titulo_produto", "Produto Magalu")
    descricao = roteiro.get("roteiro_perfeito", "")
    criado_em = roteiro.get("criado_em", "")

    # Monta a URL canônica do produto na Magalu (se tiver SKU)
    url_produto = f"https://www.magazineluiza.com.br/p/{sku}/" if sku else ""

    jsonld = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": titulo,
        "description": descricao[:500],  # Limit para SEO
        "category": categoria_nome,
    }

    if sku:
        jsonld["sku"] = sku
        jsonld["url"] = url_produto
        jsonld["productID"] = sku

    if criado_em:
        jsonld["datePublished"] = str(criado_em)

    jsonld["brand"] = {
        "@type": "Brand",
        "name": "Magazine Luiza"
    }

    jsonld["review"] = {
        "@type": "Review",
        "author": {
            "@type": "Organization",
            "name": "Magalu AI Suite"
        },
        "reviewBody": descricao[:300]
    }

    return jsonld


def generate_creative_work_jsonld(roteiro: dict, categoria_nome: str = "Genérico") -> dict:
    """
    Gera um payload JSON-LD do tipo CreativeWork (para o roteiro como obra criativa).
    
    Args:
        roteiro: dict com keys do roteiro_ouro
        categoria_nome: nome da categoria
    
    Returns:
        dict representando o JSON-LD
    """
    titulo = roteiro.get("titulo_produto", "Roteiro Magalu")
    descricao = roteiro.get("roteiro_perfeito", "")
    criado_em = roteiro.get("criado_em", "")
    sku = roteiro.get("codigo_produto", "") or ""

    jsonld = {
        "@context": "https://schema.org/",
        "@type": "CreativeWork",
        "name": f"Roteiro de Vídeo: {titulo}",
        "text": descricao,
        "genre": categoria_nome,
        "inLanguage": "pt-BR",
        "author": {
            "@type": "Organization",
            "name": "Magalu AI Suite"
        }
    }

    if criado_em:
        jsonld["dateCreated"] = str(criado_em)

    if sku:
        jsonld["about"] = {
            "@type": "Product",
            "sku": sku,
            "url": f"https://www.magazineluiza.com.br/p/{sku}/"
        }

    return jsonld


def export_jsonld_string(roteiro: dict, categoria_nome: str = "Genérico", schema_type: str = "Product") -> str:
    """
    Retorna o JSON-LD como string formatada, pronto para injeção em <script type="application/ld+json">.
    
    Args:
        roteiro: dict do roteiro_ouro
        categoria_nome: nome da categoria
        schema_type: "Product" ou "CreativeWork"
    
    Returns:
        String JSON formatada
    """
    if schema_type == "CreativeWork":
        payload = generate_creative_work_jsonld(roteiro, categoria_nome)
    else:
        payload = generate_product_jsonld(roteiro, categoria_nome)
    
    return json.dumps(payload, indent=2, ensure_ascii=False)


def wrap_in_script_tag(jsonld_string: str) -> str:
    """Envolve o JSON-LD em uma tag <script> pronta pra HTML."""
    return f'<script type="application/ld+json">\n{jsonld_string}\n</script>'
