"""
CLI Runner for Free AI Gateway
"""

from __future__ import annotations
import argparse
import sys
import uvicorn
from free_ai.client import FreeAIClient
from free_ai.daemon import ensure_daemon_running


def main():
    parser = argparse.ArgumentParser(description="Free AI Gateway — OpenAI Compatible Server & CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Launch the OpenAI-compatible HTTP proxy gateway")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    serve_parser.add_argument("--port", type=int, default=4097, help="Port to listen on (default: 4097)")

    # Prompt command
    prompt_parser = subparsers.add_parser("prompt", help="Quick one-liner terminal query")
    prompt_parser.add_argument("query", type=str, help="Question or prompt for the model")
    prompt_parser.add_argument("--model", "-m", default="deepseek-v4.1-flash-free", help="Model ID")
    prompt_parser.add_argument("--show-reasoning", "-r", action="store_true", help="Print model's thought process")

    # Status command
    subparsers.add_parser("status", help="Check OpenCode daemon health")

    args = parser.parse_args()

    if args.command == "serve" or args.command is None:
        port = getattr(args, "port", 4097)
        host = getattr(args, "host", "127.0.0.1")
        print("=" * 60)
        print("  ⚡ Free AI Gateway — OpenAI Compatible Proxy")
        print(f"  Base URL:  http://{host}:{port}/v1")
        print("  Models:    deepseek-v4.1-flash-free, nemotron-3.5-super-vl-free")
        print("  Cost:      $0.00 / Zero API Keys Required")
        print("=" * 60)
        ensure_daemon_running()
        from free_ai.gateway import app
        uvicorn.run(app, host=host, port=port, log_level="info")

    elif args.command == "prompt":
        client = FreeAIClient()
        resp = client.chat(args.query, model=args.model)
        if args.show_reasoning and resp.reasoning:
            print("\n--- Reasoning Thought Process ---")
            print(resp.reasoning)
            print("---------------------------------\n")
        print(resp.content)

    elif args.command == "status":
        alive = ensure_daemon_running()
        if alive:
            print("[+] OpenCode daemon is ONLINE and responding at http://127.0.0.1:4096")
        else:
            print("[-] OpenCode daemon is OFFLINE. Unable to locate opencode.exe")


if __name__ == "__main__":
    main()
