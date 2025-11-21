#!/usr/bin/env python3
"""
Complete Claude Code Documentation Loader

Loads ALL 44 Claude Code documentation pages with proper handling of:
- Special characters and escaping
- Large documents
- Rate limiting
- Error recovery
"""

import sqlite3
import requests
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple

# Database path
DB_PATH = Path.home() / ".claude" / "enhanced_memories" / "memory.db"

# All 44 documentation pages
DOCUMENTATION_PAGES = {
    "Getting Started": [
        ("Overview", "https://code.claude.com/docs/en/overview.md"),
        ("Quickstart", "https://code.claude.com/docs/en/quickstart.md"),
        ("Common Workflows", "https://code.claude.com/docs/en/common-workflows.md"),
        ("Claude Code on the Web", "https://code.claude.com/docs/en/claude-code-on-the-web.md"),
    ],
    "Build with Claude Code": [
        ("Sub-agents", "https://code.claude.com/docs/en/sub-agents.md"),
        ("Plugins", "https://code.claude.com/docs/en/plugins.md"),
        ("Skills", "https://code.claude.com/docs/en/skills.md"),
        ("Output Styles", "https://code.claude.com/docs/en/output-styles.md"),
        ("Hooks Guide", "https://code.claude.com/docs/en/hooks-guide.md"),
        ("Headless", "https://code.claude.com/docs/en/headless.md"),
        ("GitHub Actions", "https://code.claude.com/docs/en/github-actions.md"),
        ("GitLab CI/CD", "https://code.claude.com/docs/en/gitlab-ci-cd.md"),
        ("MCP", "https://code.claude.com/docs/en/mcp.md"),
        ("Troubleshooting", "https://code.claude.com/docs/en/troubleshooting.md"),
    ],
    "Deployment": [
        ("Third-party Integrations", "https://code.claude.com/docs/en/third-party-integrations.md"),
        ("Amazon Bedrock", "https://code.claude.com/docs/en/amazon-bedrock.md"),
        ("Google Vertex AI", "https://code.claude.com/docs/en/google-vertex-ai.md"),
        ("Network Config", "https://code.claude.com/docs/en/network-config.md"),
        ("LLM Gateway", "https://code.claude.com/docs/en/llm-gateway.md"),
        ("Dev Container", "https://code.claude.com/docs/en/devcontainer.md"),
        ("Sandboxing", "https://code.claude.com/docs/en/sandboxing.md"),
    ],
    "Administration": [
        ("Setup", "https://code.claude.com/docs/en/setup.md"),
        ("IAM", "https://code.claude.com/docs/en/iam.md"),
        ("Security", "https://code.claude.com/docs/en/security.md"),
        ("Data Usage", "https://code.claude.com/docs/en/data-usage.md"),
        ("Monitoring Usage", "https://code.claude.com/docs/en/monitoring-usage.md"),
        ("Costs", "https://code.claude.com/docs/en/costs.md"),
        ("Analytics", "https://code.claude.com/docs/en/analytics.md"),
        ("Plugin Marketplaces", "https://code.claude.com/docs/en/plugin-marketplaces.md"),
    ],
    "Configuration": [
        ("Settings", "https://code.claude.com/docs/en/settings.md"),
        ("VS Code", "https://code.claude.com/docs/en/vs-code.md"),
        ("JetBrains", "https://code.claude.com/docs/en/jetbrains.md"),
        ("Terminal Config", "https://code.claude.com/docs/en/terminal-config.md"),
        ("Model Config", "https://code.claude.com/docs/en/model-config.md"),
        ("Memory", "https://code.claude.com/docs/en/memory.md"),
        ("Status Line", "https://code.claude.com/docs/en/statusline.md"),
    ],
    "Reference": [
        ("CLI Reference", "https://code.claude.com/docs/en/cli-reference.md"),
        ("Interactive Mode", "https://code.claude.com/docs/en/interactive-mode.md"),
        ("Slash Commands", "https://code.claude.com/docs/en/slash-commands.md"),
        ("Checkpointing", "https://code.claude.com/docs/en/checkpointing.md"),
        ("Hooks", "https://code.claude.com/docs/en/hooks.md"),
        ("Plugins Reference", "https://code.claude.com/docs/en/plugins-reference.md"),
    ],
    "Resources": [
        ("Legal and Compliance", "https://code.claude.com/docs/en/legal-and-compliance.md"),
    ],
}


def safe_chunk_text(text: str, max_chunk_size: int = 2000) -> List[str]:
    """
    Safely chunk text at paragraph boundaries with proper handling.

    Args:
        text: Text to chunk
        max_chunk_size: Maximum size per chunk

    Returns:
        List of text chunks
    """
    # Split by double newlines (paragraphs)
    paragraphs = text.split('\n\n')

    chunks = []
    current_chunk = []
    current_size = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_size = len(para)

        # If single paragraph is too large, split by sentences
        if para_size > max_chunk_size:
            sentences = re.split(r'([.!?]\s+)', para)
            for sentence in sentences:
                if not sentence.strip():
                    continue

                if current_size + len(sentence) > max_chunk_size and current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = [sentence]
                    current_size = len(sentence)
                else:
                    current_chunk.append(sentence)
                    current_size += len(sentence)
        else:
            # Normal paragraph handling
            if current_size + para_size > max_chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size

    # Add remaining chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks


