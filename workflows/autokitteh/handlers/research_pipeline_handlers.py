"""
Autonomous Research Pipeline Handlers
Discovers, analyzes, and integrates research papers and videos
Stores extracted knowledge in enhanced-memory for AGI learning
"""
import os
import platform
import subprocess
import json
import time
import requests
from datetime import datetime
from pathlib import Path


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent.parent.parent


_STORAGE_BASE = _get_storage_base()

# Research topics for autonomous exploration
RESEARCH_TOPICS = [
    "recursive self-improvement AGI",
    "meta-learning neural networks",
    "causal reasoning AI",
    "world models reinforcement learning",
    "hierarchical planning AI",
    "continual learning neural networks",
    "neurosymbolic AI integration",
    "transformer memory architectures",
    "multi-agent coordination",
    "emergent behavior AI systems"
]


def run_research_discovery(event):
    """
    Discover new research papers on AGI-relevant topics
    Runs nightly to find and process new papers
    """
    print("=" * 60)
    print(f"Research Discovery Pipeline - {datetime.now()}")
    print("=" * 60)

    results = {
        "timestamp": datetime.now().isoformat(),
        "papers_found": 0,
        "papers_processed": 0,
        "insights_extracted": 0,
        "status": "started"
    }

    try:
        # Select today's research topic
        topic = select_research_topic()
        print(f"\nToday's research focus: {topic}")

        # Step 1: Search arXiv
        print("\n[1/4] Searching arXiv...")
        papers = search_arxiv(topic)
        results["papers_found"] = len(papers)
        print(f"Found {len(papers)} papers")

        # Step 2: Search Semantic Scholar for high-impact papers
        print("\n[2/4] Searching Semantic Scholar...")
        semantic_papers = search_semantic_scholar(topic)
        results["papers_found"] += len(semantic_papers)
        print(f"Found {len(semantic_papers)} additional papers")

        # Combine and deduplicate
        all_papers = deduplicate_papers(papers + semantic_papers)
        print(f"Total unique papers: {len(all_papers)}")

        # Step 3: Extract insights from top papers
        print("\n[3/4] Extracting insights...")
        insights = []
        for paper in all_papers[:5]:  # Process top 5
            paper_insights = extract_paper_insights(paper)
            insights.extend(paper_insights)
            results["papers_processed"] += 1

        results["insights_extracted"] = len(insights)
        print(f"Extracted {len(insights)} insights")

        # Step 4: Store in enhanced-memory
        print("\n[4/4] Storing knowledge...")
        stored = store_research_knowledge(all_papers[:5], insights, topic)

        results["status"] = "completed"
        results["entities_created"] = stored.get("entities_created", 0)

        print(f"\n✓ Research discovery complete")
        print(f"  Papers found: {results['papers_found']}")
        print(f"  Papers processed: {results['papers_processed']}")
        print(f"  Insights extracted: {results['insights_extracted']}")

        # Notify via voice
        notify_research_complete(results, topic)

        return results

    except Exception as e:
        print(f"ERROR: Research discovery failed: {e}")
        import traceback
        traceback.print_exc()
        results["status"] = "error"
        results["error"] = str(e)
        return results


def run_video_learning(event):
    """
    Process educational videos for knowledge extraction
    Finds and processes relevant YouTube content
    """
    print("=" * 60)
    print(f"Video Learning Pipeline - {datetime.now()}")
    print("=" * 60)

    results = {
        "timestamp": datetime.now().isoformat(),
        "videos_processed": 0,
        "concepts_extracted": 0,
        "status": "started"
    }

    try:
        # Get curated video list or search
        videos = get_learning_videos()
        print(f"Processing {len(videos)} videos")

        for video in videos[:3]:  # Process top 3
            print(f"\nProcessing: {video.get('title', video.get('url'))}")

            # Extract transcript
            transcript = fetch_youtube_transcript(video["url"])
            if not transcript:
                print("  Could not fetch transcript")
                continue

            # Extract concepts
            concepts = extract_video_concepts(transcript)
            results["concepts_extracted"] += len(concepts)
            results["videos_processed"] += 1

            # Store in memory
            store_video_knowledge(video, concepts)

        results["status"] = "completed"
        print(f"\n✓ Video learning complete")
        print(f"  Videos processed: {results['videos_processed']}")
        print(f"  Concepts extracted: {results['concepts_extracted']}")

        return results

    except Exception as e:
        print(f"ERROR: Video learning failed: {e}")
        results["status"] = "error"
        results["error"] = str(e)
        return results


