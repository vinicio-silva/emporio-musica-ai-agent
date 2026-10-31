"""Unit and retrieval precision tests for Empório da Música Policy RAG."""

import pytest
from src.rag import PolicyRAGEngine, get_rag_engine, search_store_policy


@pytest.fixture(scope="module")
def rag_engine():
    return get_rag_engine()


def test_pdf_loading_and_chunk_count(rag_engine):
    """Verify PDF was loaded and chunked into distinct semantic chapters."""
    assert len(rag_engine.chunks) >= 10, f"Expected at least 10 policy chunks, got {len(rag_engine.chunks)}"


def test_section_address_and_hours_retrieval(rag_engine):
    """Scenario 2 check: address and business hours retrieval."""
    hits = rag_engine.search("Qual o endereço da loja e horário de funcionamento?", top_k=2)
    assert len(hits) > 0
    top_titles = [h["title"] for h in hits]
    # Should retrieve Section 1 (Dados da Empresa) or Section 2 (Horário de Funcionamento)
    matched = any("Horário" in t or "Dados da Empresa" in t or "Sobre a Empório" in t for t in top_titles)
    assert matched, f"Expected store info sections, got {top_titles}"

    # Verify content contains the canonical address and hours
    combined_content = " ".join(h["content"] for h in hits)
    assert "14 de Maio" in combined_content or "Horário" in combined_content


def test_right_of_regret_cdc_retrieval(rag_engine):
    """Scenario 4 check: return policy and CDC right of regret within 7 days."""
    hits = rag_engine.search("Me arrependi da minha compra online, posso devolver?", top_k=2)
    assert len(hits) > 0
    top_hit = hits[0]
    assert "4.1" in top_hit["section_id"] or "Arrependimento" in top_hit["title"] or "Troca" in top_hit["title"]
    assert "7" in top_hit["content"]
    assert "dias" in top_hit["content"]


def test_shipping_policy_retrieval(rag_engine):
    """Verify local Campo Grande and national shipping retrieval."""
    hits = rag_engine.search("Como funciona a entrega e frete em Campo Grande?", top_k=2)
    assert len(hits) > 0
    combined = " ".join(h["content"] for h in hits)
    assert "Campo Grande" in combined or "Frete" in combined


def test_payment_methods_retrieval(rag_engine):
    """Verify payment terms retrieval (PIX discount and installment)."""
    hits = rag_engine.search("Quais são as formas de pagamento e desconto no PIX?", top_k=2)
    assert len(hits) > 0
    combined = " ".join(h["content"] for h in hits)
    assert "PIX" in combined
    assert "5%" in combined
