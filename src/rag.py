"""Policy RAG (Retrieval-Augmented Generation) engine for Empório da Música.

Extracts store policy manual from PDF, segments it into structured semantic
chunks by section, and provides hybrid lexical and semantic retrieval.
"""

from __future__ import annotations

import math
import os
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pymupdf

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def normalize_text(text: str) -> str:
    """Normalize text by lowercasing and stripping diacritics for resilient keyword matching."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return stripped.lower()


SYNONYM_MAP = {
    "encordoamento": ["cordas", "corda", "acessorios"],
    "encordoamentos": ["cordas", "corda", "acessorios"],
    "pedal": ["pedais", "acessorios"],
    "pedais": ["pedal", "acessorios"],
    "cordas": ["corda", "encordoamento", "acessorios"],
    "palheta": ["palhetas", "acessorios"],
    "palhetas": ["palheta", "acessorios"],
    "amplificador": ["amplificadores", "acessorios"],
    "amplificadores": ["amplificador", "acessorios"],
    "cabo": ["cabos", "acessorios"],
    "cabos": ["cabo", "acessorios"],
    "devolver": ["devolucao", "arrependimento", "reembolso"],
    "devolucao": ["devolver", "arrependimento", "reembolso"],
    "arrepender": ["arrependimento", "devolucao", "7 dias"],
    "arrependi": ["arrependimento", "devolucao", "7 dias"],
    "endereco": ["localizacao", "onde fica", "rua 14 de maio", "campo grande"],
    "localizacao": ["endereco", "onde fica", "rua 14 de maio"],
    "horario": ["funcionamento", "abertura", "fechamento", "sabado"],
}


def expand_query_tokens(tokens: List[str]) -> List[str]:
    """Expand query tokens with domain synonyms for store policies."""
    expanded = list(tokens)
    for tok in tokens:
        if tok in SYNONYM_MAP:
            for syn in SYNONYM_MAP[tok]:
                norm_syn = normalize_text(syn)
                if norm_syn not in expanded:
                    expanded.append(norm_syn)
    return expanded


def tokenize(text: str) -> List[str]:
    """Tokenize normalized text into clean alphanumeric words."""
    norm = normalize_text(text)
    return re.findall(r"\b[a-z0-9]{2,}\b", norm)


class PolicyChunk:
    """Structured semantic chunk representing an official policy chapter or subsection."""

    def __init__(
        self,
        section_id: str,
        title: str,
        content: str,
        page_num: int,
        keywords: Optional[List[str]] = None,
    ):
        self.section_id = section_id
        self.title = title
        self.content = content.strip()
        self.page_num = page_num
        self.keywords = keywords or []
        # Pre-tokenize for fast BM25 / lexical scoring
        self.tokens = tokenize(f"{title} {content} {' '.join(self.keywords)}")
        self.token_set = set(self.tokens)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "content": self.content,
            "page_num": self.page_num,
            "keywords": self.keywords,
        }


class PolicyRAGEngine:
    """Hybrid lexical and semantic retrieval engine for store policies."""

    def __init__(self, data_dir: Path | str = DATA_DIR):
        self.data_dir = Path(data_dir)
        self.chunks: List[PolicyChunk] = []
        self._doc_frequencies: Counter[str] = Counter()
        self._avg_dl: float = 0.0
        self._load_and_chunk()

    def _find_pdf(self) -> Path:
        """Locate the policy PDF file with resilient filename matching."""
        candidates = list(self.data_dir.glob("*pol*ticas*.pdf"))
        if not candidates:
            # Fallback to any PDF in data
            candidates = list(self.data_dir.glob("*.pdf"))
        if not candidates:
            raise FileNotFoundError(f"Store policy manual PDF not found in {self.data_dir}")
        return candidates[0]

    def _load_and_chunk(self) -> None:
        """Extract text from PDF and segment into structured semantic sections."""
        pdf_path = self._find_pdf()
        doc = pymupdf.open(pdf_path)

        raw_pages: List[Tuple[int, str]] = []
        for page_idx in range(len(doc)):
            page_text = doc[page_idx].get_text().replace("\u200b", "").strip()
            raw_pages.append((page_idx + 1, page_text))
        doc.close()

        # Combine page texts into full document while retaining page references
        full_text = "\n\n".join(text for _, text in raw_pages)

        # Regex matching numbered section headings: e.g. "1. Sobre a Empório", "4.1 Direito de Arrependimento"
        section_pattern = re.compile(
            r"(?m)^(?:Seção\s+)?([0-9]+(?:\.[0-9]+)*)\.?\s+([A-ZÀ-Ú][^\n]{3,60})$"
        )

        matches = list(section_pattern.finditer(full_text))

        if matches:
            for i, match in enumerate(matches):
                sec_num = match.group(1).strip()
                sec_title = match.group(2).strip()
                start_pos = match.start()
                end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
                sec_content = full_text[start_pos:end_pos].strip()

                # Approximate page number
                approx_page = 1
                char_count = 0
                for page_num, text in raw_pages:
                    char_count += len(text)
                    if start_pos <= char_count:
                        approx_page = page_num
                        break

                # Extract domain-specific keywords for relevance boosting
                keywords = []
                main_sec = sec_num.split(".")[0]
                if main_sec == "1":
                    keywords.extend(["endereco", "rua 14 de maio", "campo grande", "cnpj", "missao", "telefone", "whatsapp", "acessorios", "exclusivamente instrumentos"])
                if main_sec == "2":
                    keywords.extend(["horario", "funcionamento", "sabado", "domingo", "abertura", "fechamento", "expediente"])
                if main_sec == "3":
                    keywords.extend(["pagamento", "pix", "desconto", "cartao", "credito", "parcelamento", "sem juros", "boleto"])
                if main_sec == "4":
                    keywords.extend(["troca", "devolucao", "arrependimento", "defeito", "7 dias", "cdc", "reembolso", "prazo", "30 dias", "embalagem original"])
                if main_sec == "5":
                    keywords.extend(["frete", "entrega", "sedex", "pac", "jadlog", "rastreamento", "gratis", "motoboy", "prazo"])
                if main_sec == "6":
                    keywords.extend(["promocao", "promocoes", "desconto", "cumulativo", "cupom", "ativa"])
                if main_sec == "7":
                    keywords.extend(["atendimento", "acessorios", "cordas", "pedais", "amplificadores", "palhetas", "cabos", "cases", "fora de estoque", "parceiras"])
                if main_sec == "8":
                    keywords.extend(["garantia", "legal", "fabricante", "90 dias", "defeito"])
                if main_sec == "9":
                    keywords.extend(["privacidade", "lgpd", "dados", "pessoais", "seguranca"])

                chunk = PolicyChunk(
                    section_id=sec_num,
                    title=f"Seção {sec_num} — {sec_title}",
                    content=sec_content,
                    page_num=approx_page,
                    keywords=keywords,
                )
                self.chunks.append(chunk)

        # Fallback if regex extracted too few chunks
        if len(self.chunks) < 5:
            # Chunk page by page
            self.chunks.clear()
            for page_num, text in raw_pages:
                if len(text) < 50:
                    continue
                chunk = PolicyChunk(
                    section_id=f"P{page_num}",
                    title=f"Manual de Políticas — Página {page_num}",
                    content=text,
                    page_num=page_num,
                )
                self.chunks.append(chunk)

        # Compute corpus statistics for BM25
        total_len = 0
        for chunk in self.chunks:
            total_len += len(chunk.tokens)
            for token in set(chunk.tokens):
                self._doc_frequencies[token] += 1
        self._avg_dl = (total_len / len(self.chunks)) if self.chunks else 1.0

    def _bm25_score(self, query_tokens: List[str], chunk: PolicyChunk, k1: float = 1.5, b: float = 0.75) -> float:
        """Calculate BM25 relevance score between query tokens and policy chunk."""
        score = 0.0
        doc_len = len(chunk.tokens)
        num_docs = len(self.chunks)
        chunk_token_counts = Counter(chunk.tokens)

        for q in query_tokens:
            if q not in chunk_token_counts:
                continue
            tf = chunk_token_counts[q]
            df = self._doc_frequencies.get(q, 0)
            # Standard IDF with Robertson-Spärck Jones formula
            idf = math.log((num_docs - df + 0.5) / (df + 0.5) + 1.0)
            numerator = tf * (k1 + 1.0)
            denominator = tf + k1 * (1.0 - b + b * (doc_len / self._avg_dl))
            score += idf * (numerator / denominator)

        return score

    def search(
        self,
        query: str,
        top_k: int = 3,
        topic: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Perform hybrid retrieval over policy chunks with lexical BM25 and keyword affinity scoring."""
        base_tokens = tokenize(query)
        if topic:
            base_tokens.extend(tokenize(topic))
        query_tokens = expand_query_tokens(base_tokens)

        scored_chunks: List[Tuple[float, PolicyChunk]] = []

        for chunk in self.chunks:
            bm25 = self._bm25_score(query_tokens, chunk)

            # Bonus for matching title tokens or curated keywords
            bonus = 0.0
            norm_title = normalize_text(chunk.title)
            norm_content = normalize_text(chunk.content)

            for token in query_tokens:
                if token in norm_title:
                    bonus += 3.0
                if token in chunk.keywords:
                    bonus += 2.5
                if token in norm_content:
                    bonus += 0.5

            total_score = bm25 + bonus
            if total_score > 0:
                scored_chunks.append((total_score, chunk))

        # Sort descending by score
        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, chunk in scored_chunks[:top_k]:
            item = chunk.to_dict()
            item["score"] = round(score, 3)
            results.append(item)

        return results

    def get_context_for_prompt(self, query: str, top_k: int = 2) -> str:
        """Format top relevant policy excerpts as clean markdown for LLM context."""
        hits = self.search(query, top_k=top_k)
        if not hits:
            return "Nenhuma política específica encontrada para esta consulta."

        parts = []
        for h in hits:
            parts.append(
                f"### {h['title']} (Pág. {h['page_num']})\n{h['content']}"
            )
        return "\n\n---\n\n".join(parts)


