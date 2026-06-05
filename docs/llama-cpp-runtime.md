# llama.cpp Runtime Plan

Updated: 2026-06-05

Purpose: make the Llama Champion path concrete without forcing heavy runtime dependencies into the default Space.

## Source

Official OpenBMB GGUF repos checked:

- Primary app target: https://huggingface.co/openbmb/MiniCPM4.1-8B-GGUF
- Verified small local smoke target: https://huggingface.co/openbmb/MiniCPM4-0.5B-QAT-Int4-GGUF

The primary repo documents both `llama-cpp-python` and `llama.cpp` usage for `openbmb/MiniCPM4.1-8B-GGUF`. The smaller MiniCPM4 0.5B GGUF is a practical local proof route for the optional `llama.cpp` backend.

## App Defaults

The app's optional llama.cpp backend defaults to:

```bash
LLAMA_CPP_REPO_ID=openbmb/MiniCPM4.1-8B-GGUF
LLAMA_CPP_FILENAME=MiniCPM4.1-8B-Q4_K_M.gguf
```

The app now supports two optional llama.cpp backend routes:

- `LLAMA_CPP_BACKEND=auto` (default): try `llama-cli` first if present, then `llama-cpp-python`.
- `LLAMA_CPP_BACKEND=cli`: require the direct `llama-cli` path.
- `LLAMA_CPP_BACKEND=python`: require `llama-cpp-python`.

Run with direct `llama-cli` if installed:

```bash
USE_LLAMA_CPP=1 \
LLAMA_CPP_BACKEND=cli \
USE_LOCAL_MODEL=1 \
python3 app.py
```

By default, the CLI route uses Hugging Face selector:

```bash
LLAMA_CPP_HF_SELECTOR=Q4_K_M
```

This maps to the official OpenBMB example:

```bash
llama-cli -hf openbmb/MiniCPM4.1-8B-GGUF:Q4_K_M
```

Run with `llama-cpp-python` if installed:

```bash
USE_LLAMA_CPP=1 LLAMA_CPP_BACKEND=python USE_LOCAL_MODEL=1 python3 app.py
```

Run with a local GGUF file:

```bash
USE_LLAMA_CPP=1 \
LLAMA_CPP_MODEL_PATH=/path/to/MiniCPM4.1-8B-Q4_K_M.gguf \
python3 app.py
```

Verified small OpenBMB MiniCPM local-file route:

```bash
hf download openbmb/MiniCPM4-0.5B-QAT-Int4-GGUF \
  MiniCPM4-0.5B-QAT-Int4_gptq_aware_q4_0.gguf \
  --local-dir /private/tmp/openbmb-minicpm4-0.5b-gguf

USE_LOCAL_MODEL=1 \
USE_LLAMA_CPP=1 \
LLAMA_CPP_BACKEND=cli \
LLAMA_CPP_MODEL_PATH=/private/tmp/openbmb-minicpm4-0.5b-gguf/MiniCPM4-0.5B-QAT-Int4_gptq_aware_q4_0.gguf \
LLAMA_CPP_MAX_TOKENS=100 \
LLAMA_CPP_TIMEOUT=90 \
python3 -c "from study_engine import build_rescue_plan; p=build_rescue_plan('Aarav','Physics formulas',90,'Mixed','I panic and forget formulas','work-energy theorem, kinetic energy',2); print(p.model_note); print(p.rescue_plan_markdown[:500])"
```

Optional tuning:

```bash
LLAMA_CPP_N_CTX=2048
LLAMA_CPP_THREADS=4
LLAMA_CPP_N_GPU_LAYERS=0
LLAMA_CPP_MAX_TOKENS=260
LLAMA_CPP_TIMEOUT=120
```

## Direct llama.cpp Smoke

If `llama.cpp` is installed with Homebrew:

```bash
brew install llama.cpp
llama-cli -hf openbmb/MiniCPM4.1-8B-GGUF:Q4_K_M \
  -p "Student has 90 minutes before a physics test and panics on formulas. Give a 4-step rescue plan."
```

