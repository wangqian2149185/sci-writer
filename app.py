"""
Manuscript Writing Agent — Gradio Web UI
Sequential 10-stage pipeline for peer-reviewed journal manuscript drafting.
"""

from pathlib import Path
import gradio as gr

from utils.state_manager import load_state, save_state, mark_stage_complete

ROOT = Path(__file__).parent


def _chat(history: list, user: str, bot: str) -> list:
    """Append a user+assistant message pair in Gradio 6 messages format."""
    if user:
        history.append({"role": "user", "content": user})
    history.append({"role": "assistant", "content": bot})
    return history


def _chat_update(history: list, bot: str) -> list:
    """Update the last assistant message in place (for ⏳ → result replacement)."""
    history[-1] = {"role": "assistant", "content": bot}
    return history


def _chat_pending(history: list, user: str, placeholder: str) -> list:
    """Append user + a placeholder assistant message (updated later via _chat_update)."""
    if user:
        history.append({"role": "user", "content": user})
    history.append({"role": "assistant", "content": placeholder})
    return history


# ──────────────────────────────────────────────
# Stage dispatcher
# ──────────────────────────────────────────────

def process_message(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    """Route user input to the correct stage handler."""
    user_input = user_input.strip()
    stage = state.get("current_stage", 0)

    if stage == 0:
        return handle_stage0(user_input, history, state)
    if stage == 1:
        return handle_stage1(user_input, history, state)
    if stage == 2:
        return handle_stage2(user_input, history, state)
    if stage == 3 and not state.get("_intro_bullets_generated"):
        return handle_stage3_keywords(user_input, history, state)
    if stage == 3 and state.get("_intro_bullets_generated") and not state.get("_intro_written"):
        return handle_stage3_select(user_input, history, state)
    if stage == 3 and state.get("_intro_written"):
        return handle_stage3_confirm(user_input, history, state)
    if stage == 4:
        return handle_stage4(user_input, history, state)
    if stage == 5:
        return handle_stage5(user_input, history, state)
    if stage == 6:
        return handle_stage6(user_input, history, state)
    if stage == 7:
        return handle_stage7(user_input, history, state)
    if stage == 8:
        return handle_stage8(user_input, history, state)
    if stage == 9:
        return handle_stage9(user_input, history, state)
    if stage == 10:
        return handle_stage10(user_input, history, state)

    reply = (
        "✅ All stages complete! Your manuscript files are in the `output/` folder.\n\n"
        "- `output/manuscript_final.docx` — final formatted manuscript\n"
        "- `output/manuscript_toned.docx` — tone-rewritten version\n"
        "- `output/figures_captions.docx` — official figure captions\n"
        "- `output/references.md` — full reference list"
    )
    _chat(history, user_input, reply)
    return "", history, state


# ─── Stage 0 ─────────────────────────────────

def handle_stage0(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    if user_input.lower() in ("/verify_files", "verify_files", "/verify"):
        from stages.stage0_verify import run_verification, format_verification_report
        errors, warnings, ok = run_verification()
        report = format_verification_report(errors, warnings, ok)

        if ok:
            state["_stage0_verified"] = True
            state["_stage0_warnings"] = warnings
            save_state(state)

        _chat(history, user_input, report)
        return "", history, state

    if state.get("_stage0_verified") and user_input.lower() in ("confirm", "yes", "y"):
        state = mark_stage_complete(state, 0)
        reply = (
            "✅ Files verified. Moving to **Stage 1: Figure Captions**.\n\n"
            "I will now inspect each figure and generate professional captions.\n"
            "Type `start` to begin, or specify figure order (e.g., `fig1, fig3, fig2`)."
        )
        _chat(history, user_input, reply)
        return "", history, state

    reply = (
        "## 👋 Welcome to the Manuscript Writing Agent\n\n"
        "I will guide you through drafting a complete peer-reviewed manuscript.\n\n"
        "**Expected folder structure:**\n"
        "```\n"
        "input/\n"
        "  figures/       ← figure image files (.png, .jpg, .tif, .svg, ...)\n"
        "  captions/      ← .txt caption files (same base name as each figure)\n"
        "  results/       ← .txt files describing your results/significance\n"
        "  methods/       ← .txt files with materials & methods content\n"
        "  tone_templates/← up to 5 .pdf or .docx papers for tone analysis (optional)\n"
        "```\n\n"
        "**Drop all your files into the correct folders, then type `/verify_files`.**"
    )
    _chat(history, user_input or "start", reply)
    return "", history, state


# ─── Stage 1 ─────────────────────────────────

def handle_stage1(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    if not state.get("_captions_generated"):
        figure_order = None
        if user_input.lower() not in ("start", "yes", "y", ""):
            figure_order = [s.strip() for s in user_input.replace(",", " ").split()]

        _chat_pending(history, user_input, "⏳ Generating figure captions (this may take a moment)...")
        try:
            from stages.stage1_captions import generate_captions
            captions, display = generate_captions(figure_order)
            state["captions"] = captions
            state["sections"]["captions"] = display
            state["_captions_generated"] = True
            save_state(state)
            display += "\n\nPlease review. Type `confirm` to proceed, or paste corrections."
            _chat_update(history, display)
        except Exception as e:
            _chat_update(history, f"❌ Error generating captions: {e}")
        return "", history, state

    if user_input.lower() in ("confirm", "yes", "y"):
        state = mark_stage_complete(state, 1)
        reply = (
            "✅ Captions confirmed. Moving to **Stage 2: Results Section**.\n\n"
            "I will draft the Results section from your `input/results/` files.\n"
            "Type `start` to begin."
        )
        _chat(history, user_input, reply)
        return "", history, state

    _chat_pending(history, user_input, "⏳ Applying corrections and regenerating captions...")
    try:
        from stages.stage1_captions import generate_captions
        captions, display = generate_captions()
        state["captions"] = captions
        state["sections"]["captions"] = display
        save_state(state)
        display += "\n\nType `confirm` to proceed."
        _chat_update(history, display)
    except Exception as e:
        _chat_update(history, f"❌ Error: {e}")
    return "", history, state


# ─── Stage 2 ─────────────────────────────────

def handle_stage2(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    if not state.get("_results_generated"):
        _chat_pending(history, user_input, "⏳ Drafting Results section...")
        try:
            from stages.stage2_results import generate_results
            captions = state.get("captions", [])
            result = generate_results(captions)
            state["sections"]["results"] = result
            state["_results_generated"] = True
            save_state(state)
            display = f"## Results Section (Stage 2)\n\n{result}\n\nType `confirm` to proceed or paste corrections."
            _chat_update(history, display)
        except Exception as e:
            _chat_update(history, f"❌ Error: {e}")
        return "", history, state

    if user_input.lower() in ("confirm", "yes", "y"):
        state = mark_stage_complete(state, 2)
        reply = (
            "✅ Results confirmed. Moving to **Stage 3: Introduction** (with literature research).\n\n"
            "Please provide keywords, field names, or any preferences for the literature search.\n"
            "Example: `CRISPR gene editing, DNA repair mechanisms, cancer therapy`"
        )
        _chat(history, user_input, reply)
        return "", history, state

    state["sections"]["results"] += f"\n\n[User correction: {user_input}]"
    state["_results_generated"] = False
    save_state(state)
    return handle_stage2("start", history, state)


# ─── Stage 3a — keywords ─────────────────────

def handle_stage3_keywords(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    if not user_input or user_input.lower() in ("start",):
        _chat(history, user_input, "Please provide keywords for the literature search.")
        return "", history, state

    state["_intro_keywords"] = user_input
    save_state(state)
    _chat_pending(history, user_input, "⏳ Searching literature (web search enabled — this may take 1-2 minutes)...")
    try:
        from stages.stage3_intro import research_intro
        bullets, display = research_intro(user_input, state["sections"].get("results", ""))
        state["intro_bullets"] = bullets
        state["_intro_bullets_generated"] = True
        save_state(state)
        _chat_update(history, display)
    except Exception as e:
        _chat_update(history, f"❌ Error during literature search: {e}")
    return "", history, state


# ─── Stage 3b — bullet selection ─────────────

def handle_stage3_select(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    import re
    numbers = re.findall(r"\d+", user_input)
    if not numbers:
        _chat(history, user_input, "Please enter bullet numbers to include, e.g.: `1,3,5,7`")
        return "", history, state

    bullets = state.get("intro_bullets", [])
    selected = [bullets[int(n) - 1] for n in numbers if 0 <= int(n) - 1 < len(bullets)]

    state["selected_bullets"] = selected
    save_state(state)

    _chat_pending(history, user_input, f"⏳ Writing Introduction with {len(selected)} selected bullets...")
    try:
        from stages.stage3_intro import write_introduction
        intro, refs = write_introduction(selected, state["sections"].get("results", ""), state.get("references", []))
        state["sections"]["introduction"] = intro
        state["references"] = refs
        state["_intro_written"] = True
        save_state(state)
        display = f"## Introduction (Stage 3)\n\n{intro}\n\nType `confirm` to proceed or paste corrections."
        _chat_update(history, display)
    except Exception as e:
        _chat_update(history, f"❌ Error writing Introduction: {e}")
    return "", history, state


# ─── Stage 3c — confirm intro ────────────────

def handle_stage3_confirm(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    if user_input.lower() in ("confirm", "yes", "y"):
        state = mark_stage_complete(state, 3)
        reply = (
            "✅ Introduction confirmed. Moving to **Stage 4: Discussion**.\n\n"
            "I will draft the Discussion connecting your results with published literature.\n"
            "Type `start` to begin."
        )
        _chat(history, user_input, reply)
        return "", history, state

    state["_intro_written"] = False
    state["_intro_bullets_generated"] = False
    state["_intro_keywords"] = ""
    save_state(state)
    _chat(history, user_input, "Restarting Introduction research with your feedback. Please provide new keywords:")
    return "", history, state


# ─── Stage 4 ─────────────────────────────────

def handle_stage4(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    if not state.get("_discussion_generated"):
        _chat_pending(history, user_input, "⏳ Drafting Discussion section...")
        try:
            from stages.stage4_discussion import generate_discussion
            text, refs = generate_discussion(
                state["sections"].get("results", ""),
                state["sections"].get("introduction", ""),
                state.get("selected_bullets", []),
                state.get("references", []),
                merge=False,
            )
            state["sections"]["discussion"] = text
            state["_discussion_generated"] = True
            save_state(state)
            display = (
                f"## Discussion (Stage 4)\n\n{text}\n\n"
                "Would you like to **merge** Results and Discussion into a single section? (yes/no)\n"
                "Or type `confirm` to keep them separate."
            )
            _chat_update(history, display)
        except Exception as e:
            _chat_update(history, f"❌ Error: {e}")
        return "", history, state

    if user_input.lower() in ("yes", "y", "merge"):
        state["merge_results_discussion"] = True
        save_state(state)
        from stages.stage4_discussion import generate_discussion
        generate_discussion(
            state["sections"].get("results", ""),
            state["sections"].get("introduction", ""),
            state.get("selected_bullets", []),
            state.get("references", []),
            merge=True,
        )
        state = mark_stage_complete(state, 4)
        _chat(history, user_input, "✅ Results and Discussion merged. Moving to **Stage 5: Materials and Methods**.\nType `start`.")
        return "", history, state

    if user_input.lower() in ("no", "n", "confirm"):
        state = mark_stage_complete(state, 4)
        _chat(history, user_input, "✅ Discussion confirmed. Moving to **Stage 5: Materials and Methods**.\nType `start`.")
        return "", history, state

    _chat(history, user_input, "Please type `yes` to merge, `no` to keep separate, or `confirm` to proceed.")
    return "", history, state


# ─── Stage 5 ─────────────────────────────────

def handle_stage5(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    if not state.get("_methods_generated"):
        _chat_pending(history, user_input, "⏳ Drafting Materials and Methods...")
        try:
            from stages.stage5_methods import generate_methods
            text, warnings, display = generate_methods()
            state["sections"]["methods"] = text
            state["_methods_generated"] = True
            save_state(state)
            display += "\n\nType `confirm` to proceed or paste corrections."
            _chat_update(history, display)
        except Exception as e:
            _chat_update(history, f"❌ Error: {e}")
        return "", history, state

    if user_input.lower() in ("confirm", "yes", "y"):
        state = mark_stage_complete(state, 5)
        reply = (
            "✅ Methods confirmed. Moving to **Stage 6: Abstract**.\n\n"
            "What is your target abstract word count? (typical: 150–300 words)\n"
            "Type a number or press Enter for default (250)."
        )
        _chat(history, user_input, reply)
        return "", history, state

    state["_methods_generated"] = False
    save_state(state)
    return handle_stage5("start", history, state)


# ─── Stage 6 ─────────────────────────────────

def handle_stage6(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    if not state.get("_abstract_generated"):
        wc = 250
        if user_input.strip().isdigit():
            wc = int(user_input.strip())
        state["abstract_word_count"] = wc
        save_state(state)

        _chat_pending(history, user_input, f"⏳ Drafting Abstract (~{wc} words)...")
        try:
            from stages.stage6_abstract import generate_abstract
            text = generate_abstract(
                state["sections"].get("results", ""),
                state["sections"].get("introduction", ""),
                state["sections"].get("discussion", ""),
                state["sections"].get("methods", ""),
                wc,
            )
            state["sections"]["abstract"] = text
            state["_abstract_generated"] = True
            save_state(state)
            display = f"## Abstract (Stage 6)\n\n{text}\n\nType `confirm` to proceed or paste corrections."
            _chat_update(history, display)
        except Exception as e:
            _chat_update(history, f"❌ Error: {e}")
        return "", history, state

    if user_input.lower() in ("confirm", "yes", "y"):
        state = mark_stage_complete(state, 6)
        _chat(history, user_input, "✅ Abstract confirmed. Moving to **Stage 7: Title Suggestions**.\nType `start`.")
        return "", history, state

    state["_abstract_generated"] = False
    save_state(state)
    return handle_stage6("250", history, state)


# ─── Stage 7 ─────────────────────────────────

def handle_stage7(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    if not state.get("_titles_generated"):
        _chat_pending(history, user_input, "⏳ Generating title suggestions...")
        try:
            from stages.stage7_titles import generate_titles
            titles, display = generate_titles(
                state["sections"].get("abstract", ""),
                state["sections"].get("results", ""),
            )
            state["_title_options"] = titles
            state["_titles_generated"] = True
            save_state(state)
            _chat_update(history, display)
        except Exception as e:
            _chat_update(history, f"❌ Error: {e}")
        return "", history, state

    titles = state.get("_title_options", [])
    chosen = user_input.strip()

    if chosen.isdigit():
        idx = int(chosen) - 1
        if 0 <= idx < len(titles):
            chosen = titles[idx]

    if chosen:
        state["chosen_title"] = chosen
        has_toned = (Path(ROOT) / "output" / "manuscript_toned.docx").exists()
        from stages.stage7_titles import apply_title
        apply_title(chosen, use_toned=has_toned)
        save_state(state)
        state = mark_stage_complete(state, 7)

        tone_files = list((ROOT / "input" / "tone_templates").glob("*.pdf")) + \
                     list((ROOT / "input" / "tone_templates").glob("*.docx"))
        if tone_files:
            reply = (
                f"✅ Title set: **{chosen}**\n\n"
                "Moving to **Stage 8: Tone Rewriting**.\n"
                f"Found {len(tone_files)} tone template(s). I'll analyze them and rewrite the manuscript.\n"
                "Type `start`."
            )
        else:
            reply = (
                f"✅ Title set: **{chosen}**\n\n"
                "No tone templates found — skipping Stage 8.\n"
                "Moving to **Stage 9: Authorship**.\n"
                "Please provide authors in order of contribution:\n"
                "Format: `First Last | Affiliation 1 | Affiliation 2` (add `*` for corresponding author)\n"
                "One author per line. When done, type `done`."
            )
            state["current_stage"] = 9
            save_state(state)
        _chat(history, user_input, reply)
        return "", history, state

    _chat(history, user_input, "Please enter the number of your chosen title or paste a custom title.")
    return "", history, state


# ─── Stage 8 ─────────────────────────────────

def handle_stage8(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    if not state.get("_tone_done"):
        _chat_pending(history, user_input, "⏳ Analyzing tone templates and rewriting manuscript (this may take a few minutes)...")
        try:
            from stages.stage8_tone import analyze_tone, rewrite_in_tone
            tone = analyze_tone()
            if not tone:
                _chat_update(history, "No tone templates found. Skipping Stage 8.")
                state = mark_stage_complete(state, 8)
                save_state(state)
                return "", history, state

            rewrite_in_tone(tone)
            state["tone_analyzed"] = True
            state["_tone_done"] = True
            save_state(state)
            _chat_update(history, (
                "✅ Manuscript rewritten in author's tone → `output/manuscript_toned.docx`\n\n"
                "Type `confirm` to proceed."
            ))
        except Exception as e:
            _chat_update(history, f"❌ Error: {e}")
        return "", history, state

    if user_input.lower() in ("confirm", "yes", "y"):
        state = mark_stage_complete(state, 8)
        reply = (
            "Moving to **Stage 9: Authorship**.\n\n"
            "Please provide authors in order of contribution (one per line):\n"
            "`First Last | Affiliation 1 | Affiliation 2`\n"
            "Add `*` after the corresponding author's name.\n\n"
            "When done listing all authors, type `done` on the last line."
        )
        _chat(history, user_input, reply)
        return "", history, state

    _chat(history, user_input, "Type `confirm` to proceed.")
    return "", history, state


# ─── Stage 9 ─────────────────────────────────

def handle_stage9(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    if not state.get("_author_input_collecting"):
        state["_author_buffer"] = ""
        state["_author_input_collecting"] = True
        save_state(state)

    if "done" in user_input.lower():
        raw_authors = state.get("_author_buffer", "") + "\n" + user_input.replace("done", "").strip()
        if not raw_authors.strip():
            _chat(history, user_input, "No author input found. Please provide at least one author.")
            return "", history, state

        state["_author_raw"] = raw_authors
        state["_awaiting_email"] = True
        save_state(state)
        _chat(history, user_input, "Please enter the corresponding author's email address:")
        return "", history, state

    if state.get("_awaiting_email"):
        email = user_input.strip()
        raw_authors = state.get("_author_raw", "")
        try:
            from stages.stage9_authors import parse_author_input, format_author_block, insert_authors_into_doc
            authors = parse_author_input(raw_authors)
            author_line, aff_block = format_author_block(authors, email)
            state["authors"] = authors

            has_toned = (ROOT / "output" / "manuscript_toned.docx").exists()
            filename = "manuscript_toned.docx" if has_toned else "manuscript_draft.docx"
            insert_authors_into_doc(filename, author_line, aff_block)
            state["_awaiting_email"] = False
            state["_author_input_collecting"] = False
            save_state(state)
            state = mark_stage_complete(state, 9)
            reply = (
                f"✅ Authors formatted:\n\n**{author_line}**\n\n{aff_block}\n\n"
                "Moving to **Stage 10: Journal Formatting**.\n\n"
                "Which journal are you targeting? (e.g., 'Nature', 'Cell', 'PLOS ONE', 'Journal of Biological Chemistry')"
            )
            _chat(history, user_input, reply)
        except Exception as e:
            _chat(history, user_input, f"❌ Error: {e}")
        return "", history, state

    state["_author_buffer"] = state.get("_author_buffer", "") + "\n" + user_input
    save_state(state)
    _chat(history, user_input, "Author line recorded. Continue adding authors or type `done` when finished.")
    return "", history, state


# ─── Stage 10 ─────────────────────────────────

def handle_stage10(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    if not state.get("_journal_requirements_fetched"):
        journal = user_input.strip()
        state["target_journal"] = journal
        save_state(state)

        _chat_pending(history, user_input, f"⏳ Looking up formatting requirements for '{journal}'...")
        try:
            from stages.stage10_journal import get_journal_requirements, reformat_references, finalize_manuscript
            reqs = get_journal_requirements(journal)
            state["_journal_requirements"] = reqs
            state["_journal_requirements_fetched"] = True
            save_state(state)

            refs = reformat_references(state.get("references", []), journal, reqs)
            state["references"] = refs
            from utils.doc_builder import save_references_md
            save_references_md(refs)

            has_toned = (ROOT / "output" / "manuscript_toned.docx").exists()
            src = "manuscript_toned.docx" if has_toned else "manuscript_draft.docx"
            final_path = finalize_manuscript(src)
            state = mark_stage_complete(state, 10)
            save_state(state)

            reply = (
                f"✅ **Manuscript complete!**\n\n"
                f"Journal: {journal}\n"
                f"References reformatted to {journal} style.\n\n"
                f"**Output files:**\n"
                f"- `output/manuscript_final.docx` — final formatted manuscript\n"
                f"- `output/manuscript_toned.docx` — tone-rewritten version\n"
                f"- `output/manuscript_draft.docx` — draft with all sections\n"
                f"- `output/figures_captions.docx` — official figure captions\n"
                f"- `output/references.md` — full reference list\n"
                f"- `output/tone.md` — writing style analysis\n\n"
                f"**Journal requirements summary:**\n{reqs[:800]}"
            )
            _chat_update(history, reply)
        except Exception as e:
            _chat_update(history, f"❌ Error: {e}")
        return "", history, state

    _chat(history, user_input, "Stage 10 complete. Type `status` to see output files.")
    return "", history, state


# ──────────────────────────────────────────────
# Gradio UI
# ──────────────────────────────────────────────

def create_app():
    with gr.Blocks(title="Manuscript Writing Agent") as app:
        state = gr.State(load_state)

        gr.Markdown("# 📄 Manuscript Writing Agent\nAI-powered peer-reviewed manuscript pipeline")

        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="Manuscript Pipeline",
                    height=600,
                    render_markdown=True,
                )
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Type your message or command here...",
                        label="",
                        lines=3,
                        scale=5,
                    )
                    send_btn = gr.Button("Send ▶", scale=1, variant="primary")

            with gr.Column(scale=1):
                gr.Markdown("### 📁 Input Files")
                file_status = gr.HTML(get_file_status())
                refresh_btn = gr.Button("🔄 Refresh Status", size="sm")
                reset_btn = gr.Button("⚠️ Reset All Progress", size="sm", variant="stop")

        # Ribosome translation progress bar — full width, bottom of page
        stage_display = gr.HTML(get_stage_display(load_state()))

        def submit(user_input, history, state_val):
            out_text, new_history, new_state = process_message(user_input, history or [], state_val)
            return out_text, new_history, new_state, get_stage_display(new_state), get_file_status()

        send_btn.click(
            submit,
            inputs=[msg_input, chatbot, state],
            outputs=[msg_input, chatbot, state, stage_display, file_status],
        )
        msg_input.submit(
            submit,
            inputs=[msg_input, chatbot, state],
            outputs=[msg_input, chatbot, state, stage_display, file_status],
        )

        refresh_btn.click(
            lambda s: (get_stage_display(s), get_file_status()),
            inputs=[state],
            outputs=[stage_display, file_status],
        )

        def reset_state():
            from utils.state_manager import DEFAULT_STATE, save_state as ss
            fresh = dict(DEFAULT_STATE)
            ss(fresh)
            return [], fresh, get_stage_display(fresh), get_file_status()

        reset_btn.click(
            reset_state,
            outputs=[chatbot, state, stage_display, file_status],
        )

        def on_load(history, state_val):
            out_text, new_history, new_state = process_message("", history or [], state_val)
            return out_text, new_history, new_state, get_stage_display(new_state), get_file_status()

        app.load(
            on_load,
            inputs=[chatbot, state],
            outputs=[msg_input, chatbot, state, stage_display, file_status],
        )

    return app


_FILE_GROUPS = [
    ("🖼️  Figures & Captions", ["figures", "captions"]),
    ("📊  Raw Data",            ["results", "methods"]),
    ("✍️  Style Templates",     ["tone_templates"]),
]


def get_file_status() -> str:
    input_dir = ROOT / "input"
    parts = ['<div class="file-status-panel">']
    for group_label, folders in _FILE_GROUPS:
        parts.append(f'<div class="file-group"><div class="file-group-header">{group_label}</div>')
        for folder in folders:
            d = input_dir / folder
            if d.exists():
                files = sorted(f for f in d.iterdir() if not f.name.startswith("."))
                n = len(files)
                badge_cls = "fbadge-ok" if n else "fbadge-empty"
                parts.append(
                    f'<div class="folder-row">'
                    f'<span class="fname">{folder}/</span>'
                    f'<span class="fbadge {badge_cls}">{n}</span>'
                    f'</div>'
                )
                if files:
                    parts.append('<div class="fnames">')
                    for f in files[:4]:
                        parts.append(f'<div class="fentry">· {f.name}</div>')
                    if n > 4:
                        parts.append(f'<div class="fentry fmuted">+ {n - 4} more</div>')
                    parts.append('</div>')
            else:
                parts.append(
                    f'<div class="folder-row">'
                    f'<span class="fname">{folder}/</span>'
                    f'<span class="fbadge fbadge-warn">⚠</span>'
                    f'</div>'
                )
        parts.append('</div>')
    parts.append('</div>')
    return "".join(parts)


STAGE_NAMES = {
    0: "Startup & File Verification",
    1: "Figure Captions",
    2: "Results Section",
    3: "Introduction (Deep Research)",
    4: "Discussion",
    5: "Materials and Methods",
    6: "Abstract",
    7: "Title Suggestions",
    8: "Tone Rewriting",
    9: "Authorship & Affiliations",
    10: "Journal Formatting",
}

_STAGE_COLORS = {
    1: "#4CC9F0", 2: "#4361EE", 3: "#3A0CA3", 4: "#7209B7",
    5: "#F72585", 6: "#E85D04", 7: "#F48C06", 8: "#AACC00",
    9: "#55A630", 10: "#007F5F",
}

_STAGE_SHORT = {
    0: "Verify", 1: "Captions", 2: "Results", 3: "Intro",
    4: "Discussion", 5: "Methods", 6: "Abstract", 7: "Titles",
    8: "Tone", 9: "Authors", 10: "Journal",
}


def _ribo_left(stage: int) -> float:
    """Ribosome center position as % of mrna-track width. AUG=8%, 10 codons=84%, UAA=8%."""
    if stage == 0:
        return 4.0
    if stage <= 10:
        return 8.0 + (stage - 0.5) * 8.4
    return 96.0


def get_stage_display(state: dict) -> str:
    current = state.get("current_stage", 0)
    completed = set(state.get("completed_stages", []))

    # AUG start codon
    if 0 in completed:
        aug_cls = "aug-done"
    elif current == 0:
        aug_cls = "aug-active"
    else:
        aug_cls = "aug-pending"

    # mRNA coding segments — 3-tick codon structure, labels moved below track
    codons_html = ""
    for i in range(1, 11):
        color = _STAGE_COLORS[i]
        if i in completed:
            cls, tick = "codon-done", '<div class="codon-tick">✓</div>'
        elif i == current:
            cls, tick = "codon-active", ""
        else:
            cls, tick = "codon-pending", ""
        codons_html += (
            f'<div class="mrna-codon {cls}" style="--cc:{color}">'
            f'{tick}'
            f'<div class="codon-ticks"><div class="ctick"></div><div class="ctick"></div><div class="ctick"></div></div>'
            f'</div>'
        )

    # Label row below the mRNA track
    labels_html = (
        '<div class="codon-labels-row">'
        '<div class="codon-label-spacer"></div>'
        + "".join(f'<div class="codon-label-item">{_STAGE_SHORT[i]}</div>' for i in range(1, 11))
        + '<div class="codon-label-spacer"></div>'
        '</div>'
    )

    # Peptide chain — anchored to upper-left of ribosome, grows leftward
    done_stages = sorted(s for s in completed if 1 <= s <= 10)
    if done_stages:
        beads = []
        for s in done_stages:
            beads.append(
                f'<div class="aa-bead" style="background:{_STAGE_COLORS[s]}" title="{_STAGE_SHORT[s]}"></div>'
            )
        peptide_inner = (
            '<div class="peptide-exit">'
            + '<div class="aa-link"></div>'.join(beads)
            + '</div>'
        )
    else:
        peptide_inner = ""

    # Stage info line
    if current > 10:
        info_html = '<div class="stage-info done-info">✅ Translation complete — all 10 stages done!</div>'
    else:
        full_name = STAGE_NAMES.get(current, f"Stage {current}")
        info_html = f'<div class="stage-info">▶ <strong>Stage {current}:</strong> {full_name}</div>'

    stop_cls = "stop-done" if current > 10 else ""
    ribo_pct = _ribo_left(current)

    return (
        '<div class="translation-bar">'
        '<div class="mrna-track">'
        f'<div class="aug-block {aug_cls}"><div class="aug-text">START</div></div>'
        f'<div class="codons-area">{codons_html}</div>'
        f'<div class="stop-block {stop_cls}"><div class="aug-text">END</div></div>'
        f'<div class="ribosome-widget" style="left:{ribo_pct:.1f}%">'
        f'{peptide_inner}'
        '<div class="ribo-large"></div>'
        '<div class="ribo-channel"></div>'
        '<div class="ribo-small"></div>'
        '</div>'
        '</div>'
        f'{labels_html}'
        f'{info_html}'
        '</div>'
    )


if __name__ == "__main__":
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        theme=gr.themes.Base(
            primary_hue="blue",
            secondary_hue="cyan",
            neutral_hue="slate",
            font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "sans-serif"],
        ),
        css=(ROOT / "utils/style.css").read_text(),
    )
