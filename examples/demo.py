#!/usr/bin/env python3
"""Example runner script to demonstrate the project structure."""

import sys
import asyncio
from pathlib import Path

# Add src to path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_ai.config import validate_environment, DEFAULT_ANTHROPIC_MODEL
from agentic_ai.utils import validate_api_key

def main():
    """Main function to demonstrate project setup."""
    print("🚀 Agentic AI Project Structure Demo")
    print("=" * 50)

    # Validate environment
    env_status = validate_environment()
    if env_status["valid"]:
        print("✅ Environment configuration is valid")
        try:
            api_key = validate_api_key()
            print("✅ Anthropic API key found")
        except RuntimeError as e:
            print(f"❌ {e}")
            return 1
    else:
        print("❌ Missing environment variables:")
        for var in env_status["missing"]:
            print(f"   - {var}")
        print("\nPlease check your .env file or environment variables.")
        return 1

    print(f"📦 Using model: {DEFAULT_ANTHROPIC_MODEL}")

    print("\n📂 Project Structure:")
    print("   ├── src/agentic_ai/        # Main package")
    print("   ├── examples/              # Example scripts")
    print("   ├── tests/                 # Test files")
    print("   ├── assets/                # Static assets")
    print("   │   ├── images/           # Image files")
    print("   │   └── prompts/          # System prompts")
    print("   └── data/                  # Data files")

    print("\n🎯 Available Examples:")
    examples = [
        ("text_messaging.py", "Basic text-based agent interaction"),
        ("multimodal_messaging.py", "Agent with image processing"),
        ("round_robin_agents.py", "Multiple agents collaboration"),
        ("state_saving.py", "Persistent state management"),
        ("jira_scenario.py", "JIRA integration example"),
    ]

    for example, description in examples:
        print(f"   • python examples/{example:<25} - {description}")

    print(f"\n💡 Try running: python examples/text_messaging.py")
    print(f"   Or use: make run-examples")

    return 0


if __name__ == "__main__":
    sys.exit(main())
