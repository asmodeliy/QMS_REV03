"""Quick local diagnostic: construct LLMService and print info.

Usage:
  python tools/test_llm_local_init.py

This script helps validate that the service can import and initialize a model using the
current environment variables (LLM_BACKEND, LLM_MODEL_PATH, LLM_MODEL_NAME ...).
"""
from __future__ import annotations
import os
import sys
import traceback

# ensure RPMT is importable
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'RPMT'))

try:
    from services import llm_service
except Exception as e:
    print('Failed to import services.llm_service:', e)
    traceback.print_exc()
    sys.exit(2)

print('LLM env:')
for k in ('LLM_BACKEND','LLM_MODEL_PATH','LLM_MODEL_NAME','LLM_MODEL_TYPE','LLM_ALLOW_DOWNLOAD','LLM_DEVICE','LLM_VERBOSE','LLM_N_CTX'):
    print(f'  {k}=', os.environ.get(k))

print('\nConstructing and inspecting the LLM service...')
try:
    info = llm_service.get_info()
    print('Service info:', info)
    print('Loaded model object:', getattr(llm_service, '_model', None))
except Exception as e:
    print('Failed to initialize or inspect LLM service:', e)
    traceback.print_exc()
    sys.exit(1)

print('\nTry a quick sync generation (may be slow):')
try:
    out = llm_service.chat_sync('Hello, say hi briefly', max_tokens=32)
    print('Response:', out)
except Exception as e:
    print('Inference failed:', e)
    traceback.print_exc()
    sys.exit(1)

print('\nAll done.')