def entity_exists(name: str) -> bool:
    """Check if entity already exists in database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM entities WHERE name = ?', (name,))
    exists = cursor.fetchone()[0] > 0
    conn.close()
    return exists


def store_documentation_page(
    name: str,
    category: str,
    url: str,
    content: str,
    skip_if_exists: bool = True
) -> Tuple[bool, str]:
    """
    Store a documentation page in the database.

    Args:
        name: Entity name
        category: Documentation category
        url: Source URL
        content: Page content
        skip_if_exists: Skip if entity already exists

    Returns:
        (success, message) tuple
    """
    entity_name = f"ClaudeCodeDocs_{category.replace(' ', '_')}_{name.replace(' ', '_')}"

    # Check if already exists
    if skip_if_exists and entity_exists(entity_name):
        return (True, f"Already exists (skipped)")

    try:
        # Chunk content
        chunks = safe_chunk_text(content, max_chunk_size=2000)

        # Open database connection
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create entity
        cursor.execute('''
            INSERT INTO entities (name, entity_type, tier, created_at, last_accessed)
            VALUES (?, ?, 'reference', ?, ?)
        ''', (entity_name, 'claude_code_documentation', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        entity_id = cursor.lastrowid

        # Create observations
        observations = [
            f"Claude Code Documentation: {name}",
            f"Category: {category}",
            f"Source: {url}",
            f"Last Updated: {datetime.now().strftime('%Y-%m-%d')}",
        ] + chunks

        # Insert observations with staggered timestamps
        base_time = datetime.now()
        for i, obs in enumerate(observations):
            # Each observation 1 second apart for proper ordering
            obs_time = (base_time - timedelta(seconds=len(observations) - i)).strftime('%Y-%m-%d %H:%M:%S')

            cursor.execute('''
                INSERT INTO observations (entity_id, content, created_at)
                VALUES (?, ?, ?)
            ''', (entity_id, obs, obs_time))

        conn.commit()
        conn.close()

        return (True, f"Stored {len(observations)} observations (entity {entity_id})")

    except Exception as e:
        return (False, f"Error: {str(e)}")


def fetch_documentation(url: str, retries: int = 3) -> Tuple[bool, str]:
    """
    Fetch documentation from URL with retries.

    Args:
        url: Documentation URL
        retries: Number of retry attempts

    Returns:
        (success, content) tuple
    """
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=30)

            if response.status_code == 404:
                return (False, "404 Not Found")

            response.raise_for_status()
            return (True, response.text)

        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                return (False, str(e))


def main():
    """Main execution function."""
    print("=" * 70)
    print("COMPLETE CLAUDE CODE DOCUMENTATION LOADER")
    print("=" * 70)
    print(f"Database: {DB_PATH}")
    print()

    total_pages = sum(len(pages) for pages in DOCUMENTATION_PAGES.values())
    processed = 0
    stored = 0
    skipped = 0
    failed = 0

    stats = {
        "total_chunks": 0,
        "total_bytes": 0,
    }

    for category, pages in DOCUMENTATION_PAGES.items():
        print(f"\n{'='*70}")
        print(f"📁 Category: {category} ({len(pages)} pages)")
        print(f"{'='*70}")

        for title, url in pages:
            processed += 1
            print(f"\n[{processed}/{total_pages}] {title}")
            print(f"  URL: {url}")

            # Fetch documentation
            success, content = fetch_documentation(url)

            if not success:
                print(f"  ❌ Failed to fetch: {content}")
                failed += 1
                continue

            print(f"  ✅ Fetched {len(content):,} characters")
            stats["total_bytes"] += len(content)

            # Store in database
            success, message = store_documentation_page(
                name=title,
                category=category,
                url=url,
                content=content,
                skip_if_exists=True
            )

            if success:
                if "skipped" in message.lower():
                    print(f"  ⏭️  {message}")
                    skipped += 1
                else:
                    print(f"  ✅ {message}")
                    stored += 1

                    # Extract chunk count from message
                    import re
                    match = re.search(r'(\d+) observations', message)
                    if match:
                        stats["total_chunks"] += int(match.group(1))
            else:
                print(f"  ❌ {message}")
                failed += 1

            # Rate limiting - be nice to the server
            time.sleep(0.5)

    # Final summary
    print("\n" + "=" * 70)
    print("DOCUMENTATION LOADING COMPLETE")
    print("=" * 70)
    print(f"Total pages: {total_pages}")
    print(f"  ✅ Stored: {stored}")
    print(f"  ⏭️  Skipped (already exists): {skipped}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📊 Success rate: {((stored + skipped) / total_pages) * 100:.1f}%")
    print()
    print(f"Total data:")
    print(f"  📦 Observations: {stats['total_chunks']:,}")
    print(f"  💾 Data size: {stats['total_bytes'] / 1024:.1f} KB")
    print("=" * 70)

    # Create/update index
    index_name = "ClaudeCodeDocs_Complete_Index"

    if not entity_exists(index_name):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO entities (name, entity_type, tier, created_at, last_accessed)
            VALUES (?, ?, 'core', ?, ?)
        ''', (index_name, 'documentation_index', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        entity_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO observations (entity_id, content, created_at)
            VALUES (?, ?, ?)
        ''', (entity_id, f"""Complete Claude Code Documentation Index

Loaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total Pages: {total_pages}
Successfully Stored: {stored}
Skipped (existing): {skipped}
Failed: {failed}
Total Observations: {stats['total_chunks']}
Total Data: {stats['total_bytes'] / 1024:.1f} KB

Categories:
{', '.join(DOCUMENTATION_PAGES.keys())}

Purpose: Complete operational self-awareness for Claude Code
Coverage: Installation, configuration, MCP, hooks, CLI, deployment, administration

Search Examples:
- "How do I configure MCP servers?"
- "What are the available hooks?"
- "How to use Claude Code in CI/CD?"
- "Settings.json configuration options"
""", datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        conn.commit()
        conn.close()

        print(f"\n✅ Documentation index created (entity {entity_id})")


if __name__ == "__main__":
    main()
