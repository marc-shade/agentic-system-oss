#!/bin/bash
# Qdrant Vector Search Maintenance Script
# Manages the enhanced_memory collection in Qdrant

set -e


# Platform-aware storage detection
detect_storage_base() {
    if [ -n "$AGENTIC_SYSTEM_PATH" ] && [ -d "$AGENTIC_SYSTEM_PATH" ]; then
        echo "$AGENTIC_SYSTEM_PATH"
        return
    fi
    case "$(uname -s)" in
        Darwin)
            if [ -d "/Volumes/SSDRAID0/agentic-system" ]; then
                echo "/Volumes/SSDRAID0/agentic-system"
            elif [ -d "/Volumes/FILES/agentic-system" ]; then
                echo "/Volumes/FILES/agentic-system"
            fi
            ;;
        Linux)
            if [ -d "/home/marc/agentic-system" ]; then
                echo "/home/marc/agentic-system"
            elif [ -d "/mnt/agentic-system" ]; then
                echo "/mnt/agentic-system"
            fi
            ;;
    esac
}

STORAGE_BASE=$(detect_storage_base)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$STORAGE_BASE/.venv"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
}

check_status() {
    print_header "Qdrant Collection Status"

    echo -e "${YELLOW}Collection: enhanced_memory${NC}"
    curl -s http://localhost:6333/collections/enhanced_memory | jq -r '
        .result |
        "  Status: \(.status)",
        "  Points: \(.points_count)",
        "  Vector Size: \(.config.params.vectors.size)",
        "  Distance: \(.config.params.vectors.distance)",
        "  Segments: \(.segments_count)"
    '

    echo
    echo -e "${YELLOW}SQLite Database:${NC}"
    sqlite3 /home/marc/.claude/enhanced_memories/memory.db << SQL
.mode column
.headers on
SELECT
    COUNT(*) as total_entities,
    COUNT(CASE WHEN id IN (SELECT DISTINCT entity_id FROM observations) THEN 1 END) as with_observations,
    COUNT(CASE WHEN id NOT IN (SELECT DISTINCT entity_id FROM observations) THEN 1 END) as without_observations
FROM entities;
SQL
    echo
}

reindex() {
    print_header "Re-indexing Enhanced Memory Entities"

    source "$VENV_PATH/bin/activate"
    python "$SCRIPT_DIR/index-qdrant-vectors.py" --batch-size 100

    echo
    echo -e "${GREEN}✓ Re-indexing complete${NC}"
}

reindex_full() {
    print_header "Full Re-index (Recreate Collection)"

    echo -e "${RED}WARNING: This will delete and recreate the collection!${NC}"
    read -p "Continue? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        echo "Cancelled."
        exit 0
    fi

    source "$VENV_PATH/bin/activate"
    python "$SCRIPT_DIR/index-qdrant-vectors.py" --recreate --batch-size 100

    echo
    echo -e "${GREEN}✓ Full re-indexing complete${NC}"
}

test_search() {
    print_header "Test Vector Search"

    source "$VENV_PATH/bin/activate"
    python "$SCRIPT_DIR/index-qdrant-vectors.py" --test-only
}

compare_methods() {
    print_header "Compare Search Methods"

    source "$VENV_PATH/bin/activate"
    python "$SCRIPT_DIR/compare-search-methods.py"
}

show_stats() {
    print_header "Detailed Statistics"

    echo -e "${YELLOW}Entity Types Distribution:${NC}"
    sqlite3 /home/marc/.claude/enhanced_memories/memory.db << SQL
.mode column
.headers on
SELECT
    entity_type,
    COUNT(*) as count,
    ROUND(AVG(salience_score), 3) as avg_salience,
    ROUND(AVG(access_count), 1) as avg_accesses
FROM entities
WHERE id IN (SELECT DISTINCT entity_id FROM observations)
GROUP BY entity_type
ORDER BY count DESC
LIMIT 15;
SQL

    echo
    echo -e "${YELLOW}Memory Tier Distribution:${NC}"
    sqlite3 /home/marc/.claude/enhanced_memories/memory.db << SQL
.mode column
.headers on
SELECT
    tier,
    COUNT(*) as count,
    ROUND(AVG(salience_score), 3) as avg_salience
FROM entities
WHERE id IN (SELECT DISTINCT entity_id FROM observations)
GROUP BY tier
ORDER BY count DESC;
SQL

    echo
}

# Main menu
case "${1:-menu}" in
    status|s)
        check_status
        ;;
    reindex|r)
        reindex
        ;;
    recreate|full|f)
        reindex_full
        ;;
    test|t)
        test_search
        ;;
    compare|c)
        compare_methods
        ;;
    stats|st)
        show_stats
        ;;
    help|h|--help|-h)
        print_header "Qdrant Maintenance Commands"
        echo "Usage: $0 [command]"
        echo
        echo "Commands:"
        echo "  status, s       - Show collection status"
        echo "  reindex, r      - Re-index entities (incremental)"
        echo "  recreate, full  - Full re-index (recreate collection)"
        echo "  test, t         - Test vector search"
        echo "  compare, c      - Compare text vs vector search"
        echo "  stats, st       - Show detailed statistics"
        echo "  help, h         - Show this help"
        echo
        ;;
    *)
        print_header "Qdrant Vector Search Maintenance"
        echo "Select an option:"
        echo
        echo "  1) Check Status"
        echo "  2) Re-index (incremental)"
        echo "  3) Full Re-index (recreate)"
        echo "  4) Test Search"
        echo "  5) Compare Methods"
        echo "  6) Show Statistics"
        echo "  7) Exit"
        echo
        read -p "Choice [1-7]: " choice

        case $choice in
            1) check_status ;;
            2) reindex ;;
            3) reindex_full ;;
            4) test_search ;;
            5) compare_methods ;;
            6) show_stats ;;
            7) exit 0 ;;
            *) echo "Invalid choice" ;;
        esac
        ;;
esac
