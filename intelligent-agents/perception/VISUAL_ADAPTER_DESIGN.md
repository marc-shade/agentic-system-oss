# Visual Adapter Design for LVR Phase 3

## Research Foundation

Based on CLIP-Adapter research (arxiv:2110.04544):
- Lightweight bottleneck adapter appended after vision encoder
- Residual-style blending with original features
- Few-shot training capability
- ~50 min training time on single GPU

## Our System Context

### Current Capabilities
- **Edge TPU**: 1001-dim MobileNet V2 logits (ImageNet softmax)
- **Visual Memory**: Cosine similarity search on 1001-dim vectors
- **GPU Node**: completeu-server (M4 Max, 128GB unified memory)
- **Inference Node**: Ollama serving LLMs

### Limitations of Current 1001-dim Embeddings
1. ImageNet class probabilities, not semantic features
2. Limited to ImageNet vocabulary (objects, animals, scenes)
3. No cross-modal alignment with language models
4. 1001-dim is sparse - most dimensions near zero

## Adapter Architecture Design

### Option A: Local Adapter (Lightweight)

```
Edge TPU (1001-dim) → Adapter → Enhanced Embedding (256-dim)
                         ↓
                    Residual Blend
                         ↓
                  Final Embedding (256/512-dim)
```

**Adapter Structure**:
```python
class VisualAdapter(nn.Module):
    def __init__(self, input_dim=1001, hidden_dim=256, output_dim=256):
        self.down = nn.Linear(input_dim, hidden_dim)
        self.up = nn.Linear(hidden_dim, output_dim)
        self.alpha = nn.Parameter(torch.tensor(0.5))

    def forward(self, x):
        adapted = F.relu(self.down(x))
        adapted = self.up(adapted)

        # Residual blend (project original if needed)
        if x.shape[-1] != adapted.shape[-1]:
            x = self.proj(x)  # optional projection

        return self.alpha * adapted + (1 - self.alpha) * x
```

**Training Data**: Visual episodes with context labels
**Training Location**: completeu-server (GPU)
**Inference Location**: macpro51 (CPU, ~5ms)

### Option B: Cross-Modal Adapter (CLIP-aligned)

```
Edge TPU (1001-dim) → Adapter → CLIP-aligned (512-dim)
                                      ↕
                              LLM Text Embeddings
```

**Benefits**:
- Direct compatibility with multimodal LLMs
- Can use CLIP text encoder for hybrid search
- Enables "describe this image" without vision model

**Training**: Contrastive loss with text-image pairs
**Data**: Visual episodes with context descriptions

### Option C: Hybrid Two-Stage

```
Stage 1 (TPU): Image → 1001-dim logits (fast, local)
Stage 2 (GPU): 1001-dim → Rich Features (768/1024-dim)
                              ↓
                    Offload to GPU node
```

**For**: High-quality feature extraction
**Latency**: ~50-100ms (network + inference)
**Use Case**: Memory consolidation, not real-time

## Implementation Plan

### Phase 3.1: Local Adapter Training
1. Collect training data from visual_episodes table
2. Define adapter architecture (Option A)
3. Train on GPU node with contrastive loss
4. Export model for CPU inference on macpro51

### Phase 3.2: Integration
1. Add `AdaptedVisualMemory` class
2. Load trained adapter weights
3. Transform embeddings on store/search
4. Update hybrid search to use adapted features

### Phase 3.3: Cross-Modal Extension
1. Research CLIP alignment approaches
2. Collect text-image pairs from context fields
3. Train cross-modal adapter
4. Enable text-to-image and image-to-text retrieval

## Training Data Strategy

### From Existing Visual Episodes
```sql
SELECT image_path, context, activity, scene_type, metadata_json
FROM visual_episodes
WHERE context IS NOT NULL AND context != ''
```

### Augmentation
- Random crops/flips during training
- Context paraphrasing with LLM
- Scene type clustering for hard negatives

### Contrastive Loss
```python
def contrastive_loss(visual_emb, text_emb, temperature=0.07):
    # Normalize
    visual_emb = F.normalize(visual_emb, dim=-1)
    text_emb = F.normalize(text_emb, dim=-1)

    # Cosine similarity matrix
    logits = visual_emb @ text_emb.T / temperature

    # Labels: diagonal is positive pairs
    labels = torch.arange(len(visual_emb))

    loss = (F.cross_entropy(logits, labels) +
            F.cross_entropy(logits.T, labels)) / 2
    return loss
```

## Code Location

- Adapter training: `intelligent-agents/perception/train_visual_adapter.py`
- Adapter inference: `intelligent-agents/perception/visual_adapter.py`
- Integration: `intelligent-agents/perception/adapted_visual_memory.py`
- MCP tools: `mcp-servers/enhanced-memory-mcp/adapted_visual_tools.py`

## Performance Targets

| Metric | Current (1001-dim) | Target (Adapted) |
|--------|-------------------|------------------|
| Embedding extraction | 15ms (TPU) | 20ms (TPU + CPU adapter) |
| Similarity search | 0.25 sim for similar | 0.7+ sim for similar |
| Cross-modal retrieval | N/A | 0.5+ text-image sim |
| Memory footprint | 4KB per episode | 1KB per episode (256-dim) |

## Dependencies

**Training (GPU node)**:
- PyTorch
- transformers (for text encoder)
- PIL, torchvision

**Inference (CPU)**:
- NumPy
- Lightweight PyTorch or ONNX runtime

## References

- [CLIP-Adapter](https://arxiv.org/abs/2110.04544) - Bottleneck adapter architecture
- [Tip-Adapter](https://arxiv.org/abs/2111.03930) - Training-free adaptation
- [VL-Adapter](https://arxiv.org/pdf/2112.06825) - Parameter-efficient VL transfer
- [Latent Visual Reasoning](https://arxiv.org/abs/2509.24251) - LVR research basis

## Implementation Status (Updated 2025-11-29)

1. [x] Implement VisualAdapter class (NumPy - lighter weight than PyTorch)
2. [x] Create training script with data loader
3. [x] Train on local CPU with visual episodes (4 samples)
4. [ ] Export to ONNX for faster CPU inference (future)
5. [x] Integrate with VisualMemory class (AdaptedVisualMemory)
6. [x] Update hybrid search with adapted embeddings
7. [x] Add MCP tools for adapted visual search (10 tools total)

## Future Enhancements

- Train with more visual episodes (need 100+ for better results)
- GPU-accelerated training on completeu-server
- ONNX export for optimized inference
- Cross-modal text-image alignment
