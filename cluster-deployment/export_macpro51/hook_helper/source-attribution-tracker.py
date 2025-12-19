#!/usr/bin/env python3
"""
Source Attribution Tracker Hook - Solves the "Source Attribution" critique

Automatically tracks and attributes sources for all research and claims made.
Runs as PostToolUse hook to capture source information from research activities.
"""

import os
import json
import sqlite3
import re
from datetime import datetime
from typing import Dict, List, Optional, Set
import hashlib
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

class SourceAttributionTracker:
    def __init__(self):
        self.db_path = os.path.expanduser("/home/marc/.claude/source_attribution.db")
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for source tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                domain TEXT,
                content_hash TEXT,
                credibility_score REAL DEFAULT 0.5,
                source_type TEXT,
                first_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_verified TIMESTAMP,
                access_count INTEGER DEFAULT 1,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_text TEXT NOT NULL,
                claim_hash TEXT UNIQUE,
                context TEXT,
                confidence_level TEXT,
                agent_source TEXT,
                tool_source TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified BOOLEAN DEFAULT FALSE,
                contradiction_found BOOLEAN DEFAULT FALSE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS claim_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER,
                source_id INTEGER,
                relevance_score REAL DEFAULT 0.5,
                quote_text TEXT,
                page_location TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (claim_id) REFERENCES claims (id),
                FOREIGN KEY (source_id) REFERENCES sources (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS source_credibility (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT UNIQUE,
                base_credibility REAL DEFAULT 0.5,
                authority_indicators TEXT,
                bias_indicators TEXT,
                last_evaluated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Initialize known credible sources
        self._init_credible_domains()
        
        conn.commit()
        conn.close()
    
    def _init_credible_domains(self):
        """Initialize database with known credible source domains"""
        credible_domains = {
            # Academic and Research
            'arxiv.org': {'credibility': 0.9, 'type': 'academic'},
            'scholar.google.com': {'credibility': 0.85, 'type': 'academic'},
            'pubmed.ncbi.nlm.nih.gov': {'credibility': 0.95, 'type': 'academic'},
            'ieee.org': {'credibility': 0.9, 'type': 'technical'},
            'acm.org': {'credibility': 0.9, 'type': 'technical'},
            
            # Official Documentation
            'docs.python.org': {'credibility': 1.0, 'type': 'official_docs'},
            'developer.mozilla.org': {'credibility': 0.95, 'type': 'official_docs'},
            'nodejs.org': {'credibility': 1.0, 'type': 'official_docs'},
            'reactjs.org': {'credibility': 1.0, 'type': 'official_docs'},
            'kubernetes.io': {'credibility': 1.0, 'type': 'official_docs'},
            
            # Technical Authority
            'stackoverflow.com': {'credibility': 0.7, 'type': 'community'},
            'github.com': {'credibility': 0.8, 'type': 'code_repository'},
            'medium.com': {'credibility': 0.6, 'type': 'blog'},
            'dev.to': {'credibility': 0.65, 'type': 'blog'},
            
            # Industry Analysis
            'gartner.com': {'credibility': 0.85, 'type': 'industry_analysis'},
            'forrester.com': {'credibility': 0.85, 'type': 'industry_analysis'},
            'techcrunch.com': {'credibility': 0.7, 'type': 'news'},
            'arstechnica.com': {'credibility': 0.75, 'type': 'news'},
            
            # Standards Bodies
            'w3.org': {'credibility': 1.0, 'type': 'standards'},
            'ietf.org': {'credibility': 1.0, 'type': 'standards'},
            'iso.org': {'credibility': 1.0, 'type': 'standards'},
        }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for domain, info in credible_domains.items():
            cursor.execute('''
                INSERT OR REPLACE INTO source_credibility 
                (domain, base_credibility, authority_indicators)
                VALUES (?, ?, ?)
            ''', (domain, info['credibility'], info['type']))
        
        conn.commit()
        conn.close()
    
    def extract_sources_from_content(self, content: str, tool_name: str) -> List[Dict]:
        """Extract source URLs and claims from content"""
        sources = []
        
        # URL extraction patterns
        url_patterns = [
            r'https?://[^\s\)]+',
            r'Source:\s*([^\n]+)',
            r'(?:From|Via|According to|Based on):\s*([^\n]+)',
        ]
        
        found_urls = set()
        for pattern in url_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                url = match.group(1) if match.groups() else match.group(0)
                url = url.strip('.,;:)')  # Clean up trailing punctuation
                
                if url.startswith('http') and url not in found_urls:
                    found_urls.add(url)
                    sources.append({
                        'url': url,
                        'context': self._extract_context(content, match.start(), match.end()),
                        'tool_source': tool_name,
                        'extraction_method': 'url_pattern'
                    })
        
        return sources
    
    def extract_claims_from_content(self, content: str, tool_name: str, agent_context: str = None) -> List[Dict]:
        """Extract factual claims from content"""
        claims = []
        
        # Claim identification patterns
        claim_patterns = [
            r'(?:According to|Research shows|Studies indicate|Data demonstrates)\s+([^.!?]+[.!?])',
            r'(?:The|This)\s+(?:study|research|analysis|report)\s+(?:found|shows|indicates|demonstrates)\s+([^.!?]+[.!?])',
            r'(?:Statistics|Benchmarks|Performance tests)\s+(?:show|indicate|demonstrate)\s+([^.!?]+[.!?])',
            r'(?:Industry analysis|Market research)\s+(?:reveals|shows|indicates)\s+([^.!?]+[.!?])',
        ]
        
        for pattern in claim_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                claim_text = match.group(1).strip()
                if len(claim_text) > 20:  # Filter out too-short claims
                    claims.append({
                        'claim_text': claim_text,
                        'context': self._extract_context(content, match.start(), match.end()),
                        'confidence_level': self._assess_confidence(claim_text),
                        'agent_source': agent_context or 'orchestrator',
                        'tool_source': tool_name
                    })
        
        # Also extract numerical claims and performance assertions
        numerical_patterns = [
            r'(\d+(?:\.\d+)?%?\s+(?:improvement|increase|decrease|faster|slower|more|less)[^.!?]*[.!?])',
            r'((?:up to|over|more than|less than)\s+\d+[^.!?]*[.!?])',
            r'(\d+x\s+(?:faster|slower|better|worse)[^.!?]*[.!?])',
        ]
        
        for pattern in numerical_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                claim_text = match.group(1).strip()
                claims.append({
                    'claim_text': claim_text,
                    'context': self._extract_context(content, match.start(), match.end()),
                    'confidence_level': 'quantitative',
                    'agent_source': agent_context or 'orchestrator',
                    'tool_source': tool_name
                })
        
        return claims
    
    def _extract_context(self, content: str, start: int, end: int, window: int = 100) -> str:
        """Extract context around a match"""
        context_start = max(0, start - window)
        context_end = min(len(content), end + window)
        return content[context_start:context_end].strip()
    
    def _assess_confidence(self, claim_text: str) -> str:
        """Assess confidence level of a claim based on language"""
        high_confidence_indicators = [
            'research shows', 'studies demonstrate', 'data proves', 
            'according to', 'statistics show', 'benchmarks indicate'
        ]
        
        low_confidence_indicators = [
            'might', 'could', 'possibly', 'potentially', 'may',
            'seems', 'appears', 'suggests', 'indicates'
        ]
        
        claim_lower = claim_text.lower()
        
        if any(indicator in claim_lower for indicator in high_confidence_indicators):
            return 'high'
        elif any(indicator in claim_lower for indicator in low_confidence_indicators):
            return 'low'
        else:
            return 'medium'
    
    def store_sources(self, sources: List[Dict]) -> List[int]:
        """Store sources in database"""
        stored_ids = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for source in sources:
            url = source['url']
            domain = urlparse(url).netloc
            
            # Get or create source record
            cursor.execute('SELECT id FROM sources WHERE url = ?', (url,))
            existing = cursor.fetchone()
            
            if existing:
                # Update access count
                cursor.execute('''
                    UPDATE sources 
                    SET access_count = access_count + 1, last_verified = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (existing[0],))
                stored_ids.append(existing[0])
            else:
                # Get credibility for domain
                cursor.execute('SELECT base_credibility FROM source_credibility WHERE domain = ?', (domain,))
                credibility_record = cursor.fetchone()
                credibility = credibility_record[0] if credibility_record else 0.5
                
                # Create new source
                cursor.execute('''
                    INSERT INTO sources 
                    (url, domain, credibility_score, source_type, metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    url,
                    domain,
                    credibility,
                    source.get('extraction_method', 'manual'),
                    json.dumps({
                        'context': source.get('context', ''),
                        'tool_source': source.get('tool_source', ''),
                        'first_seen': datetime.now().isoformat()
                    })
                ))
                
                stored_ids.append(cursor.lastrowid)
        
        conn.commit()
        conn.close()
        return stored_ids
    
    def store_claims(self, claims: List[Dict]) -> List[int]:
        """Store claims in database"""
        stored_ids = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for claim in claims:
            # Create hash to detect duplicate claims
            claim_content = claim['claim_text'] + claim.get('context', '')
            claim_hash = hashlib.md5(claim_content.encode()).hexdigest()
            
            # Check if claim already exists
            cursor.execute('SELECT id FROM claims WHERE claim_hash = ?', (claim_hash,))
            existing = cursor.fetchone()
            
            if not existing:
                cursor.execute('''
                    INSERT INTO claims 
                    (claim_text, claim_hash, context, confidence_level, 
                     agent_source, tool_source)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    claim['claim_text'],
                    claim_hash,
                    claim.get('context', ''),
                    claim.get('confidence_level', 'medium'),
                    claim.get('agent_source', 'orchestrator'),
                    claim.get('tool_source', 'unknown')
                ))
                
                stored_ids.append(cursor.lastrowid)
            else:
                stored_ids.append(existing[0])
        
        conn.commit()
        conn.close()
        return stored_ids
    
    def link_claims_to_sources(self, claim_ids: List[int], source_ids: List[int]) -> int:
        """Link claims to their sources"""
        if not claim_ids or not source_ids:
            return 0
        
        links_created = 0
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for claim_id in claim_ids:
            for source_id in source_ids:
                # Check if link already exists
                cursor.execute('''
                    SELECT id FROM claim_sources 
                    WHERE claim_id = ? AND source_id = ?
                ''', (claim_id, source_id))
                
                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO claim_sources (claim_id, source_id, relevance_score)
                        VALUES (?, ?, ?)
                    ''', (claim_id, source_id, 0.8))  # Default relevance
                    links_created += 1
        
        conn.commit()
        conn.close()
        return links_created
    
    def generate_source_report(self, claim_text: str = None) -> str:
        """Generate source attribution report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if claim_text:
            # Report for specific claim
            cursor.execute('''
                SELECT c.claim_text, s.url, s.title, s.credibility_score, cs.quote_text
                FROM claims c
                JOIN claim_sources cs ON c.id = cs.claim_id
                JOIN sources s ON cs.source_id = s.id
                WHERE c.claim_text LIKE ?
                ORDER BY s.credibility_score DESC
            ''', (f'%{claim_text}%',))
        else:
            # General source quality report
            cursor.execute('''
                SELECT s.domain, COUNT(*) as usage_count, 
                       AVG(s.credibility_score) as avg_credibility,
                       MAX(s.last_verified) as last_verified
                FROM sources s
                GROUP BY s.domain
                ORDER BY usage_count DESC, avg_credibility DESC
                LIMIT 20
            ''')
        
        results = cursor.fetchall()
        conn.close()
        
        if claim_text and results:
            report = f"## Source Attribution for: '{claim_text[:50]}...'\n\n"
            for row in results:
                report += f"**Source**: [{row[1]}]({row[1]})\n"
                report += f"- **Credibility**: {row[3]:.2f}/1.0\n"
                if row[4]:
                    report += f"- **Quote**: \"{row[4][:100]}...\"\n"
                report += "\n"
        elif results:
            report = "## Source Quality Report\n\n"
            report += "| Domain | Usage Count | Avg Credibility | Last Verified |\n"
            report += "|--------|-------------|-----------------|---------------|\n"
            for row in results:
                report += f"| {row[0]} | {row[1]} | {row[2]:.2f} | {row[3] or 'Never'} |\n"
        else:
            report = "No source attribution data found."
        
        return report
    
    def verify_source_accessibility(self, url: str) -> Dict:
        """Verify that a source is still accessible"""
        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Compatible Source Verification Bot)'
            })
            
            if response.status_code == 200:
                # Try to extract title
                soup = BeautifulSoup(response.content, 'html.parser')
                title = soup.find('title')
                title_text = title.get_text().strip() if title else 'No title'
                
                return {
                    'accessible': True,
                    'status_code': response.status_code,
                    'title': title_text,
                    'content_length': len(response.content),
                    'last_modified': response.headers.get('Last-Modified'),
                    'verified_at': datetime.now().isoformat()
                }
            else:
                return {
                    'accessible': False,
                    'status_code': response.status_code,
                    'error': f'HTTP {response.status_code}',
                    'verified_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'accessible': False,
                'error': str(e),
                'verified_at': datetime.now().isoformat()
            }

def hook_main(tool_name: str, tool_args: Dict, tool_result: str, context: Dict) -> Dict:
    """
    Main hook function - called after each tool use
    Tracks source attribution from research activities
    """
    try:
        tracker = SourceAttributionTracker()
        
        # Focus on research-related tools
        research_tools = ['WebFetch', 'WebSearch', 'Read', 'Grep']
        if tool_name not in research_tools:
            return {"sources_tracked": 0, "claims_tracked": 0}
        
        agent_context = context.get('agent_name', 'orchestrator')
        
        # Analyze tool arguments and results
        content_to_analyze = ""
        
        # For WebFetch, analyze the URL and content
        if tool_name == 'WebFetch' and isinstance(tool_args, dict):
            url = tool_args.get('url', '')
            if url:
                # Store the URL as a source
                sources = [{'url': url, 'tool_source': tool_name}]
                source_ids = tracker.store_sources(sources)
                
                # Analyze the fetched content for claims
                if isinstance(tool_result, str):
                    content_to_analyze = tool_result
        
        # For other tools, extract sources and claims from results
        elif isinstance(tool_result, str) and len(tool_result) > 100:
            content_to_analyze = tool_result
        
        if content_to_analyze:
            # Extract sources from content
            sources = tracker.extract_sources_from_content(content_to_analyze, tool_name)
            source_ids = tracker.store_sources(sources) if sources else []
            
            # Extract claims from content
            claims = tracker.extract_claims_from_content(
                content_to_analyze, tool_name, agent_context
            )
            claim_ids = tracker.store_claims(claims) if claims else []
            
            # Link claims to sources
            links_created = 0
            if claim_ids and source_ids:
                links_created = tracker.link_claims_to_sources(claim_ids, source_ids)
            
            return {
                "sources_tracked": len(source_ids),
                "claims_tracked": len(claim_ids),
                "links_created": links_created,
                "research_quality_score": sum(s.get('credibility_score', 0.5) for s in sources) / len(sources) if sources else 0
            }
        
        return {"sources_tracked": 0, "claims_tracked": 0}
        
    except Exception as e:
        # Log error but don't break the tool chain
        with open(os.path.expanduser("/home/marc/.claude/hooks/source_attribution_errors.log"), "a") as f:
            f.write(f"{datetime.now().isoformat()}: Error in source attribution: {str(e)}\n")
        return {"error": str(e), "sources_tracked": 0, "claims_tracked": 0}

def get_attribution_dashboard() -> str:
    """Generate source attribution dashboard"""
    try:
        tracker = SourceAttributionTracker()
        
        # Get recent activity
        conn = sqlite3.connect(tracker.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM sources 
            WHERE first_accessed >= date('now', '-7 days')
        ''')
        recent_sources = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM claims 
            WHERE created_date >= date('now', '-7 days')
        ''')
        recent_claims = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT AVG(credibility_score) FROM sources
        ''')
        avg_credibility = cursor.fetchone()[0] or 0
        
        conn.close()
        
        dashboard = f"""
# Source Attribution Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Recent Activity (Past 7 Days)
- **New Sources**: {recent_sources}
- **New Claims**: {recent_claims}
- **Average Source Credibility**: {avg_credibility:.2f}/1.0

## Source Quality Report
{tracker.generate_source_report()}

## Commands
- View claim sources: `get_claim_sources("claim text")`
- Verify source accessibility: `verify_source_status("url")`
- Generate attribution report: `get_attribution_report()`

---
*All research claims are automatically tracked with source attribution*
"""
        
        return dashboard
        
    except Exception as e:
        return f"Error generating attribution dashboard: {str(e)}"

if __name__ == "__main__":
    # CLI interface for manual source attribution management
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: source-attribution-tracker.py [dashboard|report|verify <url>]")
        sys.exit(1)
    
    command = sys.argv[1]
    tracker = SourceAttributionTracker()
    
    if command == "dashboard":
        print(get_attribution_dashboard())
    elif command == "report":
        claim_text = sys.argv[2] if len(sys.argv) > 2 else None
        print(tracker.generate_source_report(claim_text))
    elif command == "verify" and len(sys.argv) > 2:
        url = sys.argv[2]
        result = tracker.verify_source_accessibility(url)
        print(json.dumps(result, indent=2))
    else:
        print("Unknown command")