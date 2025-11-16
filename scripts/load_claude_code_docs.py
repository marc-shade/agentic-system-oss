#!/usr/bin/env python3
"""
Load Complete Claude Code Documentation into Enhanced Memory

Fetches all 40+ documentation pages from code.claude.com and stores them
in enhanced-memory with contextual enrichment for fast retrieval.

Purpose: Provide Claude Code with complete operational self-awareness
"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import time

# Add enhanced-memory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-servers" / "enhanced-memory-mcp"))

from memory_client import MemoryClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Documentation pages organized by category
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
        ("Migration Guide", "https://code.claude.com/docs/en/migration-guide.md"),
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


def fetch_documentation_page(url: str) -> str:
    """
    Fetch a documentation page from code.claude.com

    Args:
        url: URL of the documentation page

    Returns:
        Markdown content of the page
    """
    try:
        logger.info(f"Fetching {url}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # The URL returns markdown directly
        content = response.text

        logger.info(f"✅ Fetched {len(content)} characters")
        return content

    except Exception as e:
        logger.error(f"❌ Failed to fetch {url}: {e}")
        return None


def parse_markdown_into_sections(content: str, title: str) -> List[str]:
    """
    Parse markdown content into logical sections for storage

    Args:
        content: Markdown content
        title: Page title

    Returns:
        List of section strings
    """
    sections = []

    # Split by major headers (##)
    lines = content.split('\n')
    current_section = []
    current_header = title

    for line in lines:
        if line.startswith('## '):
            # Save previous section
            if current_section:
                section_text = '\n'.join(current_section).strip()
                if section_text:
                    sections.append(f"{current_header}\n\n{section_text}")

            # Start new section
            current_header = line.replace('## ', '').strip()
            current_section = []
        else:
            current_section.append(line)

    # Save last section
    if current_section:
        section_text = '\n'.join(current_section).strip()
        if section_text:
            sections.append(f"{current_header}\n\n{section_text}")

    return sections if sections else [content]  # Return full content if no sections found


async def store_documentation():
    """Main function to fetch and store all documentation"""

    client = MemoryClient()

    total_pages = sum(len(pages) for pages in DOCUMENTATION_PAGES.values())
    processed = 0
    stored = 0
    failed = 0

    logger.info("=" * 60)
    logger.info(f"Loading {total_pages} Claude Code Documentation Pages")
    logger.info("=" * 60)

    for category, pages in DOCUMENTATION_PAGES.items():
        logger.info(f"\n📁 Category: {category} ({len(pages)} pages)")

        for title, url in pages:
            processed += 1
            logger.info(f"\n[{processed}/{total_pages}] {title}")

            # Fetch page content
            content = fetch_documentation_page(url)

            if not content:
                failed += 1
                continue

            # Parse into sections
            sections = parse_markdown_into_sections(content, title)
            logger.info(f"  Parsed into {len(sections)} sections")

            # Create entity for this documentation page
            entity = {
                "name": f"ClaudeCode_Docs_{category.replace(' ', '_')}_{title.replace(' ', '_')}",
                "entityType": "documentation",
                "observations": [
                    f"Documentation page: {title}",
                    f"Category: {category}",
                    f"URL: {url}",
                    f"Sections: {len(sections)}",
                ] + sections  # Add all content sections as observations
            }

            # Store in enhanced-memory (will auto-enrich with contextual prefix)
            try:
                result = await client.create_entities([entity])

                if result.get("success"):
                    stored += 1
                    enrichment = result.get("contextual_enrichment", {})
                    logger.info(f"  ✅ Stored with {enrichment.get('enriched', 0)} contextual prefix")
                else:
                    failed += 1
                    logger.error(f"  ❌ Failed: {result.get('error')}")

            except Exception as e:
                failed += 1
                logger.error(f"  ❌ Error storing: {e}")

            # Rate limiting - be nice to the server
            time.sleep(0.5)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("DOCUMENTATION LOADING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total pages: {total_pages}")
    logger.info(f"✅ Stored: {stored}")
    logger.info(f"❌ Failed: {failed}")
    logger.info(f"📊 Success rate: {(stored/total_pages)*100:.1f}%")

    # Create index entity
    index_entity = {
        "name": "ClaudeCode_Documentation_Index",
        "entityType": "documentation_index",
        "observations": [
            f"Complete Claude Code documentation loaded on {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total pages: {total_pages}",
            f"Successfully stored: {stored}",
            f"Categories: {', '.join(DOCUMENTATION_PAGES.keys())}",
            "Purpose: Operational self-awareness for Claude Code",
            "Usage: Search with queries like 'how do I use hooks' or 'MCP server configuration'",
        ]
    }

    await client.create_entities([index_entity])
    logger.info("\n✅ Documentation index created")


if __name__ == "__main__":
    asyncio.run(store_documentation())
