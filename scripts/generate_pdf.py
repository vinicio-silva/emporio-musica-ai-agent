"""Generate high-fidelity, professional PDF documentation using headless Chrome/Edge.

Embeds diagrams as Base64 images and applies GitHub-grade typography and CSS.
Generates:
1. docs/README.pdf (Standalone project README)
2. docs/Emporio_da_Musica_Technical_Documentation.pdf (Full Master Dossier: README + Architecture + 5 Scenarios)
"""

import base64
import os
import re
import subprocess
import sys
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

print(f"Using Browser for PDF conversion: {BROWSER_PATH}")

CSS_STYLING = """
@page {
    size: A4;
    margin: 20mm 15mm 20mm 15mm;
}
@media print {
    body {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
}
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.55;
    color: #1f2328;
    background-color: #ffffff;
    margin: 0;
    padding: 0;
}
h1 {
    font-size: 22pt;
    font-weight: 700;
    border-bottom: 2px solid #d0d7de;
    padding-bottom: 0.3em;
    margin-top: 0;
    margin-bottom: 0.5em;
    color: #0969da;
}
h2 {
    font-size: 16pt;
    font-weight: 600;
    border-bottom: 1px solid #d0d7de;
    padding-bottom: 0.3em;
    margin-top: 1.8em;
    margin-bottom: 0.6em;
    page-break-after: avoid;
    color: #1f2328;
}
h3 {
    font-size: 12.5pt;
    font-weight: 600;
    margin-top: 1.4em;
    margin-bottom: 0.4em;
    page-break-after: avoid;
    color: #24292f;
}
h4 {
    font-size: 11pt;
    font-weight: 600;
    margin-top: 1em;
    page-break-after: avoid;
}
p {
    margin-top: 0;
    margin-bottom: 0.8em;
}
ul, ol {
    margin-top: 0;
    margin-bottom: 0.8em;
    padding-left: 1.8em;
}
li {
    margin-bottom: 0.3em;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 1.2em 0;
    font-size: 9pt;
    page-break-inside: avoid;
}
table th, table td {
    border: 1px solid #d0d7de;
    padding: 7px 10px;
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
    font-size: 8.5pt;
    line-height: 1.45;
    overflow-x: auto;
    page-break-inside: avoid;
    margin: 0.8em 0;
}
code {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
    font-size: 9pt;
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
img {
    max-width: 95%;
    height: auto;
    display: block;
    margin: 1.2em auto;
    border-radius: 6px;
    border: 1px solid #d0d7de;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    page-break-inside: avoid;
}
hr {
    border: 0;
    border-top: 1px solid #d0d7de;
    margin: 1.8em 0;
}
.page-break {
    page-break-before: always;
}
.badge-bar {
    margin-bottom: 1em;
}
.badge-bar img {
    display: inline-block;
    margin: 2px 4px 2px 0;
    border: none;
    box-shadow: none;
}
.header-box {
    background: linear-gradient(135deg, #0969da 0%, #1a7f37 100%);
    color: white;
    padding: 24px;
    border-radius: 8px;
    margin-bottom: 2em;
}
.header-box h1 {
    color: white;
    border-bottom: 1px solid rgba(255,255,255,0.3);
    margin: 0 0 10px 0;
}
.header-box p {
    margin: 4px 0;
    font-size: 11pt;
    opacity: 0.95;
}
"""


def embed_images_as_base64(md_content: str, base_path: Path) -> str:
    """Replace image references with inline base64 data URIs."""
    def replacer(match):
        alt = match.group(1)
        rel_path = match.group(2)
        full_path = (base_path / rel_path).resolve()
        if full_path.exists() and full_path.is_file():
            ext = full_path.suffix.lstrip(".").lower()
            mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"
            with open(full_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            return f"![{alt}](data:{mime};base64,{b64})"
        return match.group(0)

    return re.sub(r"!\[(.*?)\]\((.*?)\)", replacer, md_content)


def convert_html_to_pdf(html_content: str, output_pdf_path: Path) -> None:
    """Render HTML content to PDF using headless Chrome/Edge."""
    temp_html = output_pdf_path.with_suffix(".tmp.html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    file_url = temp_html.as_uri()
    cmd = [
        BROWSER_PATH,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--run-all-compositor-stages-before-draw",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={str(output_pdf_path)}",
        file_url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if temp_html.exists():
        temp_html.unlink()

    if result.returncode != 0:
        raise RuntimeError(f"Browser PDF generation failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")

    size_kb = output_pdf_path.stat().st_size / 1024
    print(f"Generated PDF: {output_pdf_path} ({size_kb:.1f} KB)")


def generate_readme_pdf() -> Path:
    """Generate standalone docs/README.pdf from README.md."""
    readme_path = BASE_DIR / "README.md"
    with open(readme_path, "r", encoding="utf-8") as f:
        md = f.read()

    md_embedded = embed_images_as_base64(md, BASE_DIR)
    body_html = markdown.markdown(md_embedded, extensions=["extra", "toc"])

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

    out_pdf = DOCS_DIR / "README.pdf"
    convert_html_to_pdf(full_html, out_pdf)
    return out_pdf


def generate_master_dossier_pdf() -> Path:
    """Generate master documentation PDF: README + Architecture + 5 Scenarios Audits."""
    readme_path = BASE_DIR / "README.md"
    arch_path = DOCS_DIR / "architecture.md"
    scenarios_dir = DOCS_DIR / "conversations"

    parts = []

    # 1. README
    with open(readme_path, "r", encoding="utf-8") as f:
        parts.append(embed_images_as_base64(f.read(), BASE_DIR))

    # 2. Architecture Specification
    if arch_path.exists():
        with open(arch_path, "r", encoding="utf-8") as f:
            parts.append("<div class='page-break'></div>\n\n# Appendix A: Detailed Architectural Specification\n\n" + embed_images_as_base64(f.read(), DOCS_DIR))

    # 3. 5 Official Scenarios
    scenario_files = sorted(scenarios_dir.glob("scenario_*.md"))
    if scenario_files:
        scen_combined = ["<div class='page-break'></div>\n\n# Appendix B: Official Artefact Evaluation Scenarios Audit\n\nComprehensive audit transcripts and criteria validation for each of the 5 official technical assessment scenarios:\n"]
        for sf in scenario_files:
            with open(sf, "r", encoding="utf-8") as f:
                scen_combined.append(f"<div class='page-break'></div>\n\n{f.read()}")
        parts.append("\n\n".join(scen_combined))

    full_md = "\n\n<div class='page-break'></div>\n\n".join(parts)
    body_html = markdown.markdown(full_md, extensions=["extra", "toc"])

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Empório da Música — Master Technical Documentation & Evaluation Dossier</title>
<style>{CSS_STYLING}</style>
</head>
<body>
{body_html}
</body>
</html>"""

    out_pdf = DOCS_DIR / "Emporio_da_Musica_Technical_Documentation.pdf"
    convert_html_to_pdf(full_html, out_pdf)
    return out_pdf


if __name__ == "__main__":
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating Standalone README.pdf...")
    p1 = generate_readme_pdf()
    print("Generating Master Technical Documentation Dossier PDF...")
    p2 = generate_master_dossier_pdf()
    print("\nPDF generation finished successfully!")