Server mode:

```bash
llama-server -hf openbmb/MiniCPM4.1-8B-GGUF:Q4_K_M
```

## Claim Rule

Do not claim Llama Champion until one of these is true:

- `USE_LLAMA_CPP=1 python3 app.py` loads a GGUF path and produces a non-fallback model note.
- `USE_LLAMA_CPP=1 LLAMA_CPP_BACKEND=cli python3 app.py` produces a non-fallback model note that says `Generated locally with llama.cpp CLI`.
- Direct `llama-cli` against an OpenBMB MiniCPM GGUF file produces a usable response and the demo can explain how the app maps to that runtime.
- Internal check passes: `python3 scripts/llama_runtime_check.py`.

The internal check proves runtime/config readiness. It does not replace the non-fallback MiniCPM GGUF generation smoke required for a final Llama Champion claim.

The local OpenBMB MiniCPM4 0.5B GGUF smoke now proves the app can use an OpenBMB MiniCPM-family model through `llama.cpp`. Treat the final Llama Champion submission claim as conditional until the final demo/materials explicitly use or show this route.

## Current Local Status

Checked on 2026-06-05:

- `llama-cli`: installed at `/opt/homebrew/bin/llama-cli`, version `9430`.
- `llama-server`: installed at `/opt/homebrew/bin/llama-server`.
- Python `llama_cpp`: not installed.
- `python3 scripts/llama_runtime_check.py`: passes `9/9`.
- Direct `llama-cli` smoke with `openbmb/MiniCPM4-0.5B-QAT-Int4-GGUF` local file passed and produced usable study text.
- App-level OpenBMB MiniCPM4 0.5B GGUF smoke passed with:

```bash
USE_LOCAL_MODEL=1 \
USE_LLAMA_CPP=1 \
LLAMA_CPP_BACKEND=cli \
LLAMA_CPP_MODEL_PATH=/private/tmp/openbmb-minicpm4-0.5b-gguf/MiniCPM4-0.5B-QAT-Int4_gptq_aware_q4_0.gguf \
LLAMA_CPP_MAX_TOKENS=100 \
LLAMA_CPP_TIMEOUT=90 \
python3 -c "from study_engine import build_rescue_plan; p=build_rescue_plan('Aarav','Physics formulas',90,'Mixed','I panic and forget formulas','work-energy theorem, kinetic energy',2); print(p.model_note)"
```

Result: `Generated locally with llama.cpp CLI model /private/tmp/openbmb-minicpm4-0.5b-gguf/MiniCPM4-0.5B-QAT-Int4_gptq_aware_q4_0.gguf.`

- App-level TinyLlama GGUF smoke passed with:

```bash
USE_LOCAL_MODEL=1 \
USE_LLAMA_CPP=1 \
LLAMA_CPP_BACKEND=cli \
LLAMA_CPP_REPO_ID=TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF \
LLAMA_CPP_HF_SELECTOR=Q2_K \
LLAMA_CPP_MAX_TOKENS=80 \
LLAMA_CPP_TIMEOUT=90 \
python3 -c "from study_engine import build_rescue_plan; p=build_rescue_plan('Aarav','Physics formulas',90,'Mixed','I panic and forget formulas','work-energy theorem, kinetic energy',2); print(p.model_note)"
```

Result: `Generated locally with llama.cpp CLI model TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF:Q2_K.`

- The OpenBMB MiniCPM GGUF file is public but about `4.97GB`. A download attempt was aborted because Hugging Face/Xet duplicated partial cache pressure on a disk with limited free space.
- Direct `llama-cli -hf openbmb/MiniCPM4-0.5B-QAT-Int4-GGUF:MiniCPM4-0.5B-QAT-Int4_gptq_aware_q4_0.gguf ...` failed with `failed to download model from Hugging Face`, so use the local-file route above for this repo.

Safer final claim: optional llama.cpp runtime path is implemented and verified locally with an official OpenBMB MiniCPM4 0.5B GGUF; OpenBMB MiniCPM4.1-8B remains the default non-GGUF model target.
