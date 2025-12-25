# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- **Install Dependencies**: `uv sync`
- **Run App**: `uv run python main.py`
- **Run (Windows VBS)**: `wscript run.vbs` (runs without console)
- **Dependencies**: Requires `xelatex` (TeX Live or MiKTeX) installed and in PATH.

## Architecture

This project is a Math Digitizer that converts structured JSON into professional LaTeX exam papers.

### Core Components
- **Frontend**: `src/gui.py` uses `customtkinter` for a modern GUI.
  - `PremiumExamApp`: Main application window.
  - Handles JSON input, file drag-and-drop, and triggers generation.
- **Backend**: `src/generator.py`.
  - `ExamGenerator`: Logic class.
  - Loads `src/exam_template.txt` (Jinja2 template).
  - Processes JSON (cleans options, handles images).
  - Renders LaTeX to `output/`.
  - Calls `xelatex` subprocess to compile PDF.
- **Validation**: `src/validator.py`.
  - Ensures JSON structure matches the schema required by the template.
- **Prompts**: `src/prompt.md` contains the system prompt for LLMs to generate the required JSON structure.

### Workflow
1. User provides exam content (text/image) to an LLM with `src/prompt.md`.
2. LLM generates JSON.
3. User pastes JSON into GUI or loads file.
4. App validates JSON.
5. `ExamGenerator` creates `.tex` and compiles `.pdf` in `output/`.

### Directory Structure
- `src/`: Source code and assets.
- `output/`: Generated LaTeX and PDF files.
- `main.py`: Entry point, sets up environment and high DPI settings.