# Module singleton
_engine_instance: Optional[PolicyRAGEngine] = None


def get_rag_engine() -> PolicyRAGEngine:
    """Return initialized singleton instance of PolicyRAGEngine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = PolicyRAGEngine()
    return _engine_instance


def search_store_policy(query: str, top_k: int = 3, topic: Optional[str] = None) -> List[Dict[str, Any]]:
    """Convenience search function for agent tools."""
    engine = get_rag_engine()
    return engine.search(query=query, top_k=top_k, topic=topic)


if __name__ == "__main__":
    eng = PolicyRAGEngine()
    print(f"Policy RAG initialized successfully with {len(eng.chunks)} chunks:")
    for c in eng.chunks:
        print(f"  [{c.section_id}] {c.title} (Page {c.page_num}) - {len(c.content)} chars")

    test_queries = [
        "Qual o endereço da loja e horário de funcionamento?",
        "Me arrependi da minha compra online, posso devolver meu pedido?",
        "Vocês vendem encordoamento de guitarra e pedal?",
    ]
    print("\n--- Testing Retrieval ---")
    for q in test_queries:
        print(f"\nQuery: {q}")
        matches = eng.search(q, top_k=2)
        for m in matches:
            print(f"  -> Score {m['score']}: {m['title']} (Pág. {m['page_num']})")
