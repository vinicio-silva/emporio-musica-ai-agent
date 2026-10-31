"""Script to render and download compiled Mermaid diagram images for documentation."""

import base64
import json
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "docs" / "images"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DIAGRAMS = {
    "development_methodology.png": """flowchart TD
    Lead["Lead Architect / Orchestrator<br/>(High Reasoning - Pro)<br/>• API contracts & Pydantic schema design<br/>• Consultative sales & hardening prompt design<br/>• Code review & delivery sign-off"]
    
    Lead -->|Parallel Task 1| WorkerDB["Data Worker<br/>(Low Reasoning - Fast)<br/>• CSV ingestion to SQLite<br/>• Relational schema & indexes"]
    Lead -->|Parallel Task 2| WorkerUI["Frontend Worker<br/>(Low Reasoning - Fast)<br/>• Storefront HTML5/Tailwind layout<br/>• Floating chat widget & async API bridge"]
    
    WorkerDB -->|Validated Code| Lead
    WorkerUI -->|Validated Code| Lead
    
    Lead --> LeadAI["AI Core Implementation<br/>(High Reasoning - Pro)<br/>• Policy RAG indexing engine<br/>• Replicate (Llama 3.1 70B) / OpenAI connector<br/>• Intent router & security guardrails"]
    
    LeadAI --> WorkerQA["QA Worker<br/>(Low/Mid Reasoning - Fast)<br/>• Pytest execution<br/>• Penetration, jailbreak & security tests<br/>• Official 5 test scenario dialogue recording"]
    
    WorkerQA --> FinalReview["Verified Delivery Ready for Submission"]""",

    "hierarchical_architecture.png": """flowchart TD
    User([Customer Message in Portuguese]) --> Sanitize["Input Sanitization & Delimiters"]
    Sanitize --> Router["1. Intent & Guardrail Router<br/>(Fast / Low-Reasoning)"]
    
    Router -->|Out of Scope: Accessories/Other| GuardrailHandler["2a. Guardrail Handler<br/>(Polite Deflection + Partner Redirect)"]
    Router -->|Catalog / Prices / Inventory| SalesAgent["2b. Consultative Sales Worker<br/>(High-Reasoning / Parameterized SQL Engine)"]
    Router -->|Order Status / Tracking| OrderAgent["2c. Order Support Worker - LGPD Safe<br/>(Fast Reasoning / Secure Order Lookup)"]
    Router -->|Store Policies / Institutional| PolicyAgent["2d. Policy & Compliance Worker<br/>(High-Reasoning / Semantic RAG)"]
    
    SalesAgent --> Synthesizer["3. Response Synthesizer<br/>(Persona: Empório da Música Musician)"]
    OrderAgent --> Synthesizer
    PolicyAgent --> Synthesizer
    GuardrailHandler --> Synthesizer
    
    Synthesizer --> ClientResponse([Final Response to Customer])""",

    "security_hardening_layers.png": """flowchart TD
    In([Customer Message]) --> L1["Layer 1: Sanitization & Context Delimiters<br/>(Blocks context-breaking XML injection)"]
    L1 --> L2["Layer 2: Prompt Hardening & Immutability<br/>(Defeats Jailbreaks, 'ignore instructions', DAN)"]
    L2 --> L3["Layer 3: Scope & Accessory Guardrails<br/>(Deflects strings, pedals, cables politely)"]
    L3 --> L4["Layer 4: Parameterized Queries / Anti-SQLi<br/>(LLM executes typed tools, never raw SQL)"]
    L4 --> L5["Layer 5: PII Protection / LGPD Compliance<br/>(Requires order auth, prevents data dumps)"]
    L5 --> Out([Safe & Verified Agent Execution])"""
}

for name, code in DIAGRAMS.items():
    graph_obj = {
        "code": code,
        "mermaid": {"theme": "default"}
    }
    b64 = base64.b64encode(json.dumps(graph_obj).encode("utf-8")).decode("ascii")
    url = f"https://mermaid.ink/img/{b64}?type=png"
    
    print(f"Rendering {name}...")
    resp = requests.get(url, timeout=20)
    if resp.status_code == 200:
        target = OUT_DIR / name
        target.write_bytes(resp.content)
        print(f"Saved {target} ({len(resp.content)} bytes)")
    else:
        print(f"Failed {name}: status {resp.status_code}")

print("Diagram generation completed.")
