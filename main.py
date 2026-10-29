import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.bootstrap import bootstrap_app


def main():
    """Main entry point for AI Dubbing Studio."""
    app, window = bootstrap_app()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

