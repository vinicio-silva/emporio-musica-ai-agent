"""Generate high-fidelity, professional PDF documentation using headless Chrome/Edge.

Features:
- Responsive, clean HTML/CSS workflow cards (eliminating raw mermaid code and broken ASCII wrapping)
- Disables all browser headers/footers (no 'file:///' URLs at page bottoms)
- Clean, standard lists for Known Limitations & Future Roadmap
- Generates:
  1. docs/Vinicio Bernardes Silva - AI Engineer – Full-Stack para Aplicações com IA Generativa.pdf
  2. docs/README.pdf
  3. docs/Emporio_da_Musica_Technical_Documentation.pdf
"""

import base64
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
    margin-bottom: 0.3em;
    color: #0969da;
}
h2 {
    font-size: 14pt;
    font-weight: 600;
    border-bottom: 1px solid #d0d7de;
    padding-bottom: 0.25em;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    page-break-after: avoid;
    color: #1f2328;
}
h3 {
    font-size: 11.5pt;
    font-weight: 600;
    margin-top: 1.2em;
    margin-bottom: 0.4em;
    page-break-after: avoid;
    color: #24292f;
}
h4 {
    font-size: 10pt;
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

/* Elegant CSS Workflow Cards */
.workflow-box, .security-box, .methodology-box {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 12px;
    margin: 1.2em 0;
    page-break-inside: avoid;
}
.wf-node {
    background: #ffffff;
    border: 1.5px solid #0969da;
    border-radius: 6px;
    padding: 6px 12px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.wf-node strong {
    color: #0969da;
    font-size: 9.5pt;
}
.wf-sub {
    font-size: 8pt;
    color: #57606a;
    margin-top: 2px;
}
.wf-arrow {
    text-align: center;
    color: #0969da;
    font-size: 11pt;
    font-weight: bold;
    line-height: 1.1;
    margin: 4px 0;
}
.wf-grid {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    margin: 4px 0;
}
.wf-card {
    flex: 1;
    background: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 8px;
    font-size: 8pt;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.wf-card-title {
    font-weight: 700;
    color: #1f2328;
    margin-bottom: 3px;
    border-bottom: 1px solid #eaecef;
    padding-bottom: 2px;
}
.wf-card-body {
    color: #424a53;
    line-height: 1.35;
}
.sec-layer {
    display: flex;
    align-items: flex-start;
    padding: 6px 0;
    border-bottom: 1px solid #e2e8f0;
}
.sec-layer:last-child {
    border-bottom: none;
}
.sec-num {
    background: #0969da;
    color: white;
    font-size: 7.5pt;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    margin-right: 10px;
    white-space: nowrap;
}
.sec-content {
    font-size: 8.5pt;
    color: #1f2328;
    line-height: 1.4;
}

/* Candidate Metadata Card */
.candidate-header {
    background-color: #f6f8fa;
    border: 1px solid #d0d7de;
    border-left: 4px solid #0969da;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 1.2em 0;
    font-size: 9pt;
    line-height: 1.6;
}
.candidate-header strong {
    color: #1f2328;
}
.candidate-header a {
    color: #0969da;
    text-decoration: none;
    font-weight: 500;
}
.lead-node {
    background: #ffffff;
    border: 1.5px solid #1a7f37;
    border-radius: 6px;
    padding: 6px 12px;
    text-align: center;
    margin-bottom: 8px;
}
.lead-node strong {
    color: #1a7f37;
    font-size: 9.5pt;
}
.methodology-grid {
    display: flex;
    justify-content: space-between;
    gap: 8px;
}
.ui-screenshot-card {
    margin: 1.5em 0;
    text-align: center;
    page-break-inside: avoid;
}
.ui-screenshot-card img {
    max-width: 98%;
    height: auto;
    border-radius: 6px;
    border: 1px solid #d0d7de;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}
.ui-screenshot-card .caption {
    font-size: 8pt;
    color: #57606a;
    margin-top: 6px;
    font-style: italic;
}
"""

HTML_HIERARCHICAL = """
<div class="workflow-box">
  <div class="wf-node">
    <strong>1. Customer Input Message</strong>
  </div>
  <div class="wf-arrow">&#9660;</div>
  <div class="wf-node">
    <strong>2. Triage &amp; Guardrail Router (Llama 3 8B)</strong>
    <div class="wf-sub">Fast Intent Classification (&lt;300ms) &bull; Prompt Injection &amp; Abuse Filtering</div>
  </div>
  <div class="wf-arrow">&#9660;</div>
  <div class="wf-grid">
    <div class="wf-card">
      <div class="wf-card-title">Catalog &amp; Sales</div>
      <div class="wf-card-body">SPIN Selling Model, SQL Parameterized Query, Active Prompts</div>
    </div>
    <div class="wf-card">
      <div class="wf-card-title">Order Tracking</div>
      <div class="wf-card-body">Dual-Factor LGPD Authentication (Tracking + Email/Phone)</div>
    </div>
    <div class="wf-card">
      <div class="wf-card-title">Store Policy (RAG)</div>
      <div class="wf-card-body">Semantic BM25 Search on Store Manual (CDC, Returns, Hours)</div>
    </div>
    <div class="wf-card">
      <div class="wf-card-title">Scope Guardrail</div>
      <div class="wf-card-body">Polite Deflection for Non-Instrument Accessories (Section 7.1)</div>
    </div>
  </div>
  <div class="wf-arrow">&#9660;</div>
  <div class="wf-node">
    <strong>3. Consultative Synthesis &amp; Streamed Response (Llama 3 70B)</strong>
    <div class="wf-sub">Multi-Intent Unified Answer &bull; Empathetic Tone &bull; Real-time Token Streaming</div>
  </div>
</div>
"""

HTML_SECURITY = """
<div class="security-box">
  <div class="sec-layer">
    <span class="sec-num">Layer 1</span>
    <div class="sec-content">
      <strong>Context Isolation &amp; XML Tagging:</strong> User inputs wrapped in <code>&lt;user_message&gt;</code> delimiters to prevent prompt injection.
    </div>
  </div>
  <div class="sec-layer">
    <span class="sec-num">Layer 2</span>
    <div class="sec-content">
      <strong>System Prompt Immutability:</strong> Hardened guardrails refusing DAN mode, 'ignore previous instructions', and persona hijacking.
    </div>
  </div>
  <div class="sec-layer">
    <span class="sec-num">Layer 3</span>
    <div class="sec-content">
      <strong>Scope &amp; Product Boundaries:</strong> Strict adherence to Section 7.1 (instruments only, polite redirection of accessories).
    </div>
  </div>
  <div class="sec-layer">
    <span class="sec-num">Layer 4</span>
    <div class="sec-content">
      <strong>Parameterized SQL Queries (Anti-SQLi):</strong> Zero raw SQL generated by LLM; typed functions with parameterized <code>?</code> placeholders.
    </div>
  </div>
  <div class="sec-layer">
    <span class="sec-num">Layer 5</span>
    <div class="sec-content">
      <strong>PII Protection &amp; LGPD Compliance:</strong> Dual-factor authentication required for order status lookups (Law 13.709/2018).
    </div>
  </div>
</div>
"""

HTML_METHODOLOGY = """
<div class="methodology-box">
  <div class="lead-node">
    <strong>Lead Architect / Orchestrator (High Reasoning - Pro)</strong>
    <div class="wf-sub">API Contracts &bull; Schema Design &bull; Consultative Prompts &bull; Code Review &amp; Sign-Off</div>
  </div>
  <div class="methodology-grid">
    <div class="wf-card">
      <div class="wf-card-title">Data Worker (Fast)</div>
      <div class="wf-card-body">CSV Ingestion to SQLite, Relational Schemas, Indexes &amp; UTF-8 Cleansing</div>
    </div>
    <div class="wf-card">
      <div class="wf-card-title">UI Worker (Fast)</div>
      <div class="wf-card-body">Storefront HTML5/Tailwind, Floating Chat Widget &amp; Token Streaming Bridge</div>
    </div>
    <div class="wf-card">
      <div class="wf-card-title">QA Worker (Deterministic)</div>
      <div class="wf-card-body">16 Unit &amp; RAG Tests, Guardrail Verification &amp; 5 Assessment Scenarios Audits</div>
    </div>
  </div>
</div>
"""


CANDIDATE_HEADER_HTML = """
<div class="candidate-header">
  <strong>Candidato:</strong> Vinicio Bernardes Silva<br/>
  <strong>Cargo / Vaga:</strong> AI Engineer – Full-Stack para Aplicações com IA Generativa (Artefact Brazil)<br/>
  <strong>GitHub do Projeto:</strong> <a href="https://github.com/vinicio-silva/emporio-musica-ai-agent">https://github.com/vinicio-silva/emporio-musica-ai-agent</a><br/>
  <strong>LinkedIn:</strong> <a href="https://www.linkedin.com/in/vinicio-bernardes-silva/">https://www.linkedin.com/in/vinicio-bernardes-silva/</a>
</div>
"""


def transform_markdown_for_pdf(md_content: str, is_main: bool = True) -> str:
    """Transform markdown into clean HTML presentation for PDF."""
    # 1. Cleanly strip badges block
    md = re.sub(r"\[!\[.*?\]\(.*?\)\](?:\(.*?\))?\s*", "", md_content)

    # 2. Insert candidate metadata card right under the main title if it's the main document
    if is_main:
        md = re.sub(
            r"(### Technical Assessment: AI Engineer — Artefact Brazil\n)",
            r"\1\n" + CANDIDATE_HEADER_HTML + "\n",
            md,
        )

    # 2. Remove all raw mermaid code blocks
    md = re.sub(r"```mermaid[\s\S]*?```", "", md)

    # 3. Replace the 3 architecture diagram image references with clean CSS workflow cards
    md = re.sub(r"!\[.*?\]\([^\)]*hierarchical_architecture\.png\)", HTML_HIERARCHICAL.strip(), md)
    md = re.sub(r"!\[.*?\]\([^\)]*security_hardening_layers\.png\)", HTML_SECURITY.strip(), md)
    md = re.sub(r"!\[.*?\]\([^\)]*development_methodology\.png\)", HTML_METHODOLOGY.strip(), md)

    # 4. Embed storefront UI screenshot as base64 data URI
    ui_img_path = BASE_DIR / "docs" / "images" / "storefront_ui.png"
    if ui_img_path.exists():
        with open(ui_img_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")
        ui_html = f'<div class="ui-screenshot-card"><img src="data:image/png;base64,{b64_img}" alt="Empório da Música Storefront &amp; Chat Widget" /><p class="caption">Figura: Interface Web da Empório da Música com Catálogo Dinâmico e Widget Flutuante de Atendimento Conversacional via Streaming SSE.</p></div>'
        md = re.sub(r"!\[.*?\]\([^\)]*storefront_ui\.png\)", ui_html, md)

    # 5. Embed 5 official scenario screenshots as base64 data URIs
    for i in range(1, 6):
        scen_img_path = BASE_DIR / "docs" / "images" / f"scenario_{i}_ui.png"
        if scen_img_path.exists():
            with open(scen_img_path, "rb") as f:
                b64_scen = base64.b64encode(f.read()).decode("utf-8")
            scen_html = f'<div class="ui-screenshot-card scenario-card"><img src="data:image/png;base64,{b64_scen}" alt="Cenário {i} UI Execution" /><p class="caption">Evidência Visual de Execução — Cenário {i} no Widget de Chat da Loja Virtual.</p></div>'
            md = re.sub(rf"!\[.*?\]\([^\)]*scenario_{i}_ui\.png\)", scen_html, md)

    # 6. Remove any other lingering image references
    md = re.sub(r"!\[.*?\]\(.*?\)", "", md)

    # 5. Clean up multiple empty lines
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
        "--no-pdf-header-footer",
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
            parts.append("<div class='page-break'></div>\n\n# Appendix A: Detailed Architectural Specification\n\n" + transform_markdown_for_pdf(f.read(), is_main=False))

    scenario_files = sorted(scenarios_dir.glob("scenario_*.md"))
    if scenario_files:
        scen_combined = ["<div class='page-break'></div>\n\n# Appendix B: Official Artefact Evaluation Scenarios Audit\n\nComprehensive audit transcripts and criteria validation for each of the 5 official technical assessment scenarios:\n"]
        for sf in scenario_files:
            with open(sf, "r", encoding="utf-8") as f:
                scen_combined.append(f"<div class='page-break'></div>\n\n{transform_markdown_for_pdf(f.read(), is_main=False)}")
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
    print("\nAll PDFs successfully generated with CSS cards and zero headers/footers!")
