#!/usr/bin/env python3
"""Quick test runner for the local GPT4All integration (QMSAssistant).

Usage examples:
  # One-off message
  python scripts/test_gpt4all.py --model-path /path/to/models --model-name Phi-3-mini-4k-instruct.Q4_0.gguf --message "Show me active projects"

  # Interactive REPL
  python scripts/test_gpt4all.py --interactive --model-path /path/to/models

Notes:
- Run this from the repository root (Python-Project/RPMT) or ensure the RPMT package is on PYTHONPATH.
- The script will wrap the model.generate() call and print the raw output, plus the high-level assistant response.
"""

import argparse
import os
import sys
import traceback

# Ensure RPMT package directory is on sys.path when running from repo root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RPMT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
if RPMT_DIR not in sys.path:
    sys.path.insert(0, RPMT_DIR)

try:
    from modules.mcp.gpt4all_client import QMSAssistant, GPT4ALL_AVAILABLE
except Exception as e:
    print("Failed to import QMSAssistant from modules.mcp.gpt4all_client:", e)
    traceback.print_exc()
    sys.exit(1)


def run_one(assistant: QMSAssistant, message: str):
    # show what the assistant will see as the prompt (approximation)
    try:
        # Build the prompt similar to chat()
        system = assistant._create_system_prompt()
        conv_hist = ""
        for msg in assistant.conversation_history[-5:]:
            conv_hist += f"{msg['role']}: {msg['content']}\n"
        prompt_preview = system + "\n\nConversation:\n" + conv_hist + "assistant: "
        print('\n--- Prompt preview (truncated) ---')
        print(prompt_preview[:2000])
        print('--- end prompt preview ---\n')
    except Exception:
        print('[WARN] Could not build prompt preview')

    # wrap model.generate to print raw output
    if assistant.model is None:
        print('[INFO] Model is not loaded (loading now)')
        assistant.load_model()

    orig_generate = None
    try:
        orig_generate = assistant.model.generate
    except Exception:
        print('[WARN] assistant.model has no generate attribute or model not loaded')

    if orig_generate:
        def wrapped_generate(*args, **kwargs):
            print('[DEBUG] model.generate called with kwargs:', {k: v for k, v in kwargs.items() if k != 'prompt'})
            raw = orig_generate(*args, **kwargs)
            print('[DEBUG] Raw model output start ---')
            try:
                print(raw[:4000])
            except Exception:
                print(raw)
            print('[DEBUG] Raw model output end ---')
            return raw
        assistant.model.generate = wrapped_generate

    # Chat
    try:
        resp = assistant.chat(message)
        print('\n=== Assistant response ===')
        print(resp)
        print('=== end response ===\n')
    except Exception as e:
        print('Error while running assistant.chat:', e)
        traceback.print_exc()
    finally:
        # restore original generate if possible
        if orig_generate and assistant.model:
            assistant.model.generate = orig_generate


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model-path', help='Path to folder containing model files', default=os.environ.get('GPT4ALL_MODEL_PATH'))
    p.add_argument('--model-name', help='Model filename', default=os.environ.get('GPT4ALL_MODEL_NAME', 'Phi-3-mini-4k-instruct.Q4_0.gguf'))
    p.add_argument('--message', '-m', help='Single message to send (can be repeated)', action='append')
    p.add_argument('--interactive', '-i', help='Interactive REPL mode', action='store_true')
    p.add_argument('--no-load', action='store_true', help='Do not call load_model automatically')
    p.add_argument('--direct', help='Call model.generate directly (debug) - provide a message')
    args = p.parse_args()

    if not GPT4ALL_AVAILABLE:
        print('gpt4all library is not installed. Install with: pip install gpt4all')
        sys.exit(1)

    assistant = QMSAssistant(model_name=args.model_name, model_path=args.model_path)
    if not args.no_load:
        try:
            print(f"Loading model {assistant.model_name} from {assistant.model_path}")
            assistant.load_model()
            print('Model load complete')
        except Exception as e:
            print('Error loading model:', e)
            traceback.print_exc()
            sys.exit(1)

    # direct generate (raw debug)
    if args.direct:
        print('[DEBUG] Calling model.generate directly with message:')
        print(args.direct)
        try:
            if assistant.model is None:
                assistant.load_model()
            raw = assistant.model.generate(args.direct, max_tokens=512, temp=0.5)
            print('\n[RAW repr]')
            try:
                print(repr(raw))
            except Exception:
                print('[RAW repr failed]')
            print('\n[RAW type]', type(raw))
            # try streaming if supported
            if hasattr(assistant.model, 'generate_stream') or hasattr(assistant.model, 'stream'):
                print('\n[INFO] Attempting streaming API (if available)')
                try:
                    if hasattr(assistant.model, 'generate_stream'):
                        for chunk in assistant.model.generate_stream(args.direct, max_tokens=512, temp=0.5):
                            print('[STREAM CHUNK]', repr(chunk))
                    elif hasattr(assistant.model, 'stream'):
                        for chunk in assistant.model.stream(args.direct, max_tokens=512, temp=0.5):
                            print('[STREAM CHUNK]', repr(chunk))
                except Exception as e:
                    print('[STREAM ERROR]', e)
            print('\n[INFO] Now running assistant.chat for comparison...')
            run_one(assistant, args.direct)
        except Exception as e:
            print('[ERROR] direct generate failed:', e)
            import traceback; traceback.print_exc()
        return

    # one-off messages
    if args.message:
        for m in args.message:
            run_one(assistant, m)
        return

    # interactive
    if args.interactive:
        print('Interactive mode. Type `quit` or `exit` to stop. Type `reset` to clear conversation history.')
        try:
            while True:
                try:
                    line = input('\nYou: ').strip()
                except EOFError:
                    break
                if not line:
                    continue
                if line.lower() in ('quit', 'exit', 'q'):
                    break
                if line.lower() == 'reset':
                    assistant.reset_conversation()
                    print('[assistant] conversation reset')
                    continue
                run_one(assistant, line)
        except KeyboardInterrupt:
            print('\nExiting')
        return

    p.print_help()


if __name__ == '__main__':
    main()
