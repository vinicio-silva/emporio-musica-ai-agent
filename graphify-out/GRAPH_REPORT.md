# Graph Report - desafio_tecnico_ai_eng_artefact  (2026-10-31)

## Corpus Check
- 21 files · ~16,749 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: .csv 6, .example 1, (none) 1)

## Summary
- 348 nodes · 547 edges · 16 communities (15 shown, 1 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 9 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cbaf11c5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- rag.py
- agent.py
- llm.py
- Full Implementation Action Plan — Empório da Música AI Agent
- EmporioAgent
- get_agent
- Empório da Música — AI Customer Service Agent
- api.py
- app.js
- tools.py
- Transcrição Oficial de Avaliação — Cenário 1: Busca de Catálogo com Restrição de Preço (Até R$ 1.000)
- Transcrição Oficial de Avaliação — Cenário 2: Informações Institucionais, Endereço e Horário de Funcionamento
- Transcrição Oficial de Avaliação — Cenário 3: Consulta Específica de Preço, Estoque e Ficha Técnica (Takamine GD20)
- Transcrição Oficial de Avaliação — Cenário 4: Política de Trocas e Direito de Arrependimento (CDC)
- Transcrição Oficial de Avaliação — Cenário 5: Guardrail de Escopo e Recusa Educada de Acessórios
- SessionMemory

## God Nodes (most connected - your core abstractions)
1. `get_connection()` - 14 edges
2. `search_products()` - 14 edges
3. `get_product_details()` - 14 edges
4. `EmporioAgent` - 12 edges
5. `get_order_status()` - 12 edges
6. `BaseLLMClient` - 12 edges
7. `get_agent()` - 11 edges
8. `get_llm_client()` - 11 edges
9. `init_db()` - 10 edges
10. `PolicyRAGEngine` - 10 edges

## Surprising Connections (you probably didn't know these)
- `Phase 4: Multi-Provider LLM Connector (`src/llm.py`) — *Skill: ponytail*` --references--> `ReplicateClient`  [INFERRED]
  docs/action_plan.md → src/llm.py
- `Phase 4: Multi-Provider LLM Connector (`src/llm.py`) — *Skill: ponytail*` --references--> `OpenAIClient`  [INFERRED]
  docs/action_plan.md → src/llm.py
- `Phase 4: Multi-Provider LLM Connector (`src/llm.py`) — *Skill: ponytail*` --references--> `MockClient`  [INFERRED]
  docs/action_plan.md → src/llm.py
- `agent()` --calls--> `get_agent()`  [EXTRACTED]
  tests/test_guardrails_security.py → src/agent.py
- `main()` --calls--> `get_agent()`  [EXTRACTED]
  cli.py → src/agent.py

## Import Cycles
- None detected.

## Communities (16 total, 1 thin omitted)

### Community 0 - "rag.py"
Cohesion: 0.06
Nodes (13): expand_query_tokens(), get_rag_engine(), normalize_text(), PolicyChunk, PolicyRAGEngine, search_store_policy(), tokenize(), rag_engine() (+5 more)

### Community 1 - "agent.py"
Cohesion: 0.08
Nodes (14): extract_budget(), get_connection(), get_order_status(), get_product_details(), list_all_products(), search_products(), db_conn(), test_anti_sqli_resilience() (+6 more)

### Community 2 - "llm.py"
Cohesion: 0.09
Nodes (9): Phase 4: Multi-Provider LLM Connector (`src/llm.py`) — *Skill: ponytail*, BaseLLMClient, format_llama3_prompt(), get_llm_client(), LLMResponse, MockClient, normalize_replicate_model(), OpenAIClient (+1 more)

### Community 3 - "Full Implementation Action Plan — Empório da Música AI Agent"
Cohesion: 0.06
Nodes (31): 0.1 Development Architecture (Orchestrator-Workers Pattern), 0.2 Development Model Allocation Matrix (Tiered Reasoning), 0.3 Specialized Skills Catalog & Implementation Mapping, 0. Development Methodology: Multi-Agent Orchestration & Tiered Reasoning, 1.1 Comparative Analysis: Monolithic Single-Agent vs. Hierarchical Multi-Agent, 1.2 Decision: Hierarchical Router-Worker Architecture, 1. Model Tiering Cost Comparison (Replicate Serverless Inference), 1. Target Application Architecture (+23 more)

### Community 4 - "EmporioAgent"
Cohesion: 0.08
Nodes (9): check_accessory_query(), check_jailbreak(), EmporioAgent, extract_email_or_phone(), extract_tracking_code(), agent(), test_accessory_guardrail_deflection(), test_jailbreak_and_prompt_injection_refusal() (+1 more)

### Community 5 - "get_agent"
Cohesion: 0.12
Nodes (6): main(), main(), get_agent(), init_db(), sanitize_text(), run_recording()

### Community 6 - "Empório da Música — AI Customer Service Agent"
Cohesion: 0.08
Nodes (22): 1. Agent Architecture: Hierarchical Router + Specialized Workers, 1. Model Tiering Cost Comparison (Replicate Serverless Inference), 2. Conversational Unit Economics, 2. Multi-Turn Session Memory (Sliding Window), 3. Latency Optimization & Cold Start Mitigations, 3. Production Tiered Reasoning Strategy, 4. Data Storage & Encoding Handling, 5. Full-Stack User Experience (+14 more)

### Community 7 - "api.py"
Cohesion: 0.11
Nodes (7): chat_endpoint(), ChatRequest, ChatResponse, get_products(), health_check(), reset_session(), SessionResetRequest

### Community 8 - "app.js"
Cohesion: 0.13
Nodes (19): allProducts, appendMessage(), chatCloseBtn, chatForm, chatInput, chatLauncher, chatMessages, chatResetBtn (+11 more)

### Community 9 - "tools.py"
Cohesion: 0.16
Nodes (9): CheckOrderInput, execute_tool(), ProductDetailsInput, SearchProductsInput, StorePolicyInput, tool_check_order(), tool_get_product_details(), tool_query_store_policy() (+1 more)

### Community 10 - "Transcrição Oficial de Avaliação — Cenário 1: Busca de Catálogo com Restrição de Preço (Até R$ 1.000)"
Cohesion: 0.29
Nodes (6): **Assistente Virtual (Empório da Música):**, **Cliente:**, 🎯 Critérios de Aceitação Verificados, 💬 Diálogo Gravado, 📋 Metadados da Execução, Transcrição Oficial de Avaliação — Cenário 1: Busca de Catálogo com Restrição de Preço (Até R$ 1.000)

### Community 11 - "Transcrição Oficial de Avaliação — Cenário 2: Informações Institucionais, Endereço e Horário de Funcionamento"
Cohesion: 0.29
Nodes (6): **Assistente Virtual (Empório da Música):**, **Cliente:**, 🎯 Critérios de Aceitação Verificados, 💬 Diálogo Gravado, 📋 Metadados da Execução, Transcrição Oficial de Avaliação — Cenário 2: Informações Institucionais, Endereço e Horário de Funcionamento

### Community 12 - "Transcrição Oficial de Avaliação — Cenário 3: Consulta Específica de Preço, Estoque e Ficha Técnica (Takamine GD20)"
Cohesion: 0.29
Nodes (6): **Assistente Virtual (Empório da Música):**, **Cliente:**, 🎯 Critérios de Aceitação Verificados, 💬 Diálogo Gravado, 📋 Metadados da Execução, Transcrição Oficial de Avaliação — Cenário 3: Consulta Específica de Preço, Estoque e Ficha Técnica (Takamine GD20)

### Community 13 - "Transcrição Oficial de Avaliação — Cenário 4: Política de Trocas e Direito de Arrependimento (CDC)"
Cohesion: 0.29
Nodes (6): **Assistente Virtual (Empório da Música):**, **Cliente:**, 🎯 Critérios de Aceitação Verificados, 💬 Diálogo Gravado, 📋 Metadados da Execução, Transcrição Oficial de Avaliação — Cenário 4: Política de Trocas e Direito de Arrependimento (CDC)

### Community 14 - "Transcrição Oficial de Avaliação — Cenário 5: Guardrail de Escopo e Recusa Educada de Acessórios"
Cohesion: 0.29
Nodes (6): **Assistente Virtual (Empório da Música):**, **Cliente:**, 🎯 Critérios de Aceitação Verificados, 💬 Diálogo Gravado, 📋 Metadados da Execução, Transcrição Oficial de Avaliação — Cenário 5: Guardrail de Escopo e Recusa Educada de Acessórios

## Knowledge Gaps
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `4. Step-by-Step Implementation Phases` connect `Full Implementation Action Plan — Empório da Música AI Agent` to `llm.py`?**
  _High betweenness centrality (0.219) - this node is a cross-community bridge._
- **Should `rag.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05714285714285714 - nodes in this community are weakly interconnected._
- **Why does `Phase 4: Multi-Provider LLM Connector (`src/llm.py`) — *Skill: ponytail*` connect `llm.py` to `Full Implementation Action Plan — Empório da Música AI Agent`?**
  _High betweenness centrality (0.216) - this node is a cross-community bridge._
- **Should `agent.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08181818181818182 - nodes in this community are weakly interconnected._
- **Why does `Full Implementation Action Plan — Empório da Música AI Agent` connect `Full Implementation Action Plan — Empório da Música AI Agent` to `Empório da Música — AI Customer Service Agent`?**
  _High betweenness centrality (0.200) - this node is a cross-community bridge._
- **Should `llm.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09047619047619047 - nodes in this community are weakly interconnected._
- **Should `Full Implementation Action Plan — Empório da Música AI Agent` be split into smaller, more focused modules?**
  _Cohesion score 0.06451612903225806 - nodes in this community are weakly interconnected._