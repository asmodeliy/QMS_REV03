"""Check LLM integration status for this QMS server.

Usage: (on server inside project root)
  python tools/check_llm_setup.py

Outputs:
 - Whether the services.llm_service is present
 - If present, the configured backend and model_path
 - Whether the optional runtime packages (llama_cpp, gpt4all) are importable
 - Helpful next-step commands for fixing common issues
"""
from __future__ import annotations
import os
import sys
import traceback

# ensure we can import RPMT package regardless of cwd: look up two levels from this script
from pathlib import Path
script_root = Path(__file__).resolve().parent.parent
rpmtdir = script_root / 'RPMT'
if rpmtdir.exists():
    sys.path.insert(0, str(rpmtdir))
else:
    # fallback: add project root so `import RPMT` works
    sys.path.insert(0, str(script_root))

print('QMS LLM setup diagnostic')
print('Script root:', script_root)
print('RPMT found:', rpmtdir.exists())
print('CWD:', os.getcwd())
print()

# Env
print('Environment variables:')
for name in ('LLM_BACKEND', 'LLM_MODEL_PATH', 'LLM_N_CTX', 'LLM_MODEL_NAME', 'LLM_MODEL_TYPE', 'LLM_ALLOW_DOWNLOAD', 'LLM_DEVICE', 'LLM_VERBOSE', 'LLM_DISABLE_LLAMA'):
    print(f'  {name}={os.environ.get(name)!r}')
print()

# services.llm_service
try:
    # Try common import styles
    try:
        import services
    except ModuleNotFoundError:
        # Maybe package installed as RPMT; try importing RPMT.services
        try:
            from RPMT import services  # type: ignore
        except Exception:
            raise

    s = getattr(services, 'llm_service', None)
    print('services.llm_service exists:', bool(s))
    if s is None:
        print('  Note: services.llm_service is None. This means the import of llm_service failed at startup and was suppressed.')
    else:
        try:
            print('  Backend:', getattr(s, 'backend', '<unknown>'))
            print('  Model path:', getattr(s, 'model_path', '<unknown>'))
            print('  Model loaded in memory:', getattr(s, '_model', None) is not None)
        except Exception:
            print('  Failed to introspect services.llm_service:')
            traceback.print_exc()
except ModuleNotFoundError:
    print('Failed to import services module: ModuleNotFoundError')
    print('Suggestions:')
    print('  - Run this script from the project root (where RPMT/ is located)')
    print('  - Or set PYTHONPATH to include the project root or RPMT directory')
    print('  - Example: python -c "import sys; sys.path.insert(0,\'RPMT\'); import services; print(\"ok\")"')
    sys.exit(2)
except Exception:
    print('Failed to import services module:')
    traceback.print_exc()
    sys.exit(2)

# Also print LLM_INFO from config if available
try:
    try:
        import core.config as cfg  # when RPMT on sys.path
    except Exception:
        from RPMT.core import config as cfg  # type: ignore
    print('\nLLM_INFO (from config):')
    print(cfg.LLM_INFO)
except Exception:
    print('\nLLM_INFO not available (could not import RPMT.core.config)')

print()
# Attempt to import backends without loading a model
for pkg, name in (('llama_cpp', 'llama-cpp-python (module: llama_cpp)'), ('gpt4all', 'gpt4all')):
    try:
        __import__(pkg)
        print(f'IMPORT OK: {name} (module {pkg})')
    except Exception as e:
        print(f'IMPORT FAIL: {name} (module {pkg}) -> {e.__class__.__name__}: {e}')

print()
print('Quick checks:')
if not getattr(services, 'llm_service', None):
    print('- services.llm_service is not available. Common fixes:')
    print('  - Ensure RPMT/llm_service.py exists on the server and is readable')
    print("  - Ensure no import-time exceptions occur (check server logs for tracebacks on startup)")
    print("  - If you want to use llama-cpp-python, install it: pip install llama-cpp-python")
    print("  - Set environment variables, e.g.:")
    print('      export LLM_BACKEND=llama')
    print('      export LLM_MODEL_PATH=/full/path/to/your_model.gguf')
    print('      export LLM_N_CTX=512')
    print('    Then restart the uvicorn process that runs the app.')
else:
    s = services.llm_service
    if not getattr(s, 'model_path', None):
        print('- LLM service is present but LLM_MODEL_PATH is not set. You will get inference-time errors. Set LLM_MODEL_PATH to a valid model path.')
    else:
        print('- LLM service is present and a model path is configured. If you still get errors, check server logs for inference timeouts or import errors of backend libs.')

print('\nYou can also run the built-in endpoint tester:')
print('  python tools/test_llm_endpoint.py --prompt "Hello"')
