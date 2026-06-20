from assistant.cli.repl import repl
from assistant.config.settings import load_settings


def main() -> None:
    """Composition root — load config and start the REPL."""
    settings = load_settings()
    repl(settings)


if __name__ == "__main__":
    main()
