#!/bin/bash
#
# AVIR - AI-Verified Independent Replication
#
# This script uses an independent AI system to verify the Agentic System
# capabilities in an isolated container environment.
#

set -e

PROVIDER="${1:-codex}"
CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-docker}"

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║              AVIR - AI-Verified Independent Replication           ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Provider: $PROVIDER"
echo "Container Runtime: $CONTAINER_RUNTIME"
echo ""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --provider) PROVIDER="$2"; shift 2 ;;
        --runtime) CONTAINER_RUNTIME="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Check prerequisites
if ! command -v $CONTAINER_RUNTIME &>/dev/null; then
    echo "ERROR: $CONTAINER_RUNTIME not found"
    exit 1
fi

case $PROVIDER in
    codex)
        if [ -z "$OPENAI_API_KEY" ]; then
            echo "ERROR: OPENAI_API_KEY not set"
            echo "Export your OpenAI API key: export OPENAI_API_KEY=sk-..."
            exit 1
        fi
        ;;
    gemini)
        if [ -z "$GOOGLE_API_KEY" ]; then
            echo "ERROR: GOOGLE_API_KEY not set"
            echo "Export your Google API key: export GOOGLE_API_KEY=AIza..."
            exit 1
        fi
        ;;
    *)
        echo "ERROR: Unknown provider: $PROVIDER"
        echo "Valid providers: codex, gemini"
        exit 1
        ;;
esac

# Create results directory
RESULTS_DIR="results/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo "Building verification container..."
$CONTAINER_RUNTIME build -t avir-verification -f Dockerfile . 2>&1 | tee "$RESULTS_DIR/build.log"

echo ""
echo "Running verification..."
$CONTAINER_RUNTIME run --rm \
    -e PROVIDER="$PROVIDER" \
    -e OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
    -e GOOGLE_API_KEY="${GOOGLE_API_KEY:-}" \
    -v "$(pwd)/$RESULTS_DIR:/results" \
    avir-verification 2>&1 | tee "$RESULTS_DIR/verification.log"

# Check results
if [ -f "$RESULTS_DIR/attestation.json" ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "                    VERIFICATION COMPLETE"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    # Extract and display results
    VERDICT=$(python3 -c "import json; print(json.load(open('$RESULTS_DIR/attestation.json'))['verdict'])")
    HASH=$(python3 -c "import json; print(json.load(open('$RESULTS_DIR/attestation.json'))['attestation_hash'])")

    echo "Verdict: $VERDICT"
    echo "Attestation Hash: $HASH"
    echo ""
    echo "Full results: $RESULTS_DIR/attestation.json"

    if [ "$VERDICT" == "VERIFIED" ]; then
        echo ""
        echo "✓ System VERIFIED by independent AI ($PROVIDER)"
        exit 0
    else
        echo ""
        echo "✗ Verification FAILED"
        exit 1
    fi
else
    echo "ERROR: No attestation generated"
    exit 1
fi
