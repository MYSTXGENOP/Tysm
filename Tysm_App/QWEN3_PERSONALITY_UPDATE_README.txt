TYSM QWEN3 + DRY MISCHIEF UPDATE

Changes: default local model qwen3:8b; Qwen thinking disabled in Ollama API calls; consolidated core personality; shortened redundant style guidance.

Original ZIP content (including memory/history, animations, audio, settings, scripts) preserved. Only four active files changed: assistant.py, tysm_personality.txt, tysm_voice.py, tysm_providers.py.

HOW TO USE: Back up your existing Tysm folder. Extract this ZIP and launch the active Tysm_Updated/assistant.py as usual. The ZIP preserves the original nested folder layout. If you previously set TYSM_OLLAMA_MODEL in your environment, it overrides the new default; set it to qwen3:8b or remove the override.

TEST: Start Ollama, launch Tysm, ask a simple question. Check Task Manager memory usage. To switch back temporarily, set environment variable TYSM_OLLAMA_MODEL=llama3.2:3b before launching, or restore your backup.

This patch was syntax-checked but not run on your Windows computer.
