"""Convenience entrypoint: python run_tests.py --target http://127.0.0.1:8000/v1/chat/completions"""

from runner.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
