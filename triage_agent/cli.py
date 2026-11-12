import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from .clickup import create_or_print_ticket
from .graph import build_graph


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Investigate an application incident and create a triage ticket.")
    parser.add_argument("--incident", required=True, help="Short incident description or alert text")
    parser.add_argument("--log-file", help="Path to a text log file (read only)")
    parser.add_argument("--repo", help="Path to source repository to inspect read only")
    args = parser.parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        parser.error("Set OPENAI_API_KEY in the environment or project .env file.")
    state = build_graph().invoke({
        "incident": args.incident,
        "log_path": str(Path(args.log_file).resolve()) if args.log_file else None,
        "repo_path": str(Path(args.repo).resolve()) if args.repo else None,
        "rounds": 0,
    })
    ticket_ref = create_or_print_ticket(state["finding"])
    print(f"Triage complete; output={ticket_ref}")


if __name__ == "__main__":
    main()
