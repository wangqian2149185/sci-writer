"""
SciCooker — Gradio Web UI
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
    if stage == 3 and not state.get("_results_findings_confirmed"):
        return handle_stage3_extract(user_input, history, state)
    if stage == 3 and state.get("_results_findings_confirmed") and not state.get("_intro_bullets_generated"):
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
        "## 👋 Welcome to SciCooker\n\n"
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
            "✅ Results confirmed. Moving to **Stage 3: Introduction**.\n\n"
            "First, I will extract the key findings from your Results section to anchor the Introduction's logic. "
            "Type `start` to begin."
        )
        _chat(history, user_input, reply)
        return "", history, state

    state["sections"]["results"] += f"\n\n[User correction: {user_input}]"
    state["_results_generated"] = False
    save_state(state)
    return handle_stage2("start", history, state)


# ─── Stage 3-pre — extract Results findings ──

def handle_stage3_extract(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    # Step 1 — run extraction if not yet done
    if not state.get("_results_extracted"):
        results_text = state["sections"].get("results", "")
        if not results_text.strip():
            _chat(history, user_input,
                  "⚠️ No Results section found in state. Please complete Stage 2 first.")
            return "", history, state

        _chat_pending(history, user_input,
                      "⏳ Extracting key findings from the Results section before drafting the Introduction...")
        try:
            from stages.stage3_intro import extract_results_findings
            findings, display = extract_results_findings(results_text)
            state["_results_findings"] = findings
            state["_results_extracted"] = True
            save_state(state)
            _chat_update(history, display)
        except Exception as e:
            _chat_update(history, f"❌ Error extracting findings: {e}")
        return "", history, state

    # Step 2 — await user confirmation or accept edited list
    if user_input.lower() in ("confirm", "yes", "y"):
        state["_results_findings_confirmed"] = True
        save_state(state)
        reply = (
            "✅ Findings confirmed. The Introduction will be anchored to these results.\n\n"
            "Now please provide keywords, field names, or any preferences for the literature search.\n"
            "Example: `CRISPR gene editing, DNA repair mechanisms, cancer therapy`"
        )
        _chat(history, user_input, reply)
        return "", history, state

    # User provided an edited/amended list — replace findings and re-display
    if user_input.strip():
        import re
        updated = []
        for line in user_input.split("\n"):
            clean = re.sub(r"^[\d\.\-\•\*]+\s*", "", line.strip()).strip()
            if clean:
                updated.append(clean)
        if updated:
            state["_results_findings"] = updated
            save_state(state)
            display = (
                "## Updated findings list\n\n"
                + "\n".join(f"{i+1}. {f}" for i, f in enumerate(updated))
                + "\n\n---\nType `confirm` to proceed, or continue editing."
            )
            _chat(history, user_input, display)
            return "", history, state

    _chat(history, user_input,
          "Type `confirm` to proceed with the findings as listed, or paste an edited version.")
    return "", history, state


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

def _interpret_selection(user_input: str, bullets: list[str], total: int) -> list[int]:
    """Call LLM to interpret user's paper selection. Returns 1-based indices."""
    from utils.claude_client import chat
    import re
    titles = [b.split("\n")[0][:100] for b in bullets]
    paper_list = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))
    prompt = (
        f"The user was shown {total} papers and asked which to include in a manuscript introduction.\n\n"
        f"Papers:\n{paper_list}\n\n"
        f"User's response: \"{user_input}\"\n\n"
        "Return ONLY a comma-separated list of 1-based paper numbers the user wants to include. "
        "If the user wants all papers, return every number from 1 to {total}. No explanation, no other text."
    ).replace("{total}", str(total))
    response = chat([{"role": "user", "content": prompt}], max_tokens=300)
    return [int(n) for n in re.findall(r"\d+", response) if 1 <= int(n) <= total]


