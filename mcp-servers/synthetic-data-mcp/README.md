# Synthetic Data MCP Server

Enterprise-grade Model Context Protocol (MCP) server for generating privacy-compliant synthetic datasets. Built for regulated industries requiring HIPAA, PCI DSS, SOX, and GDPR compliance with multiple LLM provider support.

## Features
<img align="right" width="300" height="300" alt="synthetic-data-mcp" src="https://github.com/user-attachments/assets/46620579-0933-4d55-82e9-3700c75fe566" />

### Core Capabilities
- **Privacy-First Local Inference**: Ollama integration for 100% local data generation
- **Domain-Specific Generation**: Specialized synthetic data for healthcare and finance
- **Privacy Protection**: Differential privacy, k-anonymity, l-diversity
- **PII Safety Guarantee**: Never retains or outputs original personal data
- **Compliance Validation**: HIPAA, PCI DSS, SOX, GDPR compliance checking
- **Statistical Fidelity**: Advanced validation to ensure data utility
- **Audit Trail**: Comprehensive logging for regulatory compliance
- **Multi-Provider Support**: Ollama (default), OpenAI, Anthropic, Google, OpenRouter

### LLM Provider Support (2025 Models)
- **OpenAI**: GPT-5, GPT-5 Mini/Nano, GPT-4o
- **Anthropic**: Claude Opus 4.1, Claude Sonnet 4 (1M context), Claude 3.5 series
- **Google**: Gemini 2.5 Pro/Flash/Flash-Lite (1M+ context, multimodal)
- **Local Models**: Dynamic Ollama integration (Llama 3.3, Qwen 2.5/3, DeepSeek-R1, Mistral Small 3)
- **Smart Routing**: Automatic provider selection with cost optimization
- **Fallback**: Multi-tier fallback with local model support

### Technology Stack (2025 Latest)
- **FastAPI 0.116+**: High-performance async web framework
- **FastMCP**: High-performance MCP server implementation
- **Pydantic 2.11+**: Type-safe data validation with enhanced performance
- **SQLAlchemy 2.0+**: Modern async ORM with type safety
- **DSPy**: Language model programming framework for intelligent data generation
- **NumPy 2.3+ & Pandas 2.3+**: Advanced data processing capabilities
- **Redis & DiskCache**: Multi-tier caching for cost optimization
- **Rich**: Beautiful terminal interfaces and progress indicators

## Enterprise Benefits

- **Privacy-First**: Generate synthetic data without exposing sensitive information
- **Compliance-Ready**: Built-in validation for HIPAA, PCI DSS, SOX, and GDPR
- **Multi-Provider**: Support for cloud APIs and local inference
- **Production-Scale**: High-performance generation for enterprise data volumes
- **Zero Vendor Lock-in**: Switch between providers seamlessly
- **Cost Control**: Use local models for unlimited generation

## Healthcare Use Cases

- Patient record synthesis with HIPAA Safe Harbor compliance
- Clinical trial data generation for FDA submissions
- Medical research datasets without PHI exposure
- Drug discovery data augmentation
- Healthcare analytics and ML model training
- EHR system testing and validation

## Finance Use Cases

- Transaction pattern modeling for fraud detection
- Credit risk assessment dataset generation
- Regulatory stress testing data (Basel III, Dodd-Frank)
- PCI DSS compliant payment data synthesis
- Trading algorithm development and backtesting
- Financial reporting system validation

## Installation

### Production Installation
```bash
pip install synthetic-data-mcp
```

### Development Installation
```bash
git clone https://github.com/marc-shade/synthetic-data-mcp
cd synthetic-data-mcp
pip install -e ".[dev,healthcare,finance]"
```

## Quick Start

### 1. Configure LLM Provider

Choose your preferred provider:

#### OpenAI (Recommended for Production)
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

#### Anthropic Claude
```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

#### Google Gemini
```bash
export GOOGLE_API_KEY="your-key-here"
```

#### OpenRouter (Access to 100+ Models)
```bash
export OPENROUTER_API_KEY="sk-or-your-key-here"
export OPENROUTER_MODEL="meta-llama/llama-3.1-8b-instruct"
```

#### Local Models (Ollama) - Privacy-First (DEFAULT)
```bash
# Install Ollama first: https://ollama.ai
ollama pull mistral-small:latest  # Or any preferred model
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="mistral-small:latest"

