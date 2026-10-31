"""Generate high-fidelity, professional PDF documentation using headless Chrome/Edge.

Features:
- Pure text-based architectural workflows and ASCII diagrams (zero broken images or raw mermaid code blocks)
- Disables all browser headers/footers (eliminating 'file:///' URLs at page bottoms)
- Clean, standard lists for Known Limitations & Future Roadmap
- Generates:
  1. docs/Vinicio Bernardes Silva - AI Engineer – Full-Stack para Aplicações com IA Generativa.pdf
  2. docs/README.pdf
  3. docs/Emporio_da_Musica_Technical_Documentation.pdf
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import markdown

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"

# Locate Chrome or Edge
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

BROWSER_PATH = None
for p in CHROME_CANDIDATES:
    if os.path.exists(p):
        BROWSER_PATH = p
        break

if not BROWSER_PATH:
    raise RuntimeError("Neither Chrome nor Edge executable was found for PDF generation.")

CSS_STYLING = """
@page {
    size: A4;
    margin: 18mm 15mm 18mm 15mm;
}
@media print {
    body {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
}
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.5;
    color: #1f2328;
    background-color: #ffffff;
    margin: 0;
    padding: 0;
}
h1 {
    font-size: 20pt;
    font-weight: 700;
    border-bottom: 2px solid #0969da;
    padding-bottom: 0.3em;
    margin-top: 0;
    margin-bottom: 0.4em;
    color: #0969da;
}
h2 {
    font-size: 14.5pt;
    font-weight: 600;
    border-bottom: 1px solid #d0d7de;
    padding-bottom: 0.25em;
    margin-top: 1.6em;
    margin-bottom: 0.5em;
    page-break-after: avoid;
    color: #1f2328;
}
h3 {
    font-size: 12pt;
    font-weight: 600;
    margin-top: 1.2em;
    margin-bottom: 0.4em;
    page-break-after: avoid;
    color: #24292f;
}
h4 {
    font-size: 10.5pt;
    font-weight: 600;
    margin-top: 1em;
    page-break-after: avoid;
}
p {
    margin-top: 0;
    margin-bottom: 0.7em;
}
ol, ul {
    margin-top: 0.3em;
    margin-bottom: 0.8em;
    padding-left: 2em;
}
ol li, ul li {
    margin-bottom: 0.4em;
    line-height: 1.45;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 1.2em 0;
    font-size: 8.5pt;
    page-break-inside: avoid;
}
table th, table td {
    border: 1px solid #d0d7de;
    padding: 6px 9px;
    text-align: left;
}
table th {
    background-color: #f6f8fa;
    font-weight: 600;
    color: #1f2328;
}
table tr:nth-child(even) {
    background-color: #fcfcfc;
}
pre {
    background-color: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 10px 12px;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
    font-size: 8pt;
    line-height: 1.35;
    overflow-x: auto;
    page-break-inside: avoid;
    margin: 0.8em 0;
}
code {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
    font-size: 8.5pt;
    background-color: rgba(175, 184, 193, 0.2);
    padding: 0.15em 0.35em;
    border-radius: 4px;
}
pre code {
    background-color: transparent;
    padding: 0;
    border-radius: 0;
}
blockquote {
    margin: 1em 0;
    padding: 0.6em 1em;
    color: #57606a;
    border-left: 4px solid #0969da;
    background-color: #f6f8fa;
    border-radius: 0 6px 6px 0;
}
hr {
    border: 0;
    border-top: 1px solid #d0d7de;
    margin: 1.6em 0;
}
.page-break {
    page-break-before: always;
}
"""

DIAGRAM_HIERARCHICAL = """
```text
┌────────────────────────────────────────────────────────────────────────┐
│                        CUSTOMER INPUT MESSAGE                          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               TRIAGE & GUARDRAIL ROUTER (Llama 3 8B)                   │
│   • Fast Intent Classification (<300ms) • Anti-Jailbreak Filter        │
└───────┬───────────────────┬───────────────────┬───────────────────┬────┘
        │                   │                   │                   │
        ▼                   ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ CATALOG &    │    │ ORDER        │    │ STORE POLICY │    │ SCOPE &      │
│ SALES WORKER │    │ TRACKING     │    │ WORKER (RAG) │    │ ACCESSORIES  │
│ (SPIN Model) │    │ (Dual Auth)  │    │ (CDC & Hours)│    │ (Deflection) │
└───────┬──────┘    └───────┬──────┘    └───────┬──────┘    └───────┬──────┘
        │                   │                   │                   │
        └───────────────────┴─────────┬─────────┴───────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────┐
│             CONSULTATIVE SYNTHESIS & STREAMED RESPONSE                 │
│         • Empathy & Clarity • Transparent Pricing • LGPD Compliant     │
└────────────────────────────────────────────────────────────────────────┘
```
"""

DIAGRAM_SECURITY = """
```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                  5-LAYER DEFENSE-IN-DEPTH ARCHITECTURE                       │
├──────────────────────────────────────────────────────────────────────────────┤
│ Layer 1: Context Isolation & XML Tagging                                     │
│          User messages strictly enclosed within <user_message> boundaries.   │
├──────────────────────────────────────────────────────────────────────────────┤
│ Layer 2: System Prompt Immutability & Jailbreak Refusal                      │
│          Immunity against prompt injections, DAN mode, and persona hijacking.│
├──────────────────────────────────────────────────────────────────────────────┤
│ Layer 3: Scope Guardrails & Business Deflection                              │
│          Strict instrument focus (Section 7.1); polite deflection of parts.  │
├──────────────────────────────────────────────────────────────────────────────┤
│ Layer 4: Parameterized Relational Queries (Anti-SQLi)                         │
│          Zero raw SQL generation by LLM; typed functions with '?' parameters.│
├──────────────────────────────────────────────────────────────────────────────┤
│ Layer 5: PII Protection & LGPD Compliance (Law 13.709/2018)                  │
│          Dual-factor authentication required for order status lookups.       │
└──────────────────────────────────────────────────────────────────────────────┘
```
"""

DIAGRAM_METHODOLOGY = """
```text
┌──────────────────────────────────────────────────────────────────────────────┐
│              ORCHESTRATOR-WORKERS MULTI-AGENT DEVELOPMENT WORKFLOW           │
├──────────────────────────────────────────────────────────────────────────────┤
│  Lead Architect / Orchestrator (High Reasoning - Pro)                        │
│  • API Contracts, Schema Design, Consultative Prompts & Code Audits          │
│       │                                                                      │
│       ├──► Data Worker (Fast Execution)                                      │
│       │    • CSV Ingestion, SQLite Schema, Indexes & UTF-8 Cleansing         │
│       │                                                                      │
│       ├──► UI Worker (Fast Execution)                                        │
│       │    • Storefront Catalog HTML5, CSS Styling & Streaming Chat Widget   │
│       │                                                                      │
│       └──► QA Worker (Deterministic Validation)                              │
│            • Unit Tests, RAG Retrieval Tests, Guardrail & Scenario Audits    │
└──────────────────────────────────────────────────────────────────────────────┘
```
"""


def transform_markdown_for_pdf(md_content: str) -> str:
    """Transform markdown to pure text diagrams, removing raw mermaid blocks and image references."""
    # 1. Remove all raw mermaid code blocks
    md = re.sub(r"```mermaid[\s\S]*?```", "", md_content)

    # 2. Replace image references with formatted text diagrams
    md = re.sub(r"!\[.*?Hierarchical.*?\]\(.*?\)", DIAGRAM_HIERARCHICAL.strip(), md)
    md = re.sub(r"!\[.*?Security.*?\]\(.*?\)", DIAGRAM_SECURITY.strip(), md)
    md = re.sub(r"!\[.*?Orchestrator.*?\]\(.*?\)", DIAGRAM_METHODOLOGY.strip(), md)

    # 3. Remove badges bar and any remaining image tags for clean typography
    md = re.sub(r"\[!\[.*?\]\(.*?\)\]\(.*?\)", "", md)
    md = re.sub(r"!\[.*?\]\(.*?\)", "", md)

    # 4. Clean up multiple empty lines
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md


def convert_html_to_pdf(html_content: str, output_pdf_path: Path) -> None:
    """Render HTML content to PDF using headless Chrome/Edge with zero header/footer."""
    temp_html = output_pdf_path.with_suffix(".tmp.html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    file_url = temp_html.as_uri()
    cmd = [
        BROWSER_PATH,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",  # Strictly disables file:/// URL and page headers/footers
        f"--print-to-pdf={str(output_pdf_path)}",
        file_url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if temp_html.exists():
        temp_html.unlink()

    if result.returncode != 0:
        raise RuntimeError(f"Browser PDF generation failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")

    size_kb = output_pdf_path.stat().st_size / 1024
    print(f"Generated PDF: {output_pdf_path.name} ({size_kb:.1f} KB)")


def generate_all_pdfs() -> None:
    """Compile formatted markdown into final PDFs."""
    readme_path = BASE_DIR / "README.md"
    with open(readme_path, "r", encoding="utf-8") as f:
        raw_readme = f.read()

    cleaned_readme = transform_markdown_for_pdf(raw_readme)
    body_html = markdown.markdown(cleaned_readme, extensions=["extra", "toc"])

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Empório da Música — Technical Documentation</title>
<style>{CSS_STYLING}</style>
</head>
<body>
{body_html}
</body>
</html>"""

    # 1. Standard docs/README.pdf
    readme_pdf = DOCS_DIR / "README.pdf"
    convert_html_to_pdf(full_html, readme_pdf)

    # 2. Personalized Candidate named PDF
    candidate_pdf_name = "Vinicio Bernardes Silva - AI Engineer – Full-Stack para Aplicações com IA Generativa.pdf"
    candidate_pdf = DOCS_DIR / candidate_pdf_name
    shutil.copyfile(readme_pdf, candidate_pdf)
    print(f"Copied to personalized candidate PDF: {candidate_pdf.name}")

    # 3. Master Technical Dossier
    arch_path = DOCS_DIR / "architecture.md"
    scenarios_dir = DOCS_DIR / "conversations"

    parts = [cleaned_readme]
    if arch_path.exists():
        with open(arch_path, "r", encoding="utf-8") as f:
            parts.append("<div class='page-break'></div>\n\n# Appendix A: Detailed Architectural Specification\n\n" + transform_markdown_for_pdf(f.read()))

    scenario_files = sorted(scenarios_dir.glob("scenario_*.md"))
    if scenario_files:
        scen_combined = ["<div class='page-break'></div>\n\n# Appendix B: Official Artefact Evaluation Scenarios Audit\n\nComprehensive audit transcripts and criteria validation for each of the 5 official technical assessment scenarios:\n"]
        for sf in scenario_files:
            with open(sf, "r", encoding="utf-8") as f:
                scen_combined.append(f"<div class='page-break'></div>\n\n{transform_markdown_for_pdf(f.read())}")
        parts.append("\n\n".join(scen_combined))

    master_md = "\n\n<div class='page-break'></div>\n\n".join(parts)
    master_body = markdown.markdown(master_md, extensions=["extra", "toc"])
    master_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Empório da Música — Master Technical Documentation & Evaluation Dossier</title>
<style>{CSS_STYLING}</style>
</head>
<body>
{master_body}
</body>
</html>"""

    master_pdf = DOCS_DIR / "Emporio_da_Musica_Technical_Documentation.pdf"
    convert_html_to_pdf(master_html, master_pdf)


if __name__ == "__main__":
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    generate_all_pdfs()
    print("\nAll PDFs successfully generated with pure text formatting and zero headers/footers!")
