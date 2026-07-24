# Third-Party Dependencies (not vendored)

**Policy (operator directive, 2026-07-24):** we do not vendor third-party
licensed source into this repository. Dependencies are fetched at install time
from their upstreams. Anything we need but cannot use under its license gets
**clean-room reimplemented** rather than copied, so our own IP stays
unencumbered.

This applies regardless of how permissive the license is. MIT and Apache code is
legally fine to use, but vendoring it still mixes third-party copyright into our
tree, which is what we are avoiding. The same rule already governs the KRE repo.

Every tree listed below was **already declared ignored** in `.gitignore` and was
tracked only because it was committed before that rule existed (gitignore does
not untrack what is already tracked). Untracking on 2026-07-24 restored the
repo's own stated intent. **Local working copies were left in place**, so
running services were not interrupted.

## Removed from tracking

| Path | Upstream | License | Notes |
|---|---|---|---|
| `openai-edge-tts/` | https://github.com/travisvn/openai-edge-tts | **GPL v3** | Strong copyleft. Do not vendor. |
| `monitoring/grafana/plugins/grafana-exploretraces-app/` | Grafana plugin catalog, v2.0.3 | **AGPL v3** | Install via `grafana-cli plugins install`. |
| `monitoring/grafana/plugins/grafana-lokiexplore-app/` | Grafana plugin catalog, v2.0.4 | **AGPL v3** | Same. |
| `monitoring/grafana/plugins/grafana-metricsdrilldown-app/` | Grafana plugin catalog, v2.0.5 | **AGPL v3** | Same. |
| `monitoring/grafana/plugins/grafana-pyroscope-app/` | Grafana plugin catalog, v2.0.5 | **AGPL v3** | Same. |
| `voice-cache/whisper.cpp/` | https://github.com/ggerganov/whisper.cpp | MIT (ggml authors) | Not the live path: `voice-mode` runs `/opt/homebrew/bin/voicemode`. |
| `chatterbox-server/` | https://github.com/devnen/Chatterbox-TTS-Server | MIT (devnen) | |
| `mcp-servers/SAFLA/` | https://github.com/marc-shade/SAFLA (fork of rUv/SAFLA) | MIT (rUv) | Our fork, third-party origin. Runs from a local venv, unaffected by untracking. |

## Retained (ours)

| Path | Copyright |
|---|---|
| `mcp-servers/fraud-detection-mcp/` | 2 Acre Studios |
| `mcp-servers/synthetic-data-mcp/` | Marc Shade / 2 Acre Studios |

## Restoring on a fresh clone

The AGPL Grafana plugins install through Grafana's own tooling and must never be
committed back:

```bash
grafana-cli plugins install grafana-exploretraces-app 2.0.3
grafana-cli plugins install grafana-lokiexplore-app 2.0.4
grafana-cli plugins install grafana-metricsdrilldown-app 2.0.5
grafana-cli plugins install grafana-pyroscope-app 2.0.5
```

The rest clone from upstream into their ignored paths:

```bash
git clone https://github.com/marc-shade/SAFLA.git             mcp-servers/SAFLA
git clone https://github.com/ggerganov/whisper.cpp.git        voice-cache/whisper.cpp
git clone https://github.com/devnen/Chatterbox-TTS-Server.git chatterbox-server
git clone https://github.com/travisvn/openai-edge-tts.git     openai-edge-tts   # GPL: runtime only, never link
```

## Standing rules

1. **Never `git add` a third-party tree.** If a dependency needs to live in the
   working directory, add it to `.gitignore` and record it here instead.
2. **AGPL and GPL are runtime-only, never linked or derived from.** If we need
   the behavior inside our own code, clean-room reimplement it from the
   documented interface, never from reading their source.
3. **A missing license file is not permission.** Absence of an explicit license
   means no license was asserted; it does not make the code ours to vendor.
4. **Check before publishing:** `git ls-files -i -c --exclude-standard` lists
   tracked files the repo's own ignore rules say should not be there. It should
   stay empty.
