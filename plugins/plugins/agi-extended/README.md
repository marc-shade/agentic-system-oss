# AGI-Extended Plugin

Full AGI capabilities with vector memory, research tools, and voice interaction.

## Overview

This plugin extends agi-memory with advanced capabilities:
- **Vector Memory**: Semantic search and RAG with Qdrant
- **Memory Types**: Episodic, semantic, procedural, working
- **Research Integration**: arXiv, Semantic Scholar, YouTube
- **Voice Mode**: Speech-to-text and text-to-speech

## Requirements

- agi-core and agi-memory plugins installed
- Docker and docker-compose
- Python 3.10+

## Installation

```bash
# Install plugin
/plugin install agi-extended@agentic-marketplace

# Run setup (starts Docker services)
~/.claude/plugins/agi-extended/scripts/setup.sh
```

## Docker Services

### Qdrant (Vector Database)
- **Port**: 6333 (HTTP), 6334 (gRPC)
- **Dashboard**: http://localhost:6333/dashboard
- **Storage**: Persistent volume `agi_qdrant_data`

### Redis (Optional)
- **Port**: 6379
- Enable with: `docker-compose --profile with-redis up -d`

## MCP Servers

### enhanced-memory
Vector-based semantic memory with RAG.

**Tools:**
- `create_entities` - Store knowledge
- `search_nodes` - Semantic search
- `add_concept` / `add_procedure` / `add_episode` - Memory types
- `create_relations` - Link knowledge
- `get_compression_stats` - Memory analytics

### research-paper
Academic paper integration.

**Tools:**
- `search_arxiv` - Search arXiv papers
- `search_semantic_scholar` - Search with citation metrics
- `download_paper` - Download PDF
- `extract_insights` - AI-powered analysis
- `analyze_citations` - Citation graph analysis
- `store_paper_knowledge` - Save to memory

### video-transcript
YouTube learning capabilities.

**Tools:**
- `fetch_youtube_transcript` - Get video transcript
- `clean_transcript` - Process raw transcript
- `extract_concepts` - Identify key topics
- `extract_methodologies` - Find techniques
- `store_video_knowledge` - Save to memory

### voice-mode
Speech interaction.

**Tools:**
- `speak` - Text-to-speech
- `listen` - Speech-to-text
- `start_voice_mode` - Continuous listening
- `toggle_stt` - Toggle speech recognition

## Commands

### /agi-research
Autonomous research on any topic from papers and videos.

### /agi-improve
Self-improvement cycle to enhance capabilities.

### /agi-learn
Learn from specific sources and store in memory.

## Memory Collections

Qdrant collections created:
- `semantic_memory` - Concepts and principles
- `episodic_memory` - Experiences and events
- `procedural_memory` - Skills and techniques
- `working_memory` - Active context
- `research_papers` - Paper knowledge
- `video_knowledge` - Video insights

## Service Management

```bash
# Start services
~/.claude/plugins/agi-extended/scripts/start-services.sh

# Stop services
~/.claude/plugins/agi-extended/scripts/stop-services.sh

# View status
docker ps | grep agi-
```

## Configuration

Edit `~/.claude/agi/config.yaml`:

```yaml
tier: extended

memory:
  qdrant_url: http://localhost:6333
  embedding_model: all-MiniLM-L6-v2

voice:
  whisper_model: base
  tts_voice: en-IE-EmilyNeural

research:
  papers_dir: ~/.claude/agi/research-papers
  transcripts_dir: ~/.claude/agi/video-transcripts
```

## Upgrade Path

Install agi-cluster for:
- Multi-node distribution
- Inter-node AI communication
- Swarm intelligence

```bash
/plugin install agi-cluster@agentic-marketplace
```

## Troubleshooting

### Qdrant not starting
```bash
# Check Docker logs
docker logs agi-qdrant

# Restart services
docker-compose -f ~/.claude/plugins/agi-extended/docker/docker-compose.yml restart
```

### Memory search returning empty
```bash
# Verify collections exist
curl http://localhost:6333/collections

# Reinitialize
python3 ~/.claude/plugins/agi-extended/scripts/init-qdrant.py
```

### Voice not working
```bash
# Check audio devices
arecord -l  # Input devices
aplay -l    # Output devices

# Test TTS
python3 -c "import edge_tts; print('OK')"
```