def handle_stage3_select(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    bullets = state.get("intro_bullets", [])
    total = len(bullets)

    if not user_input.strip():
        _chat(history, user_input, "Please enter paper numbers to include, e.g.: `1,3,5` or `all`")
        return "", history, state

    _chat_pending(history, user_input, "⏳ Interpreting selection and writing Introduction...")
    try:
        indices = _interpret_selection(user_input, bullets, total)
        if not indices:
            _chat_update(history, "Could not determine which papers to include. Please specify numbers, e.g.: `1,3,5` or `all`")
            return "", history, state

        selected = [bullets[i - 1] for i in indices if 1 <= i <= total]
        state["selected_bullets"] = selected
        save_state(state)

        from stages.stage3_intro import write_introduction
        intro, refs = write_introduction(
            selected,
            state["sections"].get("results", ""),
            state.get("references", []),
            confirmed_findings=state.get("_results_findings"),
        )
        state["sections"]["introduction"] = intro
        state["references"] = refs
        state["_intro_written"] = True
        save_state(state)
        display = f"## Introduction (Stage 3)\n\n{intro}\n\nType `confirm` to proceed or paste corrections."
        _chat_update(history, display)
    except Exception as e:
        _chat_update(history, f"❌ Error: {e}")
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
    # 7a — generate title options
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

    # 7b — title selection
    if not state.get("_title_chosen"):
        titles = state.get("_title_options", [])
        chosen = user_input.strip()
        if chosen.isdigit():
            idx = int(chosen) - 1
            if 0 <= idx < len(titles):
                chosen = titles[idx]
        if not chosen:
            _chat(history, user_input, "Please enter the number of your chosen title or paste a custom title.")
            return "", history, state

        state["chosen_title"] = chosen
        state["_title_chosen"] = True
        has_toned = (Path(ROOT) / "output" / "manuscript_toned.docx").exists()
        from stages.stage7_titles import apply_title
        apply_title(chosen, use_toned=has_toned)
        save_state(state)

        reply = (
            f"✅ Title set: **{chosen}**\n\n"
            "Now let's draft the **Acknowledgements** section.\n\n"
            "Please provide the following information (include whatever applies):\n"
            "- **Funding**: full agency name, grant number, PI name\n"
            "- **Individual contributions**: name, role (e.g., technical assistance, statistical consultation)\n"
            "- **AI tool disclosure**: tool name and how it was used (if applicable)\n"
            "- **Data availability**: repository URL and DOI (if applicable)\n\n"
            "Paste all relevant details, then press **Send**. "
            "Type `skip` to leave a placeholder and proceed."
        )
        _chat(history, user_input, reply)
        return "", history, state

    # 7c — acknowledgements collection and generation
    if not state.get("_acknowledgements_generated"):
        if user_input.lower().strip() == "skip":
            ack_text = (
                "Funding: [FUNDING AGENCY, Grant No. XXXX, PI: NAME]. "
                "[CONTRIBUTOR NAME] provided [CONTRIBUTION]. "
                "All data and code are available at [REPOSITORY URL], DOI: [10.xxxx/xxxxx]."
            )
            from utils.doc_builder import append_section
            append_section("manuscript_draft.docx", "Acknowledgements", ack_text)
            state["sections"]["acknowledgements"] = ack_text
        else:
            _chat_pending(history, user_input, "⏳ Drafting Acknowledgements section...")
            try:
                from stages.stage7_titles import generate_acknowledgements
                ack_text = generate_acknowledgements(user_input)
                state["sections"]["acknowledgements"] = ack_text
                _chat_update(history, f"## Acknowledgements\n\n{ack_text}\n\nType `confirm` to proceed or paste corrections.")
            except Exception as e:
                _chat_update(history, f"❌ Error: {e}")
            state["_acknowledgements_generated"] = True
            save_state(state)
            return "", history, state

        state["_acknowledgements_generated"] = True
        save_state(state)
        _chat(history, user_input, f"## Acknowledgements (placeholder)\n\n{ack_text}\n\nType `confirm` to proceed.")
        return "", history, state

    # 7d — confirm or correct acknowledgements
    if user_input.lower() in ("confirm", "yes", "y"):
        state = mark_stage_complete(state, 7)
        tone_files = list((ROOT / "input" / "tone_templates").glob("*.pdf")) + \
                     list((ROOT / "input" / "tone_templates").glob("*.docx"))
        if tone_files:
            reply = (
                "✅ Acknowledgements confirmed.\n\n"
                "Moving to **Stage 8: Tone Rewriting**.\n"
                f"Found {len(tone_files)} tone template(s). I'll analyze them and rewrite the manuscript.\n"
                "Type `start`."
            )
        else:
            reply = (
                "✅ Acknowledgements confirmed.\n\n"
                "No tone templates found — skipping Stage 8.\n"
                "Moving to **Stage 9: Authorship**.\n\n"
                "Type `start` to begin collecting author information."
            )
            state["current_stage"] = 9
            save_state(state)
        _chat(history, user_input, reply)
        return "", history, state

    # Correction — regenerate
    _chat_pending(history, user_input, "⏳ Regenerating Acknowledgements with your corrections...")
    try:
        from stages.stage7_titles import generate_acknowledgements
        ack_text = generate_acknowledgements(user_input)
        state["sections"]["acknowledgements"] = ack_text
        save_state(state)
        _chat_update(history, f"## Acknowledgements\n\n{ack_text}\n\nType `confirm` to proceed or paste corrections.")
    except Exception as e:
        _chat_update(history, f"❌ Error: {e}")
    return "", history, state


# ─── Stage 8 ─────────────────────────────────

_S8_MENU = (
    "**Stage 8: Tone Rewriting**\n\n"
    "Choose the style source for tone matching:\n\n"
    "**`1`** — Use uploaded papers in `input/tone_templates/`\n"
    "**`2`** — Search by author name and institution\n"
    "**`3`** — Enter an ORCID iD directly\n\n"
    "Reply with `1`, `2`, or `3`."
)


def _s8_run_orcid_analysis(orcid_id: str, author_name: str, user_input: str,
                            history: list, state: dict) -> tuple[str, list, dict]:
    """Shared helper: fetch ORCID papers, analyze, update history."""
    _chat_pending(history, user_input,
        f"⏳ Fetching papers for **{author_name}** (ORCID: `{orcid_id}`) "
        "and analyzing writing style — this may take 2–3 minutes...")
    try:
        from stages.stage8_tone import analyze_tone_from_orcid
        profile = analyze_tone_from_orcid(orcid_id, author_name)
        if not profile:
            _chat_update(history,
                f"⚠️ No papers with retrievable abstracts found for ORCID `{orcid_id}`.\n\n"
                "The profile may have no public works, or abstracts are paywalled.\n"
                "Try uploading papers to `input/tone_templates/` and choose option `1`.\n\n"
                + _S8_MENU)
            state["_tone_step"] = "source_choice"
        else:
            state["_tone_profile"] = profile
            state["_tone_step"] = "pending_rewrite"
            _chat_update(history,
                f"✅ Style profile generated for **{author_name}**.\n\n"
                f"{profile[:1400]}{'...' if len(profile) > 1400 else ''}\n\n"
                "---\nFull profile saved to `output/tone.md`.\n\n"
                "Type `confirm` to rewrite the manuscript in this style, "
                "or `restart` to choose a different style source.")
    except Exception as e:
        _chat_update(history, f"❌ Error during ORCID analysis: {e}")
    save_state(state)
    return "", history, state


def handle_stage8(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    step = state.get("_tone_step", "init")

    # ── init — show source options ─────────────────────────────────────────────
    if step == "init":
        state["_tone_step"] = "source_choice"
        save_state(state)
        tone_dir = ROOT / "input" / "tone_templates"
        n_files = sum(1 for f in tone_dir.glob("*") if f.suffix in (".pdf", ".docx", ".txt"))
        hint = f" ({n_files} file(s) found)" if n_files else " *(no files yet — upload PDFs/DOCXs first)*"
        reply = (
            "**Stage 8: Tone Rewriting**\n\n"
            "Choose the style source for tone matching:\n\n"
            f"**`1`** — Use uploaded papers in `input/tone_templates/`{hint}\n"
            "**`2`** — Search by author name and institution → auto-fetch ORCID + papers\n"
            "**`3`** — Enter an ORCID iD directly\n\n"
            "Reply with `1`, `2`, or `3`."
        )
        _chat(history, user_input, reply)
        return "", history, state

    # ── source choice ──────────────────────────────────────────────────────────
    if step == "source_choice":
        c = user_input.strip()

        if c == "1":
            _chat_pending(history, user_input,
                "⏳ Analyzing tone templates and building style profile (may take a few minutes)...")
            try:
                from stages.stage8_tone import analyze_tone
                profile = analyze_tone()
                if not profile:
                    state["_tone_step"] = "source_choice"
                    save_state(state)
                    _chat_update(history,
                        "⚠️ No files found in `input/tone_templates/`. "
                        "Upload PDFs or DOCX papers, then reply `1` again.\n\n"
                        + _S8_MENU)
                else:
                    state["_tone_profile"] = profile
                    state["_tone_step"] = "pending_rewrite"
                    save_state(state)
                    _chat_update(history,
                        "✅ Style profile generated from uploaded templates.\n\n"
                        f"{profile[:1400]}{'...' if len(profile) > 1400 else ''}\n\n"
                        "---\nFull profile saved to `output/tone.md`.\n\n"
                        "Type `confirm` to rewrite the manuscript in this style, "
                        "or `restart` to choose a different style source.")
            except Exception as e:
                _chat_update(history, f"❌ Error analyzing templates: {e}")
            return "", history, state

        elif c == "2":
            state["_tone_step"] = "name_entry"
            save_state(state)
            _chat(history, user_input,
                "Enter the author's full name and institution:\n\n"
                "Format: `Last, First | Institution`\n\n"
                "Example: `Zhang, Feng | Broad Institute of MIT and Harvard`\n\n"
                "*(Institution is optional but improves search accuracy.)*")
            return "", history, state

        elif c == "3":
            state["_tone_step"] = "orcid_entry"
            save_state(state)
            _chat(history, user_input,
                "Enter the ORCID iD:\n\n"
                "Format: `XXXX-XXXX-XXXX-XXXX`\n\n"
                "Example: `0000-0001-8593-9998`")
            return "", history, state

        else:
            _chat(history, user_input, "Please reply with `1`, `2`, or `3`.")
            return "", history, state

    # ── name entry — ORCID lookup (API + web fallback inline) ─────────────────
    if step == "name_entry":
        val = user_input.strip()
        if not val:
            _chat(history, user_input,
                "Please enter the author's name (and optionally institution after `|`).")
            return "", history, state

        parts = [p.strip() for p in val.split("|")]
        name = parts[0]
        institution = parts[1] if len(parts) > 1 else ""
        state["_tone_author_query"] = name
        save_state(state)

        _chat_pending(history, user_input, f"⏳ Searching ORCID registry for **{name}**...")
        try:
            from stages.stage8_tone import search_orcid_by_name, search_orcid_web
            candidates = search_orcid_by_name(name, institution)

            if candidates:
                state["_tone_orcid_candidates"] = candidates
                state["_tone_step"] = "name_results"
                save_state(state)
                lines = [f"Found **{len(candidates)}** ORCID profile(s):\n"]
                for i, cand in enumerate(candidates, 1):
                    aff = f" — {cand['institution']}" if cand["institution"] else ""
                    lines.append(
                        f"**{i}.** {cand['name']}{aff}  \n"
                        f"   ORCID: `{cand['orcid_id']}`"
                    )
                lines += [
                    "",
                    "Reply with the **number** of the correct match, paste an ORCID iD directly, "
                    "or type `none` if none of these is correct.",
                ]
                _chat_update(history, "\n".join(lines))

            else:
                _chat_update(history,
                    f"⏳ No registry matches for **'{name}'**. Searching the web...")
                orcid_id, snippet = search_orcid_web(name)
                if orcid_id:
                    state["_tone_orcid_candidates"] = [
                        {"orcid_id": orcid_id, "name": name, "institution": ""}
                    ]
                    state["_tone_step"] = "name_results"
                    save_state(state)
                    _chat_update(history,
                        f"Found via web search:\n\n"
                        f"**1.** `{orcid_id}` — {snippet[:120]}\n\n"
                        "Reply `1` to confirm, paste a different ORCID iD, "
                        "or type `none` to enter manually.")
                else:
                    state["_tone_step"] = "orcid_entry"
                    save_state(state)
                    _chat_update(history,
                        f"Could not locate ORCID for **'{name}'** via registry or web search.\n\n"
                        "Please enter the ORCID iD manually (format: `XXXX-XXXX-XXXX-XXXX`):")

        except Exception as e:
            _chat_update(history, f"❌ Error during ORCID search: {e}")
        return "", history, state

    # ── name results — user picks a candidate, then we analyze inline ──────────
    if step == "name_results":
        import re as _re
        val = user_input.strip()
        candidates = state.get("_tone_orcid_candidates", [])

        if val.lower() == "none":
            state["_tone_step"] = "orcid_entry"
            save_state(state)
            _chat(history, user_input,
                "Please enter the ORCID iD manually:\n\n"
                "Format: `XXXX-XXXX-XXXX-XXXX`")
            return "", history, state

        orcid_id = ""
        author_name = state.get("_tone_author_query", "")

        if val.isdigit():
            idx = int(val) - 1
            if 0 <= idx < len(candidates):
                orcid_id = candidates[idx]["orcid_id"]
                author_name = candidates[idx]["name"] or author_name
            else:
                _chat(history, user_input,
                    f"Invalid number. Enter 1–{len(candidates)}, paste an ORCID iD, or type `none`.")
                return "", history, state
        elif _re.match(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$", val):
            orcid_id = val
        else:
            _chat(history, user_input,
                "Enter the number of the correct match, paste an ORCID iD, or type `none`.")
            return "", history, state

        state["_tone_orcid"] = orcid_id
        state["_tone_author_name"] = author_name
        save_state(state)
        return _s8_run_orcid_analysis(orcid_id, author_name, user_input, history, state)

    # ── direct ORCID entry — validate then analyze inline ─────────────────────
    if step == "orcid_entry":
        import re as _re
        val = user_input.strip()
        if not _re.match(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$", val):
            _chat(history, user_input,
                "⚠️ Invalid ORCID format. Expected `XXXX-XXXX-XXXX-XXXX`\n\n"
                "Example: `0000-0001-8593-9998`")
            return "", history, state

        author_name = state.get("_tone_author_query", val)
        state["_tone_orcid"] = val
        state["_tone_author_name"] = author_name
        save_state(state)
        return _s8_run_orcid_analysis(val, author_name, user_input, history, state)

    # ── pending rewrite — confirm then rewrite ─────────────────────────────────
    if step == "pending_rewrite":
        val = user_input.strip().lower()

        if val == "restart":
            for k in ("_tone_profile", "_tone_orcid", "_tone_author_name",
                      "_tone_orcid_candidates", "_tone_author_query"):
                state.pop(k, None)
            state["_tone_step"] = "source_choice"
            save_state(state)
            _chat(history, user_input, _S8_MENU)
            return "", history, state

        if val not in ("confirm", "yes", "y"):
            _chat(history, user_input,
                "Type `confirm` to rewrite the manuscript in the analyzed style, "
                "or `restart` to choose a different style source.")
            return "", history, state

        _chat_pending(history, user_input,
            "⏳ Rewriting manuscript in analyzed style — this may take 3–5 minutes...")
        try:
            from stages.stage8_tone import rewrite_in_tone
            rewrite_in_tone(state.get("_tone_profile", ""))
            state["_tone_step"] = "done"
            state["_tone_done"] = True
            save_state(state)
            _chat_update(history,
                "✅ Manuscript rewritten → `output/manuscript_toned.docx`\n\n"
                "Style compliance report → `output/style_compliance_report.md`\n\n"
                "Type `confirm` to proceed to **Stage 9: Authorship**.")
        except Exception as e:
            _chat_update(history, f"❌ Error during rewriting: {e}")
        return "", history, state

    # ── done — confirm and advance ─────────────────────────────────────────────
    if step == "done":
        if user_input.strip().lower() in ("confirm", "yes", "y"):
            state = mark_stage_complete(state, 8)
            save_state(state)
            _chat(history, user_input,
                "✅ Tone rewriting complete.\n\n"
                "Moving to **Stage 9: Authorship**.\n\n"
                "Type `start` to begin collecting author information.")
        else:
            _chat(history, user_input, "Type `confirm` to proceed to Stage 9.")
        return "", history, state

    # Fallback
    state["_tone_step"] = "init"
    save_state(state)
    return handle_stage8("", history, state)


# ─── Stage 9 ─────────────────────────────────

_STAGE9_STEP1 = (
    "**Step 1 of 3 — First Author**\n\n"
    "Enter the first author's name and affiliations:\n\n"
    "Format: `Last, First | Affiliation 1 | Affiliation 2`\n\n"
    "Example: `Smith, John | Department of Biology, MIT | Broad Institute`"
)

_STAGE9_STEP2 = (
    "**Step 2 of 3 — Corresponding Author**\n\n"
    "Enter the corresponding author's name, affiliations, and email:\n\n"
    "Format: `Last, First | Affiliation 1 | Affiliation 2 | email@institution.edu`\n\n"
    "If the corresponding author is the same as the first author, enter their details again (with email)."
)

_STAGE9_STEP3 = (
    "**Step 3 of 3 — Other Authors**\n\n"
    "Enter each remaining author on a separate line, in decreasing priority order:\n\n"
    "Format: `Last, First | Affiliation 1 | Affiliation 2`\n\n"
    "Type `done` when all authors have been entered, or `done` immediately if there are no other authors."
)


def handle_stage9(user_input: str, history: list, state: dict) -> tuple[str, list, dict]:
    step = state.get("_author_step", "init")

    # ── init ──────────────────────────────────────────────────────────────────
    if step == "init":
        state["_author_step"] = "first_author"
        state["_author_others_buf"] = []
        save_state(state)
        _chat(history, user_input, _STAGE9_STEP1)
        return "", history, state

    # ── collect first author ───────────────────────────────────────────────
    if step == "first_author":
        if not user_input.strip() or "|" not in user_input:
            _chat(history, user_input,
                  "⚠️ Invalid format. Please use: `Last, First | Affiliation 1 | Affiliation 2`")
            return "", history, state

        from stages.stage9_authors import parse_author_line
        state["_author_first"] = parse_author_line(user_input.strip())
        state["_author_step"] = "corresponding"
        save_state(state)
        _chat(history, user_input, _STAGE9_STEP2)
        return "", history, state

    # ── collect corresponding author ───────────────────────────────────────
    if step == "corresponding":
        if not user_input.strip() or "|" not in user_input:
            _chat(history, user_input,
                  "⚠️ Invalid format. Please use: `Last, First | Affiliation 1 | email@domain.com`")
            return "", history, state

        from stages.stage9_authors import parse_corresponding_line
        state["_author_corresponding"] = parse_corresponding_line(user_input.strip())
        state["_author_step"] = "others"
        save_state(state)
        _chat(history, user_input, _STAGE9_STEP3)
        return "", history, state

    # ── collect other authors (multi-line, terminated by "done") ──────────
    if step == "others":
        if user_input.strip().lower() == "done":
            state["_author_step"] = "co_first"
            save_state(state)
            others = state.get("_author_others_buf", [])
            if others:
                names = ", ".join(a["name"] for a in others)
                buf_display = f"Other authors recorded: {names}\n\n"
            else:
                buf_display = "No other authors recorded.\n\n"
            _chat(history, user_input,
                  buf_display + "Are there any **co-first authors** (authors who contributed equally)? "
                  "Reply `yes` or `no`.")
            return "", history, state

        if not user_input.strip() or "|" not in user_input:
            _chat(history, user_input,
                  "⚠️ Invalid format. Use: `Last, First | Affiliation 1 | Affiliation 2`  "
                  "— or type `done` if there are no more authors.")
            return "", history, state

        from stages.stage9_authors import parse_author_line
        author = parse_author_line(user_input.strip())
        buf = state.get("_author_others_buf", [])
        buf.append(author)
        state["_author_others_buf"] = buf
        save_state(state)
        _chat(history, user_input,
              f"✓ Added: **{author['name']}**. Enter the next author or type `done` to finish.")
        return "", history, state

    # ── co-first yes/no ───────────────────────────────────────────────────
    if step == "co_first":
        if user_input.strip().lower() in ("yes", "y"):
            state["_author_step"] = "co_first_names"
            save_state(state)
            _chat(history, user_input,
                  "List the names of all co-first authors (comma-separated), "
                  "exactly as entered above.\n\nExample: `Smith, John, Lee, Jane`")
            return "", history, state

        if user_input.strip().lower() in ("no", "n"):
            state["_co_first_names"] = []
            state["_author_step"] = "generate"
            save_state(state)
            return handle_stage9("", history, state)

        _chat(history, user_input, "Please reply `yes` or `no`.")
        return "", history, state

    # ── collect co-first author names ─────────────────────────────────────
    if step == "co_first_names":
        names = [n.strip() for n in user_input.replace(";", ",").split(",") if n.strip()]
        state["_co_first_names"] = names
        state["_author_step"] = "generate"
        save_state(state)
        return handle_stage9("", history, state)

    # ── generate author block ─────────────────────────────────────────────
    if step == "generate":
        from stages.stage9_authors import (
            assign_affiliation_symbols, format_author_block, insert_authors_into_doc
        )

        first = state.get("_author_first", {})
        corresponding = state.get("_author_corresponding", {})
        others = state.get("_author_others_buf", [])
        co_first_names = state.get("_co_first_names", [])

        ordered = [first] + others + ([] if first["name"].strip().lower() == corresponding["name"].strip().lower() else [corresponding])
        aff_to_sym = assign_affiliation_symbols(ordered)
        author_line, aff_block = format_author_block(first, corresponding, others, co_first_names, aff_to_sym)

        state["_author_line"] = author_line
        state["_author_aff_block"] = aff_block
        state["_author_step"] = "confirm"
        save_state(state)

        preview = (
            "## Author Block Preview\n\n"
            f"**{author_line}**\n\n"
            f"{aff_block}\n\n"
            "---\nType `confirm` to insert this into the manuscript, "
            "or `restart` to re-enter all author information."
        )
        _chat(history, user_input, preview)
        return "", history, state

    # ── confirm / restart ─────────────────────────────────────────────────
    if step == "confirm":
        if user_input.strip().lower() == "restart":
            for k in ("_author_step", "_author_first", "_author_corresponding",
                      "_author_others_buf", "_co_first_names", "_author_line", "_author_aff_block"):
                state.pop(k, None)
            state["_author_step"] = "init"
            save_state(state)
            return handle_stage9("", history, state)

        if user_input.strip().lower() in ("confirm", "yes", "y"):
            author_line = state.get("_author_line", "")
            aff_block = state.get("_author_aff_block", "")
            try:
                from stages.stage9_authors import insert_authors_into_doc
                has_toned = (ROOT / "output" / "manuscript_toned.docx").exists()
                filename = "manuscript_toned.docx" if has_toned else "manuscript_draft.docx"
                insert_authors_into_doc(filename, author_line, aff_block)
                state = mark_stage_complete(state, 9)
                save_state(state)
                reply = (
                    f"✅ Authors inserted into `{filename}`.\n\n"
                    "Moving to **Stage 10: Journal Formatting**.\n\n"
                    "Which journal are you targeting?\n"
                    "Examples: `Nature`, `Cell`, `PLOS ONE`, `Journal of Biological Chemistry`"
                )
                _chat(history, user_input, reply)
            except Exception as e:
                _chat(history, user_input, f"❌ Error inserting authors: {e}")
            return "", history, state

        _chat(history, user_input, "Type `confirm` to proceed or `restart` to re-enter author information.")
        return "", history, state

    # Fallback — re-enter init
    state["_author_step"] = "init"
    save_state(state)
    return handle_stage9("", history, state)


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
    with gr.Blocks(title="SciCooker") as app:
        state = gr.State(load_state)

        gr.Markdown("# 📄 SciCooker\nAI-powered peer-reviewed manuscript pipeline")

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
