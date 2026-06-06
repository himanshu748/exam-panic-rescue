# Development Workflow

Updated: 2026-06-06

This file exists to make the project easy to run, inspect, and judge from common developer tools, including JetBrains/PyCharm, without committing IDE-specific `.idea/` files.

## Fast Local Checks

```bash
python3 -m py_compile app.py study_engine.py scripts/readiness_check.py
python3 -m unittest discover -s tests
python3 scripts/readiness_check.py
```

Expected readiness smoke:

```text
biology panic: 7/7
physics numericals: 7/7
history long answers: 7/7
math traps: 7/7

Readiness smoke score: 28/28
```

## Local Gradio Smoke

Use fallback mode for fast UI checks without downloading MiniCPM:

```bash
USE_LOCAL_MODEL=0 GRADIO_SERVER_NAME=127.0.0.1 GRADIO_SERVER_PORT=8065 python3 app.py
```

Use the default OpenBMB/MiniCPM path when hardware/network can handle the model:

```bash
USE_LOCAL_MODEL=1 python3 app.py
```

On Hugging Face CPU-only hardware, the app defaults to the deterministic fallback unless `USE_LOCAL_MODEL=1` is explicitly set. This prevents the live demo from timing out while still preserving the OpenBMB path for upgraded hardware or local smoke tests.

## Hugging Face ZeroGPU Smoke

Official ZeroGPU docs require Gradio, the `spaces` package, and `@spaces.GPU` around GPU-dependent functions. The app now decorates the main generation handler with `@spaces.GPU(duration=120)`, while keeping the local fallback decorator for non-HF runs.

Verified live MiniCPM smoke on 2026-06-06:

1. Space hardware was switched from `cpu-basic` to ZeroGPU (`zero-a10g`).
2. Space variables were set: `USE_LOCAL_MODEL=1` and `PRELOAD_TRANSFORMER_MODEL=1`.
3. A sample physics scenario loads successfully, then generates only after the explicit build action.
4. The model note returned exactly `Generated with openbmb/MiniCPM4.1-8B on CUDA/ZeroGPU.`
5. The sanitizer check confirmed no `<think>` tags were present in the returned packet.

## JetBrains/PyCharm Setup

Create three Python run configurations:

| Name | Script/module | Environment | Purpose |
| --- | --- | --- | --- |
| `Exam Panic Rescue - App` | `app.py` | `USE_LOCAL_MODEL=0;GRADIO_SERVER_NAME=127.0.0.1;GRADIO_SERVER_PORT=8065` | Fast local UI smoke. |
| `Exam Panic Rescue - Tests` | module `unittest` args `discover -s tests` | `USE_LOCAL_MODEL=0` | Unit tests. |
| `Exam Panic Rescue - Readiness` | `scripts/readiness_check.py` | `USE_LOCAL_MODEL=0` | Demo-case scoring. |

Do not commit `.idea/` unless the team explicitly decides to version IDE configuration.

## Optional Sponsor Hooks

- OpenBMB default: `MODEL_ID=openbmb/MiniCPM4.1-8B`
- ZeroGPU handler: `spaces>=0.50,<1` with `@spaces.GPU(duration=120)`
- Cohere review: `USE_COHERE_REVIEW=1 COHERE_API_KEY=...`
- llama.cpp runtime: `USE_LLAMA_CPP=1 LLAMA_CPP_MODEL_PATH=/path/to/model.gguf`

Only OpenBMB is part of the default submission story. Optional hooks must be tested before they are claimed in final materials.
