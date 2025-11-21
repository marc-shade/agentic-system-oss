#!/usr/bin/env bash
#
# Unified Security Scanning Script
# Integrates Nuclei, Checkov, and other security tools
#
# Usage: ./unified-security-scan.sh [OPTIONS]
#

set -euo pipefail

# Configuration
NUCLEI_BIN="${NUCLEI_BIN:-/Volumes/FILES/go/bin/nuclei}"
CHECKOV_BIN="${CHECKOV_BIN:-checkov}"
SCAN_DIR="${1:-.}"
OUTPUT_DIR="${OUTPUT_DIR:-./security-reports}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo -e "${GREEN}=== Unified Security Scan ===${NC}"
echo "Scan Directory: $SCAN_DIR"
echo "Output Directory: $OUTPUT_DIR"
echo "Timestamp: $TIMESTAMP"
echo ""

# Function: Run Checkov for IaC scanning
run_checkov() {
    echo -e "${YELLOW}Running Checkov IaC Security Scan...${NC}"
    if command -v "$CHECKOV_BIN" &> /dev/null; then
        $CHECKOV_BIN -d "$SCAN_DIR" \
            --framework all \
            --output json \
            --output-file "$OUTPUT_DIR/checkov-report-$TIMESTAMP.json" \
            --soft-fail || true

        # Also generate human-readable report
        $CHECKOV_BIN -d "$SCAN_DIR" \
            --framework all \
            --output cli \
            > "$OUTPUT_DIR/checkov-report-$TIMESTAMP.txt" || true

        echo -e "${GREEN}✓ Checkov scan complete${NC}"
    else
        echo -e "${RED}✗ Checkov not found, skipping IaC scan${NC}"
    fi
}

# Function: Run Nuclei for web vulnerability scanning
run_nuclei() {
    local target="$1"
    echo -e "${YELLOW}Running Nuclei Vulnerability Scan on $target...${NC}"

    if command -v "$NUCLEI_BIN" &> /dev/null; then
        $NUCLEI_BIN -u "$target" \
            -j \
            -duc \
            -silent \
            -o "$OUTPUT_DIR/nuclei-report-$TIMESTAMP.json" || true

        echo -e "${GREEN}✓ Nuclei scan complete${NC}"
    else
        echo -e "${RED}✗ Nuclei not found, skipping vulnerability scan${NC}"
    fi
}

# Function: Secret scanning
run_secret_scan() {
    echo -e "${YELLOW}Running Secret Detection Scan...${NC}"
    if command -v "$CHECKOV_BIN" &> /dev/null; then
        $CHECKOV_BIN --framework secrets \
            -d "$SCAN_DIR" \
            --output json \
            --output-file "$OUTPUT_DIR/secrets-report-$TIMESTAMP.json" \
            --soft-fail || true

        echo -e "${GREEN}✓ Secret scan complete${NC}"
    else
        echo -e "${RED}✗ Checkov not found, skipping secret scan${NC}"
    fi
}

# Function: Generate summary report
generate_summary() {
    echo -e "${YELLOW}Generating Security Summary...${NC}"

    cat > "$OUTPUT_DIR/summary-$TIMESTAMP.md" <<EOF
# Security Scan Summary
**Date**: $(date)
**Scan Directory**: $SCAN_DIR

## Scans Performed

### 1. Infrastructure as Code (Checkov)
- Report: checkov-report-$TIMESTAMP.json
- Text Output: checkov-report-$TIMESTAMP.txt

### 2. Secret Detection (Checkov)
- Report: secrets-report-$TIMESTAMP.json

### 3. Web Vulnerabilities (Nuclei)
- Available via MCP for on-demand scanning
- Command: Use mcp__nuclei-mcp__nuclei_scan_start tool

## Next Steps

1. Review Checkov findings for infrastructure misconfigurations
2. Address any detected secrets immediately
3. Use Nuclei MCP for dynamic web application testing
4. Integrate into CI/CD pipeline for continuous scanning

## MCP Integration

### Nuclei MCP Server
The Nuclei MCP server is now available for dynamic scanning:

\`\`\`python
# Via Claude Code
mcp__nuclei-mcp__nuclei_scan_start(
    target="https://example.com",
    severity="critical,high",
    templates=["cves", "exposures"]
)
\`\`\`

### Available Tools
- nuclei_scan_start: Run Nuclei scans via MCP
- Checkov: Run manually or via CI/CD

EOF

    echo -e "${GREEN}✓ Summary report generated${NC}"
    echo ""
    echo -e "${GREEN}All security reports saved to: $OUTPUT_DIR${NC}"
}

# Main execution
main() {
    # Run IaC security scan
    run_checkov

    # Run secret detection
    run_secret_scan

    # Generate summary
    generate_summary

    echo ""
    echo -e "${GREEN}=== Security Scan Complete ===${NC}"
    echo "View reports in: $OUTPUT_DIR"
    echo ""
    echo "For web application scanning, use the Nuclei MCP server:"
    echo "  mcp__nuclei-mcp__nuclei_scan_start(target='https://your-app.com')"
}

# Run main function
main "$@"