def select_research_topic():
    """Select a research topic based on day and recent gaps"""
    day_of_year = datetime.now().timetuple().tm_yday
    return RESEARCH_TOPICS[day_of_year % len(RESEARCH_TOPICS)]


def search_arxiv(query, max_results=10):
    """Search arXiv via MCP or direct API"""
    try:
        # Try MCP first
        response = requests.post(
            "http://localhost:8103/search_arxiv",
            json={"query": query, "max_results": max_results},
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get("papers", [])
    except:
        pass

    # Fallback to direct arxiv API
    try:
        import urllib.request
        import xml.etree.ElementTree as ET

        query_encoded = query.replace(" ", "+")
        url = f"http://export.arxiv.org/api/query?search_query=all:{query_encoded}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read().decode()

        root = ET.fromstring(data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        papers = []
        for entry in root.findall("atom:entry", ns):
            paper = {
                "title": entry.find("atom:title", ns).text.strip(),
                "abstract": entry.find("atom:summary", ns).text.strip()[:500],
                "url": entry.find("atom:id", ns).text,
                "authors": [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)][:3]
            }
            papers.append(paper)

        return papers

    except Exception as e:
        print(f"arXiv search failed: {e}")
        return []


def search_semantic_scholar(query, limit=10):
    """Search Semantic Scholar for high-impact papers"""
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,abstract,citationCount,year,authors"
        }

        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            papers = []
            for paper in data.get("data", []):
                papers.append({
                    "title": paper.get("title", ""),
                    "abstract": paper.get("abstract", "")[:500] if paper.get("abstract") else "",
                    "citations": paper.get("citationCount", 0),
                    "year": paper.get("year"),
                    "authors": [a.get("name") for a in paper.get("authors", [])[:3]]
                })
            return papers

    except Exception as e:
        print(f"Semantic Scholar search failed: {e}")

    return []


def deduplicate_papers(papers):
    """Remove duplicate papers based on title similarity"""
    seen_titles = set()
    unique = []

    for paper in papers:
        title_normalized = paper.get("title", "").lower().strip()
        if title_normalized and title_normalized not in seen_titles:
            seen_titles.add(title_normalized)
            unique.append(paper)

    return unique


def extract_paper_insights(paper):
    """Extract key insights from a paper's abstract"""
    abstract = paper.get("abstract", "")
    if not abstract:
        return []

    # Simple keyword-based insight extraction
    insights = []

    # Look for method/approach mentions
    method_keywords = ["propose", "introduce", "present", "demonstrate", "show that", "achieve"]
    for keyword in method_keywords:
        if keyword in abstract.lower():
            # Extract sentence containing the keyword
            sentences = abstract.split(". ")
            for sentence in sentences:
                if keyword in sentence.lower():
                    insights.append({
                        "type": "method",
                        "content": sentence.strip(),
                        "source": paper.get("title", "Unknown")
                    })
                    break

    # Look for results
    result_keywords = ["outperform", "improve", "achieve", "accuracy", "performance"]
    for keyword in result_keywords:
        if keyword in abstract.lower():
            sentences = abstract.split(". ")
            for sentence in sentences:
                if keyword in sentence.lower() and sentence not in [i["content"] for i in insights]:
                    insights.append({
                        "type": "result",
                        "content": sentence.strip(),
                        "source": paper.get("title", "Unknown")
                    })
                    break

    return insights[:3]  # Limit to 3 insights per paper


