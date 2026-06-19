# 📄 Manuscript Writing Agent

> **An AI-powered agentic pipeline for drafting peer-reviewed journal manuscripts** — from raw data to submission-ready documents, end to end.

![Demo](https://github.com/wangqian2149185/sci-writer/blob/main/demo/hero.gif?raw=true)

---

## 🚀 Why Use This?

**Academic writing is one of the most time-consuming parts of research.** Most scientists spend more time writing than experimenting. This project lets AI handle the heavy lifting of drafting, so you can stay focused on the science itself.

Three core principles:

- **No hallucination** — every sentence is grounded in your uploaded files or verified web search results. Nothing is invented.
- **Stage gating** — the pipeline pauses at every key checkpoint and waits for your explicit `confirm` before moving on. You stay in control.
- **Resumable** — progress is auto-saved to `output/state.json`. Close the app, come back later, and pick up exactly where you left off.

---

## ⚡ Quick Start

```bash
# 1. Navigate to the project folder
cd sci-writer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Load environment variables (API keys, etc.)
source .env

# 4. Launch the app
python3 app.py
```

Then open **http://localhost:7860** in your browser.

---

## 📁 Folder Structure

```
sci-writer/
├── app.py                    # 🎯 Main entry point — run this
│
├── stages/                   # 📋 One module per pipeline stage
│   ├── stage0_verify.py      # File verification & figure↔caption matching
│   ├── stage1_captions.py    # Figure captions (Claude Vision)
│   ├── stage2_results.py     # Results section
│   ├── stage3_intro.py       # Introduction + web search
│   ├── stage4_discussion.py  # Discussion
│   ├── stage5_methods.py     # Materials & Methods
│   ├── stage6_abstract.py    # Abstract
│   ├── stage7_titles.py      # Title suggestions
│   ├── stage8_tone.py        # Tone rewriting from templates
│   ├── stage9_authors.py     # Authorship & affiliations
│   └── stage10_journal.py    # Journal formatting
│
├── utils/                    # 🔧 Shared utilities
│   ├── claude_client.py      # Anthropic API wrapper
│   ├── doc_builder.py        # python-docx helpers
│   ├── entity_registry.py    # Controlled vocabulary & near-miss entity audit
│   ├── figure_checker.py     # Pillow image validation
│   ├── reference_manager.py  # Reference canonicalization & deduplication
│   └── state_manager.py      # state.json persistence
│
├── input/                    # 📥 Drop your files here
│   ├── figures/              # Figure image files
│   ├── captions/             # Caption .txt files (same base name as figures)
│   ├── results/              # Results notes (.txt)
│   ├── methods/              # Methods notes (.txt)
│   ├── tone_templates/       # Optional: up to 5 .pdf/.docx papers for tone analysis
│   └── entity_registry.csv   # Optional: controlled vocabulary for proteins, genes, methods, references
│
└── output/                   # 📤 All generated files land here (auto-created)
    ├── manuscript_draft.docx
    ├── manuscript_toned.docx
    ├── manuscript_final.docx
    ├── figures_captions.docx
    ├── references.md
    ├── canonical_references.json
    ├── canonical_references.md
    ├── uncertain_references.md
    ├── entity_audit_*.md
    ├── tone.md
    └── state.json
```

---

## 🔬 Pipeline Stages — 11 Steps, Fully Automated

| Stage | Name | What It Does |
|:-----:|------|--------------|
| **0** | Startup & Verification | File integrity check, figure↔caption matching, size warnings |
| **1** | Figure Captions | Claude Vision generates journal-style captions from your images |
| **2** | Results | Drafts the Results section from your results/ notes |
| **3** | Introduction | Web search → bullet list → user selects → 800–2,000 word Introduction with 30+ references |
| **4** | Discussion | Connects results with literature; optional merge with Results |
| **5** | Materials & Methods | Drafts from methods/ files with built-in sanity checks |
| **6** | Abstract | Generates a structured 150–300 word abstract |
| **7** | Titles | Produces 5–8 title options; you choose the final one |
| **8** | Tone Rewriting | Analyzes your tone_templates/ → rewrites the manuscript in your voice |
| **9** | Authorship | Formats authors, affiliations, and corresponding author block |
| **10** | Journal Formatting | Looks up journal style → reformats references → produces final .docx |

---

## ✨ Three Core Guarantees

**🛡️ No Hallucination**
All content is sourced exclusively from your uploaded files or web-search-verified literature. The AI will never fabricate data, results, or citations.

**🔒 Stage Gating**
After each stage, the pipeline pauses and waits for your `confirm` before proceeding. You can review and revise at every step — nothing runs away from you.

**♻️ Resumable Sessions**
All progress is saved in real time to `output/state.json`. If the session is interrupted, simply re-run `python3 app.py` and continue from where you left off.

---

## 📦 Dependencies

```
anthropic      # Claude API
python-docx    # Word document generation
pillow         # Image validation
gradio         # Web UI
pymupdf        # PDF processing
tiktoken       # Token counting
```

Install everything at once:

```bash
pip install -r requirements.txt
```

---

## 💡 Tips for Best Results

- **Match figure and caption filenames** — `figure1.png` pairs automatically with `figure1.txt`
- **The richer your notes, the better the output** — detailed results and methods files lead to higher-quality drafts
- **Use an entity registry for high-risk terms** — copy `input/entity_registry.example.csv` to `input/entity_registry.csv`, then list canonical protein/gene/method names, allowed aliases, and forbidden/confusing names
- **Tone templates are optional but powerful** — drop 1–5 of your published papers into `tone_templates/` to write in your own voice
- **Introduction is fully transparent** — the pipeline shows you the retrieved literature bullets first, lets you confirm, then expands into the full section
- **References are canonicalized** — DOI/PMID/arXiv/title hashes are used to deduplicate sources before the final bibliography is generated

---

## 🤝 Contributing & Feedback

Issues and pull requests are welcome! If this project saves you time on your next manuscript, consider giving it a ⭐ Star.
