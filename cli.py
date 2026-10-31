"""Interactive CLI terminal for Empório da Música AI Agent.

Allows testing conversational customer queries, debugging hierarchical intent
routing, and inspecting internal RAG / SQL context.
"""

from __future__ import annotations

import argparse
import sys
import time

from src.agent import get_agent, memory
from src.database import DEFAULT_DB_PATH, init_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Empório da Música — AI Agent Interactive CLI")
    parser.add_argument("--debug", action="store_true", help="Print debug information (intent, latency, memory)")
    parser.add_argument("--session", type=str, default="cli_session", help="Custom session ID")
    parser.add_argument("--init-db", action="store_true", help="Re-initialize database before starting")
    args = parser.parse_args()

    if args.init_db or not DEFAULT_DB_PATH.exists():
        print("Initializing database...")
        init_db()

    agent = get_agent()

    banner = """
======================================================================
  🎵 Empório da Música — AI Customer Service Agent CLI
  Localização: Rua 14 de Maio, 3200 — Centro, Campo Grande - MS
  Comandos: 'sair' ou 'exit' para encerrar | 'limpar' para resetar
======================================================================
"""
    print(banner)

    while True:
        try:
            user_input = input("\n[Você] > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAté logo!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["sair", "exit", "quit"]:
            print("Atendimento encerrado. Até breve!")
            break

        if user_input.lower() in ["limpar", "clear", "reset"]:
            memory.clear(args.session)
            print(f"Sessão '{args.session}' resetada.")
            continue

        t0 = time.time()
        intent = agent.classify_intent(user_input)

        if args.debug:
            print(f"\n[DEBUG] Intent Classificado: {intent}")

        response = agent.chat(user_input, session_id=args.session)
        elapsed = time.time() - t0

        print(f"\n[Empório da Música] > {response}")

        if args.debug:
            print(f"[DEBUG] Tempo de resposta: {elapsed:.2f}s | Turnos em memória: {len(memory.get_messages(args.session)) // 2}")


if __name__ == "__main__":
    main()
