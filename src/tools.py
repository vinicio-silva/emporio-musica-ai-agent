"""Agent tool definitions and Pydantic schemas for Empório da Música.

Provides strongly-typed parameters, JSON tool schemas for LLM function calling,
and deterministic execution connecting to SQLite and Policy RAG.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.database import get_order_status, get_product_details, search_products
from src.rag import search_store_policy


# ==========================================
# Pydantic Schemas for Tool Arguments
# ==========================================

class SearchProductsInput(BaseModel):
    keyword: Optional[str] = Field(
        default=None,
        description="Search keyword for instrument name or description (e.g. 'violão', 'yamaha', 'guitarra', 'stratocaster').",
    )
    max_price: Optional[float] = Field(
        default=None,
        description="Maximum budget in Brazilian Reais (BRL). e.g. 1000.0.",
    )
    category: Optional[str] = Field(
        default=None,
        description="Category name (e.g. 'Violões', 'Guitarras', 'Baixos', 'Teclados').",
    )
    in_stock_only: bool = Field(
        default=True,
        description="Whether to only return items with stock_quantity > 0.",
    )


class ProductDetailsInput(BaseModel):
    product_identifier: str = Field(
        description="Numeric product ID or full/partial instrument name (e.g. 'Takamine GD20' or '81')."
    )


class CheckOrderInput(BaseModel):
    tracking_code: str = Field(
        description="Official carrier tracking code (e.g. 'BRAB1234567BR')."
    )
    customer_identifier: str = Field(
        description="Customer email or phone number for dual-factor LGPD validation."
    )


class StorePolicyInput(BaseModel):
    question: str = Field(
        description="The customer's question regarding store policies, hours, address, returns, payments, or shipping."
    )
    topic: Optional[str] = Field(
        default=None,
        description="Optional policy topic (e.g. 'trocas', 'frete', 'pagamento', 'garantia', 'horario', 'endereco').",
    )


# ==========================================
# Concrete Tool Implementations
# ==========================================

def tool_search_products(
    keyword: Optional[str] = None,
    max_price: Optional[float] = None,
    category: Optional[str] = None,
    in_stock_only: bool = True,
) -> Dict[str, Any]:
    """Search catalog instruments with parameterized SQL and calculated payment terms."""
    items = search_products(
        keyword=keyword,
        max_price=max_price,
        category_name=category,
        in_stock_only=in_stock_only,
    )
    return {
        "count": len(items),
        "products": items,
    }


def tool_get_product_details(product_identifier: str) -> Dict[str, Any]:
    """Retrieve full specifications, stock availability, and prices for a single instrument."""
    item = get_product_details(product_identifier)
    if not item:
        return {
            "found": False,
            "message": f"Nenhum produto encontrado para o identificador '{product_identifier}'.",
        }
    return {
        "found": True,
        "product": item,
    }


def tool_check_order(tracking_code: str, customer_identifier: str) -> Dict[str, Any]:
    """Query order lifecycle and tracking with dual-factor LGPD verification."""
    return get_order_status(tracking_code=tracking_code, customer_identifier=customer_identifier)


def tool_query_store_policy(question: str, topic: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve official store policy excerpts from the Store Manual (PDF) using hybrid RAG."""
    hits = search_store_policy(query=question, top_k=2, topic=topic)
    return {
        "matches_count": len(hits),
        "policies": hits,
    }


# ==========================================
# Tool Registry and Execution Dispatcher
# ==========================================

TOOLS_METADATA = [
    {
        "type": "function",
        "function": {
            "name": "tool_search_products",
            "description": "Busca instrumentos musicais no catálogo por palavra-chave, preço máximo e categoria. Retorna preços com 5% de desconto no PIX e parcelamento em até 12x.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Termo de busca (ex: 'violão', 'Takamine', 'Yamaha')"},
                    "max_price": {"type": "number", "description": "Preço máximo em reais (ex: 1000.0)"},
                    "category": {"type": "string", "description": "Categoria (ex: 'Violões', 'Guitarras')"},
                    "in_stock_only": {"type": "boolean", "default": True, "description": "Apenas produtos em estoque"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tool_get_product_details",
            "description": "Obtém detalhes completos, especificações técnicas (madeiras, escala, captação), estoque e preços de um instrumento específico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_identifier": {"type": "string", "description": "Nome ou ID do produto (ex: 'Takamine GD20' ou '95')"}
                },
                "required": ["product_identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tool_check_order",
            "description": "Consulta o status e rastreamento de um pedido. Exige validação dupla LGPD (código de rastreio e e-mail ou telefone do titular).",
            "parameters": {
                "type": "object",
                "properties": {
                    "tracking_code": {"type": "string", "description": "Código de rastreamento (ex: 'BRAB1234567BR')"},
                    "customer_identifier": {"type": "string", "description": "E-mail ou telefone do comprador titular"},
                },
                "required": ["tracking_code", "customer_identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tool_query_store_policy",
            "description": "Consulta o Manual Oficial de Políticas da Loja sobre trocas, devoluções, direito de arrependimento (CDC 7 dias), frete, formas de pagamento, endereço e horário de atendimento.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Pergunta ou dúvida sobre as políticas da loja"},
                    "topic": {"type": "string", "description": "Tópico opcional ('trocas', 'frete', 'pagamento', 'horario', 'endereco')"},
                },
                "required": ["question"],
            },
        },
    },
]

TOOL_FUNCTION_MAP = {
    "tool_search_products": tool_search_products,
    "tool_get_product_details": tool_get_product_details,
    "tool_check_order": tool_check_order,
    "tool_query_store_policy": tool_query_store_policy,
}


def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a registered tool deterministically by name with validated arguments."""
    func = TOOL_FUNCTION_MAP.get(name)
    if not func:
        return {"error": f"Tool '{name}' is not registered."}
    try:
        return func(**arguments)
    except Exception as exc:
        return {"error": f"Error executing tool '{name}': {str(exc)}"}
