# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Synthetic Data MCP Server - Enterprise-grade Model Context Protocol server for generating privacy-compliant synthetic datasets for regulated industries (healthcare, finance) with multiple LLM provider support. 

**Primary Features:**
- Ollama integration for 100% local, privacy-first inference (no API keys required)
- Complete PII protection - never retains or outputs original personal data
- Test credit card numbers for safe financial data generation
- DSPy orchestration with automatic provider fallback

## Key Commands

### Development

```bash
# Install development environment
pip install -e ".[dev,healthcare,finance]"

# Run tests
pytest                              # Run all tests
pytest -m unit                     # Unit tests only
pytest -m integration              # Integration tests
pytest -m compliance               # Compliance validation tests
pytest -m privacy                  # Privacy protection tests
pytest --cov=synthetic_data_mcp   # With coverage report

# Code quality
black src/ tests/                 # Format code
isort src/ tests/                 # Sort imports
flake8 src/ tests/                # Linting
mypy src                          # Type checking

# Start MCP server
python -m synthetic_data_mcp.server
synthetic-data-mcp serve --port 3000
```

## Architecture

### Core Structure

- **src/synthetic_data_mcp/**: Main package directory
  - **server.py**: FastMCP server implementation with tool definitions
  - **core/generator.py**: SyntheticDataGenerator with DSPy framework integration
  - **providers/**: LLM provider implementations (OpenAI, Anthropic, Google, Ollama, OpenRouter)
  - **compliance/**: Regulatory framework validators (HIPAA, PCI DSS, SOX, GDPR)
  - **privacy/**: Privacy protection engines (differential privacy, k-anonymity)
  - **database/**: Database connectors for 10+ systems (PostgreSQL, MongoDB, Snowflake, etc.)
  - **ingestion/**: Data ingestion pipeline with pattern analysis
  - **schemas/**: Domain-specific Pydantic models (healthcare, finance)
  - **validation/**: Statistical validation and utility preservation
  - **utils/**: Audit trails and monitoring

### Key Design Patterns

1. **Provider Abstraction**: All LLM providers implement DSPy's LM interface for seamless switching
2. **Tiered Fallback**: Automatic fallback from cloud → local models for resilience
3. **Domain Specialization**: Healthcare and finance modules with compliance validation
4. **Privacy by Design**: Built-in differential privacy and statistical disclosure control
5. **Audit Trail**: Comprehensive logging for regulatory compliance

### MCP Tools

The server exposes these primary tools via FastMCP:

- `generate_synthetic_dataset`: Main generation tool with domain/compliance parameters
- `validate_dataset_compliance`: Validate existing data against frameworks
- `analyze_privacy_risk`: Privacy risk assessment
- `generate_domain_schema`: Create Pydantic schemas
- `benchmark_synthetic_data`: Performance benchmarking
- `ingest_and_learn`: Learn patterns from real data

## Testing Strategy

- **Unit tests**: Individual component testing
- **Integration tests**: Provider and database connector testing  
- **Compliance tests**: Regulatory framework validation
- **Privacy tests**: Privacy guarantee verification
- **Performance tests**: Scalability and speed benchmarks

Test fixtures and mocks are in `tests/conftest.py`. Provider tests use mock responses to avoid API costs.

## LLM Provider Configuration

Priority order (automatically selected):
1. **Local Ollama** (DEFAULT - privacy-first, no costs, no API keys)
2. OpenAI (best performance when Ollama unavailable)
3. Anthropic Claude (reasoning)
4. Google Gemini (cost-effective)
5. OpenRouter (open models)

**Ollama Configuration (Primary Provider):**
- Auto-detects Ollama at `http://localhost:11434`
- Automatically selects best available model (e.g., mistral-small)
- No configuration needed if Ollama is running
- 100% local inference, data never leaves machine

Set environment variables for providers:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`
- `OPENROUTER_API_KEY`
- `OLLAMA_BASE_URL` and `OLLAMA_MODEL`

## Domain-Specific Features

### Healthcare
- HIPAA Safe Harbor validation (18 identifiers)
- FHIR resource generation
- HL7 message formatting
- Clinical trial data synthesis

### Finance
- PCI DSS compliance for payment data
- Transaction pattern modeling
- Basel III regulatory reporting
- Trading data generation

## Performance Considerations

- Caching with Redis/DiskCache for repeated generations
- Batch processing for large datasets
- Async operations throughout
- Connection pooling for databases
- Lazy loading of domain modules

## Security

- JWT authentication for API endpoints
- Field-level encryption for sensitive data
- Audit logging for all operations
- Rate limiting and quota management
- Secrets never logged or exposed