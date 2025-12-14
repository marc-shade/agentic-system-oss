# Contributing to Synthetic Data MCP

We welcome contributions from the community! This document provides guidelines for contributing to the Synthetic Data MCP server.

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Git
- Basic understanding of synthetic data and privacy concepts

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/marc-shade/synthetic-data-mcp.git
   cd synthetic-data-mcp
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install development dependencies:**
   ```bash
   pip install -e ".[dev,healthcare,finance]"
   ```

4. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

## 🔧 Development Workflow

### Code Style

We use the following tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

Run all checks:
```bash
# Format code
black .
isort .

# Run linting
flake8 src tests

# Type checking
mypy src
```

### Testing

We maintain high test coverage (>80%). Run tests with:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=synthetic_data_mcp --cov-report=html

# Run specific test categories
pytest -m compliance     # Compliance tests
pytest -m privacy        # Privacy tests
pytest -m integration    # Integration tests
```

### Documentation

- Update docstrings for all public functions
- Add examples for new features
- Update README.md if adding major features

## 📋 Contribution Types

### Bug Reports

Please include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, etc.)
- Relevant logs or error messages

### Feature Requests

Please include:
- Clear use case description
- Benefits to the community
- Implementation suggestions (if any)
- Potential breaking changes

### Pull Requests

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Write code following our style guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes:**
   ```bash
   pytest
   pre-commit run --all-files
   ```

4. **Submit pull request:**
   - Clear title and description
   - Reference related issues
   - Include test results

## 🏥 Domain-Specific Contributions

### Healthcare Domain

- Must comply with HIPAA Safe Harbor requirements
- Include appropriate medical terminology validation
- Test with realistic clinical scenarios
- Consider FDA guidance for synthetic clinical data

### Finance Domain

- Must comply with relevant financial regulations (SOX, PCI DSS)
- Include proper risk modeling approaches
- Test with realistic financial scenarios
- Consider regulatory reporting requirements

## 🔒 Security & Privacy

### Security Guidelines

- Never commit API keys or secrets
- Use environment variables for sensitive configuration
- Follow principle of least privilege
- Implement proper input validation
- Review cryptographic implementations carefully

### Privacy Guidelines

- Implement differential privacy correctly
- Validate re-identification risk assessments
- Test privacy preservation mechanisms
- Document privacy parameters and their effects

## 📊 Performance Considerations

- Profile code for performance bottlenecks
- Optimize for large dataset generation
- Consider memory usage patterns
- Test with realistic data volumes
- Document performance characteristics

## 🤝 Community Guidelines

### Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors.

- Be respectful and constructive
- Welcome newcomers and help them learn
- Focus on what is best for the community
- Show empathy towards other community members

### Communication

- Use GitHub Issues for bug reports and feature requests
- Use GitHub Discussions for general questions
- Be clear and concise in communications
- Provide context and examples when helpful

## 🏢 Legal Considerations

### Licensing

- All contributions will be licensed under MIT License
- Ensure you have rights to contribute code
- Do not include copyrighted material without permission

### Compliance

- Understand regulatory implications of changes
- Test compliance validation thoroughly
- Document regulatory considerations
- Consider international regulations (GDPR, etc.)

## 📈 Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):
- MAJOR: Breaking changes
- MINOR: New features (backwards compatible)
- PATCH: Bug fixes (backwards compatible)

### Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version bumped
- [ ] Security review completed
- [ ] Compliance validation passed

## 🆘 Getting Help

- **Documentation**: [Read the Docs](https://synthetic-data-mcp.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/marc-shade/synthetic-data-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/marc-shade/synthetic-data-mcp/discussions)
- **Email**: support@2acrestudios.com

## 🙏 Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to Synthetic Data MCP! 🎉