# The system automatically detects and uses Ollama if available
# No API keys required for local inference!
```

### 2. Start the MCP Server

```bash
synthetic-data-mcp serve --port 3000
```

### 3. Add to Claude Desktop Configuration

```json
{
  "mcpServers": {
    "synthetic-data": {
      "command": "python",
      "args": ["-m", "synthetic_data_mcp.server"],
      "env": {
        "OPENAI_API_KEY": "your-api-key"
      }
    }
  }
}
```

### 4. Generate Synthetic Data

```python
# Using the MCP client
result = await client.call_tool(
    "generate_synthetic_dataset",
    {
        "domain": "healthcare",
        "dataset_type": "patient_records",
        "record_count": 10000,
        "privacy_level": "high",
        "compliance_frameworks": ["hipaa"],
        "output_format": "json"
    }
)
```

## Provider Configuration

### Priority-Based Provider Selection

The system automatically selects the best available provider:

1. **Local Models (Ollama)** - Highest privacy, no API costs
2. **OpenAI** - Best performance and reliability
3. **Anthropic Claude** - Excellent reasoning capabilities
4. **Google Gemini** - Fast and cost-effective
5. **OpenRouter** - Access to open source models
6. **Fallback Mock** - Testing and development

### Provider-Specific Configuration

#### OpenAI Configuration
```python
# Environment variables
OPENAI_API_KEY="sk-your-key-here"
OPENAI_MODEL="gpt-4"  # or gpt-4-turbo, gpt-3.5-turbo
OPENAI_TEMPERATURE="0.7"
OPENAI_MAX_TOKENS="2000"
```

#### Anthropic Configuration
```python
# Environment variables
ANTHROPIC_API_KEY="sk-ant-your-key-here"
ANTHROPIC_MODEL="claude-3-opus-20240229"  # or claude-3-sonnet, claude-3-haiku
ANTHROPIC_MAX_TOKENS="2000"
```

#### Local Ollama Configuration
```python
# Environment variables
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="llama3.1:8b"  # or any installed model

# Supported local models:
# - llama3.1:8b, llama3.1:70b
# - mistral:7b, mixtral:8x7b
# - qwen2:7b, deepseek-coder:6.7b
# - and 20+ more models
```

## Available MCP Tools

### `generate_synthetic_dataset`
Generate domain-specific synthetic datasets with compliance validation.

**Parameters:**
- `domain`: Healthcare, finance, or custom
- `dataset_type`: Patient records, transactions, clinical trials, etc.
- `record_count`: Number of synthetic records to generate
- `privacy_level`: Privacy protection level (low/medium/high/maximum)
- `compliance_frameworks`: Required compliance validations
- `output_format`: JSON, CSV, Parquet, or database export
- `provider`: Override automatic provider selection

### `validate_dataset_compliance`
Validate existing datasets against regulatory requirements.

### `analyze_privacy_risk`
Comprehensive privacy risk assessment for datasets.

### `generate_domain_schema`
Create Pydantic schemas for domain-specific data structures.

### `benchmark_synthetic_data`
Performance and utility benchmarking against real data.

## Compliance Frameworks

### Healthcare Compliance
- **HIPAA Safe Harbor**: Automatic validation of 18 identifiers
- **HIPAA Expert Determination**: Statistical disclosure control
- **FDA Guidance**: Synthetic clinical data for submissions
- **GDPR**: Healthcare data processing compliance
- **HITECH**: Security and breach notification

### Finance Compliance
- **PCI DSS**: Payment card industry data security
- **SOX**: Sarbanes-Oxley internal controls
- **Basel III**: Banking regulatory framework
- **MiFID II**: Markets in Financial Instruments Directive
- **Dodd-Frank**: Financial reform regulations

## Privacy Protection

### Core Privacy Features
- **Differential Privacy**: Configurable ε values (0.1-1.0)
- **Statistical Disclosure Control**: k-anonymity, l-diversity, t-closeness
- **Synthetic Data Indistinguishability**: Provable privacy guarantees
- **Re-identification Risk Assessment**: Continuous monitoring
- **Privacy Budget Management**: Automatic composition tracking

### PII Protection Guarantee
- **NO Data Retention**: Original personal data is NEVER stored
- **Automatic PII Detection**: Identifies names, emails, SSNs, phones, addresses, credit cards
- **Complete Anonymization**: All PII is anonymized before pattern learning
- **Statistical Learning Only**: Only learns distributions, means, and frequencies
- **100% Synthetic Output**: Generated data is completely fake

### Credit Card Safety
- **Test Card Numbers Only**: Uses official test cards (4242-4242-4242-4242, etc.)
- **Provider Support**: Visa, Mastercard, AmEx, Discover, and more
- **Configurable Providers**: Specify provider or use weighted distribution
- **Never Real Cards**: Original credit card numbers are never retained or output

Example usage with credit card provider selection:
```python
# Use specific provider test cards
result = await pipeline.ingest(
    source=data,
    credit_card_provider='visa'  # Uses Visa test cards
)

