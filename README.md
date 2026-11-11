# AI Gallery 2.0

Local gallery for AI-generated images **and videos**. It reads prompts, models
and LoRAs straight from the files and keeps itself up to date while you
generate. Version 2.0 is a separate project; the 1.x app is untouched.

```
./run.sh            # http://127.0.0.1:8924
```

Requires `uv`, plus `ffmpeg`/`ffprobe` for video. Node is only needed to
rebuild the interface (`cd frontend && npm install && npm run build`); the
built interface is committed in `frontend/dist`.

## What is new in 2.0

- **Detection without a list of known nodes** (`backend/detect.py`). Any
  string that is a model file (`.safetensors`, `.gguf`, `.ckpt`, …) is found
  wherever it sits and classified by the key, node class and path around it:
  main model, LoRA, VAE, text encoder, upscaler, ControlNet. The main model
  is the loader that feeds the sampler, whatever that loader is called.
- **Files from unknown tools.** Every text chunk, EXIF field and video tag is
  read; JSON is walked by key names, plain text by patterns (`Model: …`,
  `<lora:name:0.8>`). Such files show up like any other, with the tool name
  guessed from the file or shown as "Unknown tool".
- **Model families that learn.** `flux1DevFp8_v10` → FLUX.1,
  `ideogram4_unconditional_fp8` → Ideogram 4, `Wan2_1-T2V` → Wan 2.1. A name
  that matches nothing known teaches the gallery a new family stem (stored in
  the `model_bases` table) which is then recognised inside later file names.
- **Video** (`mp4`, `webm`, `mov`, `mkv`, `m4v`): metadata from container
  tags (ComfyUI SaveVideo, VideoHelperSuite), thumbnail from a frame, preview
  on hover, player in the viewer.
- **New interface** (Svelte 5 + Vite): virtualised grid and masonry, full
  screen viewer with tile-to-viewer transition, filters by family / model /
  LoRA / tool / type / tag, command palette.

## Hidden folders

Open a file and press ⊘ to hide the folder it is in (subfolders included).
Hidden files stay on disk and in the index but are left out of the grid,
counts and filters. Settings (⚙) lists hidden folders with a "Show again"
button, and also manages the folders in the gallery.

## Keys

| Key | Action |
|---|---|
| `Ctrl+K` | Command palette: jump to a model, LoRA, tag or action |
| `/` | Search prompts |
| Arrows, `PageUp/Down`, `Home` | Move in the grid; previous / next in the viewer |
| `Enter` / `Esc` | Open / close the viewer |
| `F` | Favorite |
| `Del` | Move to trash |
| `Ctrl+E` | Copy the file to a folder |
| `Ctrl+C` | Copy the prompt |
| `Ctrl+-` / `Ctrl+=` | Tile size |

Shift+click on ⟳ reads the metadata of every file again (use it after
updating the app). `python reparse.py --force` does the same without the
server.

## Tests

```
.venv/bin/pytest
```
