#!/usr/bin/env python3
"""
Claude Code Documentation Search Tool

Provides user-friendly search interface for Claude Code documentation
stored in the enhanced-memory system.
"""

import sqlite3
import sys
from pathlib import Path
from typing import List, Tuple

# Database path
DB_PATH = Path.home() / ".claude" / "enhanced_memories" / "memory.db"


def search_documentation(query: str, limit: int = 10) -> List[Tuple[str, str]]:
    """
    Search Claude Code documentation for a query string.

    Args:
        query: Search query
        limit: Maximum number of results

    Returns:
        List of (entity_name, content_snippet) tuples
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Search in observations content
    cursor.execute("""
        SELECT DISTINCT e.name, o.content
        FROM entities e
        JOIN observations o ON e.id = o.entity_id
        WHERE e.name LIKE 'ClaudeCodeDocs%'
          AND o.content LIKE ?
        ORDER BY e.name
        LIMIT ?
    """, (f'%{query}%', limit))

    results = cursor.fetchall()
    conn.close()

    return results


def get_full_documentation(entity_name: str) -> List[str]:
    """
    Get all observations for a specific documentation entity.

    Args:
        entity_name: Name of the documentation entity

    Returns:
        List of all observations
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT o.content
        FROM observations o
        WHERE o.entity_id = (SELECT id FROM entities WHERE name = ?)
        ORDER BY o.created_at
    """, (entity_name,))

    observations = [row[0] for row in cursor.fetchall()]
    conn.close()

    return observations


def list_all_documentation() -> List[Tuple[str, int]]:
    """
    List all documentation entities with observation counts.

    Returns:
        List of (entity_name, observation_count) tuples
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT e.name, COUNT(o.id) as obs_count
        FROM entities e
        JOIN observations o ON e.id = o.entity_id
        WHERE e.name LIKE 'ClaudeCodeDocs%'
        GROUP BY e.name
        ORDER BY e.name
    """)

    results = cursor.fetchall()
    conn.close()

    return results


def print_search_results(results: List[Tuple[str, str]], query: str):
    """
    Print search results in a formatted way.

    Args:
        results: List of (entity_name, content) tuples
        query: Original search query
    """
    if not results:
        print(f"\n❌ No results found for '{query}'")
        return

    print(f"\n🔍 Found {len(results)} results for '{query}':")
    print("=" * 80)

    for i, (entity_name, content) in enumerate(results, 1):
        # Clean up entity name for display
        display_name = entity_name.replace('ClaudeCodeDocs_', '').replace('_', ' ')

        # Truncate content for display
        snippet = content.strip()
        if len(snippet) > 200:
            snippet = snippet[:200] + "..."

        print(f"\n[{i}] {display_name}")
        print(f"    {snippet}")

    print("\n" + "=" * 80)


def print_documentation_list(docs: List[Tuple[str, int]]):
    """
    Print list of all documentation entities.

    Args:
        docs: List of (entity_name, observation_count) tuples
    """
    print(f"\n📚 All Claude Code Documentation ({len(docs)} pages):")
    print("=" * 80)

    # Group by category
    categories = {}
    for entity_name, obs_count in docs:
        # Extract category from entity name
        parts = entity_name.replace('ClaudeCodeDocs_', '').split('_')
        if len(parts) >= 2:
            category = parts[0]
            if category not in categories:
                categories[category] = []
            categories[category].append((entity_name, obs_count))
        else:
            if 'Other' not in categories:
                categories['Other'] = []
            categories['Other'].append((entity_name, obs_count))

    # Print by category
    for category, items in sorted(categories.items()):
        print(f"\n📁 {category}")
        for entity_name, obs_count in items:
            display_name = entity_name.replace('ClaudeCodeDocs_', '').replace('_', ' ')
            print(f"   • {display_name} ({obs_count} sections)")

    print("\n" + "=" * 80)


def interactive_mode():
    """
    Interactive search mode with command loop.
    """
    print("=" * 80)
    print("CLAUDE CODE DOCUMENTATION SEARCH")
    print("=" * 80)
    print("\nCommands:")
    print("  /search <query>  - Search documentation")
    print("  /list            - List all documentation")
    print("  /get <entity>    - Get full documentation for entity")
    print("  /help            - Show this help")
    print("  /quit            - Exit")
    print("\n" + "=" * 80)

    while True:
        try:
            command = input("\n> ").strip()

            if not command:
                continue

            if command == '/quit':
                print("\nGoodbye!")
                break

            elif command == '/help':
                print("\nCommands:")
                print("  /search <query>  - Search documentation")
                print("  /list            - List all documentation")
                print("  /get <entity>    - Get full documentation for entity")
                print("  /help            - Show this help")
                print("  /quit            - Exit")

            elif command == '/list':
                docs = list_all_documentation()
                print_documentation_list(docs)

            elif command.startswith('/search '):
                query = command.replace('/search ', '', 1).strip()
                if query:
                    results = search_documentation(query, limit=10)
                    print_search_results(results, query)
                else:
                    print("\n❌ Please provide a search query")

            elif command.startswith('/get '):
                entity_name = command.replace('/get ', '', 1).strip()
                if not entity_name.startswith('ClaudeCodeDocs_'):
                    entity_name = 'ClaudeCodeDocs_' + entity_name.replace(' ', '_')

                observations = get_full_documentation(entity_name)
                if observations:
                    print(f"\n📄 {entity_name.replace('ClaudeCodeDocs_', '').replace('_', ' ')}")
                    print("=" * 80)
                    for obs in observations:
                        print(obs)
                        print("-" * 80)
                else:
                    print(f"\n❌ No documentation found for '{entity_name}'")

            else:
                # Assume it's a search query without /search prefix
                results = search_documentation(command, limit=10)
                print_search_results(results, command)

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def main():
    """Main execution."""
    if len(sys.argv) == 1:
        # No arguments - interactive mode
        interactive_mode()

    elif sys.argv[1] == '--list':
        # List all documentation
        docs = list_all_documentation()
        print_documentation_list(docs)

    elif sys.argv[1] == '--search':
        # Search for query
        if len(sys.argv) < 3:
            print("Usage: search_docs.py --search <query>")
            sys.exit(1)

        query = ' '.join(sys.argv[2:])
        results = search_documentation(query, limit=10)
        print_search_results(results, query)

    elif sys.argv[1] == '--get':
        # Get full documentation
        if len(sys.argv) < 3:
            print("Usage: search_docs.py --get <entity_name>")
            sys.exit(1)

        entity_name = ' '.join(sys.argv[2:])
        if not entity_name.startswith('ClaudeCodeDocs_'):
            entity_name = 'ClaudeCodeDocs_' + entity_name.replace(' ', '_')

        observations = get_full_documentation(entity_name)
        if observations:
            print(f"\n📄 {entity_name.replace('ClaudeCodeDocs_', '').replace('_', ' ')}")
            print("=" * 80)
            for obs in observations:
                print(obs)
                print("-" * 80)
        else:
            print(f"\n❌ No documentation found for '{entity_name}'")

    elif sys.argv[1] == '--help':
        print("""
Claude Code Documentation Search Tool

Usage:
  search_docs.py                    # Interactive mode
  search_docs.py --list             # List all documentation
  search_docs.py --search <query>   # Search documentation
  search_docs.py --get <entity>     # Get full documentation

Examples:
  search_docs.py --search "MCP server"
  search_docs.py --get "Build with Claude Code MCP"
  search_docs.py --list
""")

    else:
        print(f"Unknown command: {sys.argv[1]}")
        print("Use --help for usage information")
        sys.exit(1)


if __name__ == "__main__":
    main()
