#!/bin/bash
# Qdrant Vector Search Quick Reference
# Location: /mnt/agentic-system/scripts/qdrant-quick-reference.sh

cat << 'QUICKREF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                        QDRANT VECTOR SEARCH - QUICK REFERENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 ENDPOINTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Qdrant Server:     http://localhost:6333
  Dashboard:         http://localhost:6333/dashboard
  Collections API:   http://localhost:6333/collections/enhanced_memory

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 QUICK CHECKS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # Check Qdrant is running
  curl -s http://localhost:6333/ | jq

  # Collection info
  curl -s http://localhost:6333/collections/enhanced_memory | jq .result

  # Count points
  curl -s http://localhost:6333/collections/enhanced_memory | jq .result.points_count

  # Check status
  docker ps | grep qdrant
  systemctl status docker

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🐍 PYTHON USAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  from qdrant_client import QdrantClient
  from sentence_transformers import SentenceTransformer
  
  # Initialize
  client = QdrantClient(host="localhost", port=6333)
  model = SentenceTransformer("all-MiniLM-L6-v2")
  
  # Search
  query = "your query here"
  embedding = model.encode(query).tolist()
  
  results = client.query_points(
      collection_name="enhanced_memory",
      query=embedding,
      limit=5
  )
  
  # Display results
  for r in results.points:
      print(f"[{r.score:.3f}] {r.payload['name']}")
      print(f"  Type: {r.payload['entity_type']}")
      print(f"  Preview: {r.payload['observations_preview'][:100]}...")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧪 TEST SCRIPTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # Comparison test (vector vs text)
  python3 /mnt/agentic-system/scripts/compare-search-methods.py

  # Direct client test
  python3 /tmp/test_vector_search_v2.py

  # Semantic advantage demo
  python3 /tmp/demonstrate_semantic_advantage.py

  # Full test report
  python3 /tmp/qdrant_test_report.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 PERFORMANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Collection:        enhanced_memory
  Points:            911 knowledge entities
  Vector Size:       384 dimensions
  Distance Metric:   Cosine similarity
  Index:             HNSW (m=16, ef_construct=100)
  Avg Query Time:    32ms
  Status:            ✅ Production ready

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 DOCUMENTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Test Report:  /mnt/agentic-system/docs/QDRANT-VECTOR-SEARCH-TEST-REPORT.md
  This File:    /mnt/agentic-system/scripts/qdrant-quick-reference.sh

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # Restart Qdrant
  docker restart qdrant

  # Check logs
  docker logs qdrant --tail 50

  # Verify collection
  curl http://localhost:6333/collections/enhanced_memory

  # Full diagnostic
  docker ps | grep qdrant && curl -s http://localhost:6333/ | jq

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUICKREF
