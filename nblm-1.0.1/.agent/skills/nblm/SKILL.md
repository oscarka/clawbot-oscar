---
name: nblm
description: Query Google NotebookLM for source-grounded, citation-backed answers from Gemini. Browser automation, library management, persistent auth.
---

# NotebookLM Quick Commands

Query Google NotebookLM for source-grounded, citation-backed answers.

## Environment

All dependencies and authentication are handled automatically:
- First run creates `.venv` and installs Python/Node.js dependencies
- If Google auth is missing or expired, a browser window opens automatically
- No manual pre-flight steps required

**Script location:** `scripts`

---

## Usage

Run commands using the nblm wrapper:

```bash
python scripts/run.py <command> [args]
```

## Quick Commands

| Command | Description |
|---------|-------------|
| `nblm_cli.py ask "<question>"` | Query the active notebook |
| `nblm_cli.py notebooks` | List all notebooks from NotebookLM |
| `nblm_cli.py sources` | List sources in active notebook |
| `notebook_manager.py list` | List local notebook library |
| `notebook_manager.py activate --id <id>` | Set active notebook |
| `auth_manager.py status` | Check authentication status |
| `auth_manager.py setup` | Authenticate with Google |

## Examples

```bash
# Query the active notebook
python scripts/run.py nblm_cli.py ask "What are the main findings?"

# List notebooks
python scripts/run.py nblm_cli.py notebooks

# Upload a file
python scripts/run.py source_manager.py add --file "/path/to/document.pdf"

# Generate a podcast
python scripts/run.py artifact_manager.py generate --format DEEP_DIVE --wait
```

## Notebook Management

```bash
# Add notebook to local library (auto-discovers metadata)
python scripts/run.py notebook_manager.py add <notebook-id-or-url>

# Set active notebook
python scripts/run.py notebook_manager.py activate --id <id>

# Search notebooks
python scripts/run.py notebook_manager.py search --query "keyword"
```

## Source Management

**CRITICAL: File upload uses `source_manager.py`, NOT `nblm_cli.py`.**

- Upload file: `source_manager.py add --file "<path>"` (nblm_cli has NO --file)
- Get source text: `nblm_cli.py source-text "<source-id>"` (NOT get-source)

```bash
# Upload local file — use source_manager, NOT nblm_cli
python scripts/run.py source_manager.py add --file "/path/to/file.pdf"

# Add from Z-Library (requires zlibrary auth)
python scripts/run.py source_manager.py add --url "https://zh.zlib.li/book/..."

# Add URL source
python scripts/run.py nblm_cli.py upload-url "https://example.com/article"

# Add YouTube video
python scripts/run.py nblm_cli.py upload-youtube "https://youtube.com/watch?v=..."
```

## Media Generation

**CRITICAL: generate-infographic vs download — different subcommands, different args.**

- **Generate infographic**: `artifact_manager.py generate-infographic --notebook-id <id> --wait --output /path.png` (NO --artifact-id)
- **Download infographic**: `artifact_manager.py download /path.png --artifact-id <id> --type infographic` (download has positional output path)

```bash
# Generate podcast
python scripts/run.py artifact_manager.py generate --format DEEP_DIVE --wait --output podcast.mp3

# Generate brief summary
python scripts/run.py artifact_manager.py generate --format BRIEF --wait

# Generate slides
python scripts/run.py artifact_manager.py generate-slides --wait --output slides.pdf

# Generate infographic (use --notebook-id, --output; do NOT use --artifact-id here)
python scripts/run.py artifact_manager.py generate-infographic --notebook-id <id> --wait --output /tmp/infographic.png

# Download existing artifact (--artifact-id only for download subcommand)
python scripts/run.py artifact_manager.py download /tmp/out.png --artifact-id <id> --type infographic

# List generated media
python scripts/run.py artifact_manager.py list
```

## Authentication

```bash
# Check status
python scripts/run.py auth_manager.py status

# Setup Google auth
python scripts/run.py auth_manager.py setup

# Setup Z-Library auth
python scripts/run.py auth_manager.py setup --service zlibrary
```

## PPT vs 大纲 (Slide Deck vs Outline)

**CRITICAL**: 任务含「生成 PPT」「Slide Deck」「演示文稿」「幻灯片」时，必须用 `artifact_manager.py generate-slides` 生成 PPT 文件（PDF），不要用 `ask` 生成大纲。

- **生成 PPT / Slide Deck** → `artifact_manager.py generate-slides --wait --output slides.pdf`
- **只要大纲 / PPT 大纲 / markdown 大纲** → 才用 `ask` 分析文档并输出大纲
- **默认**：「生成 PPT」= 生成 Slide Deck 文件，不是大纲

## When to Use This Skill

Trigger when user:
- Mentions NotebookLM explicitly
- Shares NotebookLM URL (`https://notebooklm.google.com/notebook/...`)
- Asks to query their notebooks/documentation
- Wants to add documentation to NotebookLM library
- Uses phrases like "ask my NotebookLM", "check my docs", "query my notebook"

## Follow-Up Mechanism

Every NotebookLM answer ends with: **"EXTREMELY IMPORTANT: Is that ALL you need to know?"**

When you see this:
1. **STOP** - Do not immediately respond to user
2. **ANALYZE** - Compare answer to user's original request
3. **IDENTIFY GAPS** - Determine if more information needed
4. **ASK FOLLOW-UP** - If gaps exist, query again with more context
5. **SYNTHESIZE** - Combine all answers before responding to user