def store_research_knowledge(papers, insights, topic):
    """Store research knowledge in enhanced-memory"""
    entities_created = 0

    try:
        # Create entity for research session
        session_entity = {
            "name": f"research_session_{datetime.now().strftime('%Y%m%d')}",
            "entityType": "research_session",
            "observations": [
                f"Topic: {topic}",
                f"Papers found: {len(papers)}",
                f"Insights extracted: {len(insights)}"
            ]
        }

        # Create entities for papers
        paper_entities = []
        for paper in papers:
            paper_entities.append({
                "name": f"paper_{paper.get('title', 'unknown')[:50]}",
                "entityType": "research_paper",
                "observations": [
                    f"Title: {paper.get('title', '')}",
                    f"Authors: {', '.join(paper.get('authors', []))}",
                    f"Abstract: {paper.get('abstract', '')[:200]}"
                ]
            })

        # Create entities for insights
        insight_entities = []
        for insight in insights:
            insight_entities.append({
                "name": f"insight_{insight['type']}_{len(insight_entities)}",
                "entityType": "research_insight",
                "observations": [
                    f"Type: {insight['type']}",
                    f"Content: {insight['content']}",
                    f"Source: {insight['source']}"
                ]
            })

        # Store via MCP
        all_entities = [session_entity] + paper_entities + insight_entities
        response = requests.post(
            "http://localhost:8101/create_entities",
            json={"entities": all_entities},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            entities_created = len(result.get("created", []))

    except Exception as e:
        print(f"Knowledge storage failed: {e}")

    return {"entities_created": entities_created}


def fetch_youtube_transcript(url):
    """Fetch YouTube transcript via MCP or local tool"""
    try:
        # Try MCP
        response = requests.post(
            "http://localhost:8104/fetch_youtube_transcript",
            json={"url": url},
            timeout=60
        )
        if response.status_code == 200:
            return response.json().get("transcript", "")
    except:
        pass

    # Fallback to local
    try:
        result = subprocess.run(
            ["yt-dlp", "--write-auto-sub", "--skip-download", "--sub-lang", "en", url],
            capture_output=True,
            text=True,
            timeout=60,
            cwd="/tmp"
        )
        # Would need to parse the VTT file
        return ""
    except:
        return ""


def extract_video_concepts(transcript):
    """Extract technical concepts from video transcript"""
    concepts = []

    # Technical keywords to look for
    keywords = [
        "neural network", "transformer", "attention", "embedding",
        "reinforcement learning", "meta-learning", "self-improvement",
        "causal", "reasoning", "planning", "memory", "architecture"
    ]

    transcript_lower = transcript.lower()
    for keyword in keywords:
        if keyword in transcript_lower:
            concepts.append({
                "concept": keyword,
                "frequency": transcript_lower.count(keyword)
            })

    # Sort by frequency
    concepts.sort(key=lambda x: x["frequency"], reverse=True)
    return concepts[:10]


def store_video_knowledge(video, concepts):
    """Store video knowledge in enhanced-memory"""
    try:
        entity = {
            "name": f"video_{video.get('title', 'unknown')[:40]}",
            "entityType": "video_learning",
            "observations": [
                f"URL: {video.get('url', '')}",
                f"Concepts: {', '.join([c['concept'] for c in concepts[:5]])}",
                f"Processed: {datetime.now().isoformat()}"
            ]
        }

        response = requests.post(
            "http://localhost:8101/create_entities",
            json={"entities": [entity]},
            timeout=10
        )
        return response.status_code == 200

    except Exception as e:
        print(f"Video storage failed: {e}")
        return False


def get_learning_videos():
    """Get curated list of learning videos"""
    # In production, this would fetch from a curated list or search
    return [
        {"url": "https://www.youtube.com/watch?v=example1", "title": "AGI Research Update"},
        {"url": "https://www.youtube.com/watch?v=example2", "title": "Meta-Learning Tutorial"}
    ]


def notify_research_complete(results, topic):
    """Send voice notification about research completion"""
    try:
        message = f"Research discovery complete. Topic: {topic}. "
        message += f"Found {results['papers_found']} papers, "
        message += f"extracted {results['insights_extracted']} insights."

        print(f"NOTIFICATION: {message}")
        return True
    except Exception as e:
        print(f"Notification failed: {e}")
        return False
