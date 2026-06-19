# 📄 Manuscript Writing Agent

> **An AI-powered agentic pipeline for drafting peer-reviewed journal manuscripts** — from raw data to submission-ready documents, end to end.

![Demo](https://github.com/wangqian2149185/sci-writer/blob/main/demo/hero.gif?raw=true)

---

## 🚀 Why Use This?

Many researchers are highly skilled at asking scientific questions and solving technical problems. But writing those ideas clearly is often a separate challenge. Manuscripts and grant proposals can take a large amount of time, especially when the goal is to communicate complex results with precision, structure, and evidence.

For many PIs, writing can become a major bottleneck. Time spent repeatedly drafting and revising text is time taken away from scientific thinking, mentoring, experimental design, and project direction.

Sci-Writer is built to reduce that bottleneck. It helps researchers turn experimental notes, figures, and literature context into structured drafts more efficiently. It is not meant to replace scientific judgment. It is meant to help authors express their ideas faster, more clearly, and with better control over the final scientific message.

Three core reliability principles:

- **Citation grounding** — reference canonicalization and audit tables reduce duplicate or ambiguous sources; in the current regression check, repeated references went from **5/32** to **0/32**.
- **Entity grounding** — controlled vocabulary and near-miss audits flag high-risk scientific names; in the current regression check, protein-name errors went from **3/41** to **0/41**.
- **Stage checkpoints** — the pipeline pauses at key checkpoints and saves progress to `output/state.json`, so interrupted sessions can usually be resumed from the latest saved state.

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

## ✨ Three Core Reliability Measures

**🛡️ Citation Grounding**
References are canonicalized with DOI, PMID, arXiv ID, or normalized-title hashes before bibliography generation. In the current regression check, duplicate reference entries decreased from **5 out of 32** to **0 out of 32**.

**🧭 Entity Grounding**
High-risk scientific terms can be constrained through `input/entity_registry.csv`, including canonical names, allowed aliases, and forbidden/confusing names. In the current regression check, protein-name errors decreased from **3 out of 41** to **0 out of 41**.

**🔒 Human Checkpoints**
The workflow pauses at key stages for user confirmation and writes intermediate state to `output/state.json`. This reduces error propagation by letting users inspect captions, literature choices, entity audits, and references before later sections reuse them.

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
