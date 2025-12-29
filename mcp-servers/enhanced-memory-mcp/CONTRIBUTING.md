# Contributing to Enhanced Memory MCP

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help maintain a welcoming community

## Getting Started

### Development Setup

1. **Fork and Clone**
```bash
git clone https://github.com/YOUR_USERNAME/enhanced-memory-mcp.git
cd enhanced-memory-mcp
```

2. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

4. **Run Tests**
```bash
pytest tests/ -v
```

### Running Locally

```bash
# Start Qdrant (required)
docker run -p 6333:6333 qdrant/qdrant

# Run the server
python server.py
```

## Development Workflow

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring
- `test/description` - Test additions

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(search): add hybrid search with RRF fusion
fix(compression): handle edge case for empty entities
docs(api): update search_nodes documentation
test(provenance): add L-Score calculation tests
```

## Pull Request Process

1. **Create Feature Branch**
```bash
git checkout -b feature/my-feature
```

2. **Make Changes**
- Write clean, documented code
- Add tests for new functionality
- Update documentation as needed

3. **Run Quality Checks**
```bash
# Linting
ruff check .

# Type checking
mypy server.py --ignore-missing-imports

# Security scan
bandit -r . -ll

# Tests
pytest tests/ -v --cov=. --cov-report=term-missing
```

4. **Push and Create PR**
```bash
git push origin feature/my-feature
```

5. **PR Requirements**
- Clear description of changes
- Tests passing
- Documentation updated
- No security issues

## Code Standards

### Python Style

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use f-strings for formatting

### Example Code

```python
async def search_entities(
    query: str,
    limit: int = 10,
    score_threshold: float = 0.5
) -> Dict[str, Any]:
    """
    Search for entities matching query.

    Args:
        query: Search query string
        limit: Maximum number of results
        score_threshold: Minimum relevance score

    Returns:
        Dictionary with search results and metadata
    """
    try:
        results = await self.searcher.search(query, limit=limit)
        return {
            "success": True,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {"success": False, "error": str(e)}
```

### Documentation

- Add docstrings to all public functions
- Update API.md for new tools
- Include examples in docstrings

### Testing

- Aim for 80%+ code coverage
- Write unit tests for utilities
- Write integration tests for tools
- Use pytest fixtures for setup

Example test:
```python
import pytest
from server import classify_tier

class TestTierClassification:
    def test_core_tier_system_role(self):
        """System role entities should be classified as core."""
        assert classify_tier("system_role", "any_name") == "core"

    @pytest.mark.parametrize("entity_type,name,expected", [
        ("project", "my_project", "working"),
        ("session", "session_123", "working"),
        ("archive", "old_data", "archive"),
    ])
    def test_tier_classification(self, entity_type, name, expected):
        assert classify_tier(entity_type, name) == expected
```

## Architecture Guidelines

### Module Organization

```
enhanced-memory-mcp/
├── server.py           # Main FastMCP server
├── memory_client.py    # Memory-DB client
├── provenance.py       # L-Score and provenance
├── hybrid_search.py    # Hybrid search implementation
├── agi/               # AGI-specific features
├── sandbox/           # Code execution sandbox
├── tests/             # Test suite
└── docs/              # Documentation
```

### Adding New Tools

1. Create tool function with `@app.tool()` decorator
2. Add comprehensive docstring
3. Include parameter validation
4. Return consistent response format
5. Add tests
6. Update API.md

### Performance Considerations

- Use async/await for I/O operations
- Implement caching for expensive operations
- Batch database operations when possible
- Profile before optimizing

## Reporting Issues

### Bug Reports

Include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error logs/traceback

### Feature Requests

Include:
- Use case description
- Proposed solution
- Alternative approaches considered

## Questions?

- Open a Discussion on GitHub
- Check existing issues first
- Tag maintainers for urgent issues

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