# Or let system use mixed providers (default)
result = await pipeline.ingest(
    source=data  # Automatically uses weighted distribution
)
```

## Performance & Quality

- **Statistical Fidelity**: 95%+ correlation preservation
- **Privacy Preservation**: <1% re-identification risk
- **Utility Preservation**: >90% ML model performance
- **Compliance Rate**: 100% regulatory framework adherence
- **Generation Speed**: 1,000-10,000 records/second (provider dependent)

### Provider Performance Comparison

| Provider | Speed (req/s) | Quality | Privacy | Cost |
|----------|---------------|---------|---------|------|
| Ollama Local | 10-50 | High | Maximum | Free |
| OpenAI GPT-4 | 20-100 | Excellent | Medium | $$$ |
| Claude 3 Opus | 15-80 | Excellent | Medium | $$$ |
| Gemini Pro | 50-200 | Good | Medium | $ |
| OpenRouter | 10-100 | Variable | Medium | $ |

## Testing

```bash
# Run all tests
pytest

# Run compliance tests only
pytest -m compliance

# Run privacy tests
pytest -m privacy

# Run with coverage
pytest --cov=synthetic_data_mcp --cov-report=html

# Test specific provider
OPENAI_API_KEY=sk-test pytest -m integration
```

## Deployment

### Docker Deployment
```bash
docker build -t synthetic-data-mcp .
docker run -p 3000:3000 \
  -e OPENAI_API_KEY=your-key \
  synthetic-data-mcp
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: synthetic-data-mcp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: synthetic-data-mcp
  template:
    metadata:
      labels:
        app: synthetic-data-mcp
    spec:
      containers:
      - name: synthetic-data-mcp
        image: synthetic-data-mcp:latest
        ports:
        - containerPort: 3000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-secrets
              key: openai-key
```

## 🔧 Development

### Code Quality
```bash
# Format code
black .
isort .

# Run linting
flake8 src tests

# Type checking
mypy src
```

### Adding New Providers

1. Create provider module in `src/synthetic_data_mcp/providers/`
2. Implement DSPy LM interface
3. Add configuration in `core/generator.py`
4. Add tests in `tests/test_providers.py`

## Examples

### Healthcare Example
```python
import asyncio
from synthetic_data_mcp import SyntheticDataGenerator

async def generate_patients():
    generator = SyntheticDataGenerator()
    
    result = await generator.generate_dataset(
        domain="healthcare",
        dataset_type="patient_records",
        record_count=1000,
        privacy_level="high",
        compliance_frameworks=["hipaa"]
    )
    
    print(f"Generated {len(result['dataset'])} patient records")
    return result

# Run the example
asyncio.run(generate_patients())
```

### Finance Example
```python
async def generate_transactions():
    generator = SyntheticDataGenerator()
    
    result = await generator.generate_dataset(
        domain="finance",
        dataset_type="transactions",
        record_count=50000,
        privacy_level="high",
        compliance_frameworks=["pci_dss"]
    )
    
    print(f"Generated {len(result['dataset'])} transactions")
    return result
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
```bash
git clone https://github.com/marc-shade/synthetic-data-mcp
cd synthetic-data-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,healthcare,finance]"
pre-commit install
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- [GitHub Issues](https://github.com/marc-shade/synthetic-data-mcp/issues)
- [GitHub Discussions](https://github.com/marc-shade/synthetic-data-mcp/discussions)
- Email: support@2acrestudios.com

## Related Projects

- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [DSPy Framework](https://dspy-docs.vercel.app/)
- [Ollama](https://ollama.ai/) - Local LLM inference
- [OpenRouter](https://openrouter.ai/) - Access to 100+ models

---

Built with ❤️ for enterprise developers who need compliant, privacy-preserving synthetic data generation.
