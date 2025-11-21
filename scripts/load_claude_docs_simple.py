#!/usr/bin/env python3
"""
Load Claude Code Documentation (Simplified)

Fetches key documentation pages and stores them in manageable chunks
"""

import asyncio
import sys
import json
from pathlib import Path
import requests

# Add enhanced-memory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-servers" / "enhanced-memory-mcp"))

# Use direct SQLite instead of memory client to avoid broken pipe
import sqlite3
from datetime import datetime

DB_PATH = Path.home() / ".claude" / "enhanced_memories" / "memory.db"

# Key documentation pages
DOCS = [
    ("Overview", "https://code.claude.com/docs/en/overview.md"),
    ("MCP", "https://code.claude.com/docs/en/mcp.md"),
    ("Hooks", "https://code.claude.com/docs/en/hooks.md"),
    ("Settings", "https://code.claude.com/docs/en/settings.md"),
    ("CLI Reference", "https://code.claude.com/docs/en/cli-reference.md"),
]


def chunk_text(text: str, max_size: int = 3000) -> list:
    """Split text into chunks at paragraph boundaries"""
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = []
    current_size = 0

    for para in paragraphs:
        para_size = len(para)

        if current_size + para_size > max_size and current_chunk:
            # Save current chunk
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_size = para_size
        else:
            current_chunk.append(para)
            current_size += para_size

    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks


def store_in_db(name: str, entity_type: str, observations: list):
    """Store directly in SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create entity
    cursor.execute('''
        INSERT INTO entities (name, entity_type, tier, created_at, last_accessed)
        VALUES (?, ?, 'reference', ?, ?)
    ''', (name, entity_type, datetime.now(), datetime.now()))

    entity_id = cursor.lastrowid

    # Add observations
    for obs in observations:
        cursor.execute('''
            INSERT INTO observations (entity_id, content, created_at)
            VALUES (?, ?, ?)
        ''', (entity_id, obs, datetime.now()))

    conn.commit()
    conn.close()

    print(f"  ✅ Stored entity {entity_id} with {len(observations)} observations")


def main():
    stored = 0

    print("=" * 60)
    print("Loading Claude Code Documentation (Simplified)")
    print("=" * 60)

    for title, url in DOCS:
        print(f"\n📄 {title}")

        try:
            # Fetch content
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            content = response.text

            print(f"  Fetched {len(content)} characters")

            # Chunk content
            chunks = chunk_text(content, max_size=2500)
            print(f"  Split into {len(chunks)} chunks")

            # Store in database
            store_in_db(
                name=f"ClaudeCodeDocs_{title.replace(' ', '_')}",
                entity_type="claude_code_documentation",
                observations=[
                    f"Claude Code Documentation: {title}",
                    f"Source: {url}",
                ] + chunks
            )

            stored += 1

        except Exception as e:
            print(f"  ❌ Error: {e}")

    print("\n" + "=" * 60)
    print(f"✅ Successfully stored {stored}/{len(DOCS)} documentation pages")
    print("=" * 60)


if __name__ == "__main__":
    main()
