#!/usr/bin/env python3
"""
Threat Intelligence MCP Server
==============================

Provides real-time threat intelligence integration for the Phoenix Agentic System.
Aggregates IOCs from multiple threat feeds and provides queryable threat data.

Feeds integrated:
- abuse.ch ThreatFox (malware IOCs)
- abuse.ch URLhaus (malicious URLs)
- CISA Known Exploited Vulnerabilities (KEV)
- Feodo Tracker (botnet C2s)

Features:
- Automatic feed synchronization
- IOC lookup by IP, domain, URL, hash
- Threat scoring and enrichment
- Integration with enhanced-memory-mcp
- Real-time alerting via voice-mode
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import sqlite3
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import aiohttp
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("threat-intel-mcp")

# Storage paths
STORAGE_BASE = Path(os.environ.get("STORAGE_BASE", Path(__file__).parent))
DATA_DIR = STORAGE_BASE / "mcp-servers/threat-intel-mcp/data"
DB_PATH = DATA_DIR / "threat_intel.db"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)


class ThreatType(Enum):
    """Types of threat indicators."""
    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    HASH_MD5 = "hash_md5"
    HASH_SHA256 = "hash_sha256"
    CVE = "cve"
    EMAIL = "email"
    FILENAME = "filename"


class ThreatSeverity(Enum):
    """Severity levels for threats."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FeedSource(Enum):
    """Threat feed sources."""
    THREATFOX = "threatfox"
    URLHAUS = "urlhaus"
    CISA_KEV = "cisa_kev"
    FEODO_TRACKER = "feodo_tracker"
    MANUAL = "manual"


@dataclass
class ThreatIndicator:
    """A single threat indicator (IOC)."""
    indicator_type: str
    value: str
    threat_type: str  # e.g., "malware", "c2", "phishing"
    malware_family: Optional[str]
    source: str
    first_seen: str
    last_seen: str
    confidence: int  # 0-100
    severity: str
    tags: List[str]
    reference_url: Optional[str]
    description: Optional[str]


@dataclass
class ThreatMatch:
    """Result of a threat lookup."""
    found: bool
    indicator: str
    matches: List[ThreatIndicator]
    risk_score: int  # 0-100
    recommendation: str


# Feed URLs - using reliable public endpoints
FEED_URLS = {
    # ThreatFox export (public, no auth required)
    FeedSource.THREATFOX: "https://threatfox.abuse.ch/export/json/recent/",
    # URLhaus recent URLs (public CSV)
    FeedSource.URLHAUS: "https://urlhaus.abuse.ch/downloads/csv_recent/",
    # CISA KEV (official JSON)
    FeedSource.CISA_KEV: "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
    # Feodo Tracker IP blocklist (public JSON)
    FeedSource.FEODO_TRACKER: "https://feodotracker.abuse.ch/downloads/ipblocklist.json",
}


class ThreatIntelDatabase:
    """SQLite-based threat intelligence storage."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize the SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main IOC table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                indicator_type TEXT NOT NULL,
                value TEXT NOT NULL,
                value_hash TEXT NOT NULL,
                threat_type TEXT,
                malware_family TEXT,
                source TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                confidence INTEGER DEFAULT 50,
                severity TEXT DEFAULT 'medium',
                tags TEXT,
                reference_url TEXT,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(value_hash, source)
            )
        ''')

        # Index for fast lookups
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_value_hash ON indicators(value_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_indicator_type ON indicators(indicator_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_severity ON indicators(severity)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON indicators(source)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_seen ON indicators(last_seen)')

        # Feed sync tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feed_sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feed_source TEXT NOT NULL,
                sync_time TEXT NOT NULL,
                indicators_added INTEGER DEFAULT 0,
                indicators_updated INTEGER DEFAULT 0,
                status TEXT,
                error_message TEXT
            )
        ''')

        # Alert history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                indicator_value TEXT NOT NULL,
                indicator_type TEXT NOT NULL,
                context TEXT,
                severity TEXT,
                alert_time TEXT NOT NULL,
                acknowledged BOOLEAN DEFAULT 0
            )
        ''')

        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")

    def _hash_value(self, value: str) -> str:
        """Create consistent hash of indicator value for deduplication."""
        normalized = value.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]

    def add_indicator(self, indicator: ThreatIndicator) -> bool:
        """Add or update a threat indicator."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        value_hash = self._hash_value(indicator.value)
        now = datetime.utcnow().isoformat()
        tags_json = json.dumps(indicator.tags) if indicator.tags else "[]"

        try:
            cursor.execute('''
                INSERT INTO indicators
                (indicator_type, value, value_hash, threat_type, malware_family,
                 source, first_seen, last_seen, confidence, severity, tags,
                 reference_url, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(value_hash, source) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    confidence = excluded.confidence,
                    tags = excluded.tags,
                    updated_at = excluded.updated_at
            ''', (
                indicator.indicator_type, indicator.value, value_hash,
                indicator.threat_type, indicator.malware_family, indicator.source,
                indicator.first_seen, indicator.last_seen, indicator.confidence,
                indicator.severity, tags_json, indicator.reference_url,
                indicator.description, now, now
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to add indicator: {e}")
            return False
        finally:
            conn.close()

    def lookup(self, value: str) -> List[ThreatIndicator]:
        """Look up an indicator by value."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        value_hash = self._hash_value(value)

        cursor.execute('''
            SELECT indicator_type, value, threat_type, malware_family, source,
                   first_seen, last_seen, confidence, severity, tags,
                   reference_url, description
            FROM indicators
            WHERE value_hash = ?
            ORDER BY confidence DESC, last_seen DESC
        ''', (value_hash,))

        results = []
        for row in cursor.fetchall():
            tags = json.loads(row[9]) if row[9] else []
            results.append(ThreatIndicator(
                indicator_type=row[0],
                value=row[1],
                threat_type=row[2],
                malware_family=row[3],
                source=row[4],
                first_seen=row[5],
                last_seen=row[6],
                confidence=row[7],
                severity=row[8],
                tags=tags,
                reference_url=row[10],
                description=row[11]
            ))

        conn.close()
        return results

    def search(self, query: str, indicator_type: Optional[str] = None,
               severity: Optional[str] = None, limit: int = 100) -> List[ThreatIndicator]:
        """Search indicators by partial match."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        sql = "SELECT * FROM indicators WHERE value LIKE ?"
        params = [f"%{query}%"]

        if indicator_type:
            sql += " AND indicator_type = ?"
            params.append(indicator_type)

        if severity:
            sql += " AND severity = ?"
            params.append(severity)

        sql += " ORDER BY confidence DESC, last_seen DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)

        results = []
        for row in cursor.fetchall():
            tags = json.loads(row[10]) if row[10] else []
            results.append(ThreatIndicator(
                indicator_type=row[1],
                value=row[2],
                threat_type=row[4],
                malware_family=row[5],
                source=row[6],
                first_seen=row[7],
                last_seen=row[8],
                confidence=row[9],
                severity=row[10] if isinstance(row[10], str) else "medium",
                tags=tags,
                reference_url=row[12],
                description=row[13]
            ))

        conn.close()
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {}

        # Total indicators
        cursor.execute("SELECT COUNT(*) FROM indicators")
        stats["total_indicators"] = cursor.fetchone()[0]

        # By type
        cursor.execute("""
            SELECT indicator_type, COUNT(*)
            FROM indicators
            GROUP BY indicator_type
        """)
        stats["by_type"] = dict(cursor.fetchall())

        # By source
        cursor.execute("""
            SELECT source, COUNT(*)
            FROM indicators
            GROUP BY source
        """)
        stats["by_source"] = dict(cursor.fetchall())

        # By severity
        cursor.execute("""
            SELECT severity, COUNT(*)
            FROM indicators
            GROUP BY severity
        """)
        stats["by_severity"] = dict(cursor.fetchall())

        # Recent indicators (last 24h)
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM indicators
            WHERE created_at > ?
        """, (yesterday,))
        stats["added_last_24h"] = cursor.fetchone()[0]

        # Last sync times
        cursor.execute("""
            SELECT feed_source, MAX(sync_time), indicators_added
            FROM feed_sync_history
            GROUP BY feed_source
        """)
        stats["last_syncs"] = {row[0]: {"time": row[1], "added": row[2]}
                               for row in cursor.fetchall()}

        conn.close()
        return stats

    def record_sync(self, source: str, added: int, updated: int,
                    status: str, error: Optional[str] = None):
        """Record a feed sync operation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO feed_sync_history
            (feed_source, sync_time, indicators_added, indicators_updated, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (source, datetime.utcnow().isoformat(), added, updated, status, error))

        conn.commit()
        conn.close()

    def record_alert(self, indicator_value: str, indicator_type: str,
                     context: str, severity: str):
        """Record when a threat is detected."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO alert_history
            (indicator_value, indicator_type, context, severity, alert_time)
            VALUES (?, ?, ?, ?, ?)
        ''', (indicator_value, indicator_type, context, severity,
              datetime.utcnow().isoformat()))

        conn.commit()
        conn.close()


class ThreatFeedFetcher:
    """Fetches and parses threat intelligence feeds."""

    def __init__(self, db: ThreatIntelDatabase):
        self.db = db
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=60)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self):
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def fetch_threatfox(self) -> Tuple[int, int]:
        """Fetch IOCs from ThreatFox public export."""
        logger.info("Fetching ThreatFox feed...")
        session = await self._get_session()
        added = updated = 0
        now = datetime.now(timezone.utc).isoformat()

        try:
            # Use public JSON export (no auth required)
            async with session.get(FEED_URLS[FeedSource.THREATFOX]) as resp:
                if resp.status != 200:
                    raise Exception(f"ThreatFox returned {resp.status}")

                data = await resp.json()

                # Handle both array and object responses
                if isinstance(data, list):
                    iocs = data
                elif isinstance(data, dict):
                    iocs = data.get("data", data.get("iocs", []))
                else:
                    iocs = []

                logger.info(f"ThreatFox returned {len(iocs)} IOCs")

                for ioc in iocs[:5000]:  # Limit to 5000
                    if not isinstance(ioc, dict):
                        continue

                    indicator = ThreatIndicator(
                        indicator_type=self._map_threatfox_type(ioc.get("ioc_type", "")),
                        value=ioc.get("ioc", ioc.get("ioc_value", "")),
                        threat_type=ioc.get("threat_type", "malware"),
                        malware_family=ioc.get("malware_printable", ioc.get("malware", "")),
                        source=FeedSource.THREATFOX.value,
                        first_seen=ioc.get("first_seen_utc", ioc.get("first_seen", now)),
                        last_seen=ioc.get("last_seen_utc", now),
                        confidence=self._map_confidence(ioc.get("confidence_level", 75)),
                        severity=self._map_threatfox_severity(ioc.get("threat_type", "")),
                        tags=ioc.get("tags", []) or [],
                        reference_url=ioc.get("reference"),
                        description=ioc.get("malware_alias", ioc.get("reporter", ""))
                    )

                    if indicator.value and self.db.add_indicator(indicator):
                        added += 1

                self.db.record_sync(FeedSource.THREATFOX.value, added, updated, "success")
                logger.info(f"ThreatFox sync complete: {added} added")

        except Exception as e:
            logger.error(f"ThreatFox fetch failed: {e}")
            self.db.record_sync(FeedSource.THREATFOX.value, 0, 0, "error", str(e))

        return added, updated

    async def fetch_urlhaus(self) -> Tuple[int, int]:
        """Fetch malicious URLs from URLhaus CSV export."""
        logger.info("Fetching URLhaus feed...")
        session = await self._get_session()
        added = updated = 0
        now = datetime.now(timezone.utc).isoformat()

        try:
            async with session.get(FEED_URLS[FeedSource.URLHAUS]) as resp:
                if resp.status != 200:
                    raise Exception(f"URLhaus returned {resp.status}")

                text = await resp.text()

                # Parse CSV format: id,dateadded,url,url_status,last_online,threat,tags,urlhaus_link,reporter
                # Columns: 0=id, 1=dateadded, 2=url, 3=url_status, 4=last_online, 5=threat, 6=tags, 7=urlhaus_link, 8=reporter
                lines = text.strip().split('\n')
                logger.info(f"URLhaus returned {len(lines)} lines")

                for line in lines[9:5009]:  # Skip header (first 9 lines), limit to 5000
                    if line.startswith('#') or not line.strip():
                        continue

                    # Parse CSV (handle quoted fields)
                    parts = line.split('","')
                    if len(parts) < 6:  # Need at least up to threat field
                        continue

                    try:
                        # Clean up CSV parsing - FIXED: Correct column indices
                        date_added = parts[1].strip('"') if len(parts) > 1 else now
                        url = parts[2].strip('"') if len(parts) > 2 else ""
                        url_status = parts[3].strip('"') if len(parts) > 3 else "unknown"
                        threat_type = parts[5].strip('"') if len(parts) > 5 else "malware_download"  # Index 5 = threat
                        tags_str = parts[6].strip('"') if len(parts) > 6 else ""  # Index 6 = tags
                        urlhaus_ref = parts[7].strip('"') if len(parts) > 7 else ""  # Index 7 = urlhaus_link
                        reporter = parts[8].strip('"') if len(parts) > 8 else ""  # Index 8 = reporter

                        tags = [t.strip() for t in tags_str.split(',') if t.strip()] if tags_str else []

                        # Build descriptive description with actual threat info
                        desc_parts = [f"Threat: {threat_type}"]
                        if tags:
                            desc_parts.append(f"Malware: {', '.join(tags[:3])}")  # First 3 tags
                        if url_status:
                            desc_parts.append(f"Status: {url_status}")
                        if reporter:
                            desc_parts.append(f"Reporter: {reporter}")

                        indicator = ThreatIndicator(
                            indicator_type=ThreatType.URL.value,
                            value=url,
                            threat_type=threat_type,
                            malware_family=tags[0] if tags else None,
                            source=FeedSource.URLHAUS.value,
                            first_seen=date_added,
                            last_seen=now,
                            confidence=80,
                            severity=ThreatSeverity.HIGH.value,
                            tags=tags,
                            reference_url=urlhaus_ref,
                            description=" | ".join(desc_parts)
                        )

                        if url and self.db.add_indicator(indicator):
                            added += 1

                    except (IndexError, ValueError) as e:
                        continue  # Skip malformed lines

                self.db.record_sync(FeedSource.URLHAUS.value, added, updated, "success")
                logger.info(f"URLhaus sync complete: {added} added")

        except Exception as e:
            logger.error(f"URLhaus fetch failed: {e}")
            self.db.record_sync(FeedSource.URLHAUS.value, 0, 0, "error", str(e))

        return added, updated

    async def fetch_cisa_kev(self) -> Tuple[int, int]:
        """Fetch CISA Known Exploited Vulnerabilities."""
        logger.info("Fetching CISA KEV feed...")
        session = await self._get_session()
        added = updated = 0

        try:
            async with session.get(FEED_URLS[FeedSource.CISA_KEV]) as resp:
                if resp.status != 200:
                    raise Exception(f"CISA KEV returned {resp.status}")

                data = await resp.json()
                vulns = data.get("vulnerabilities", [])
                logger.info(f"CISA KEV returned {len(vulns)} vulnerabilities")

                for vuln in vulns:
                    # Extract additional CISA KEV fields
                    vendor = vuln.get("vendorProject", "")
                    product = vuln.get("product", "")
                    due_date = vuln.get("dueDate", "")
                    ransomware_use = vuln.get("knownRansomwareCampaignUse", "Unknown")
                    vulnerability_name = vuln.get("vulnerabilityName", "")

                    # Build comprehensive tags
                    tags = [t for t in [vendor, product] if t]
                    if ransomware_use and ransomware_use.lower() != "unknown":
                        tags.append(f"ransomware:{ransomware_use}")

                    # Build detailed description
                    desc_parts = []
                    short_desc = vuln.get("shortDescription", "")
                    if short_desc:
                        desc_parts.append(short_desc)
                    if vulnerability_name:
                        desc_parts.append(f"Name: {vulnerability_name}")
                    if due_date:
                        desc_parts.append(f"Remediation Due: {due_date}")
                    if ransomware_use and ransomware_use.lower() != "unknown":
                        desc_parts.append(f"Ransomware Campaign: {ransomware_use}")

                    indicator = ThreatIndicator(
                        indicator_type=ThreatType.CVE.value,
                        value=vuln.get("cveID", ""),
                        threat_type="known_exploited_vulnerability",
                        malware_family=None,
                        source=FeedSource.CISA_KEV.value,
                        first_seen=vuln.get("dateAdded", datetime.utcnow().isoformat()),
                        last_seen=datetime.utcnow().isoformat(),
                        confidence=100,  # CISA KEV is authoritative
                        severity=ThreatSeverity.CRITICAL.value,
                        tags=tags,
                        reference_url=f"https://nvd.nist.gov/vuln/detail/{vuln.get('cveID', '')}",
                        description=" | ".join(desc_parts) if desc_parts else "Known Exploited Vulnerability"
                    )

                    if indicator.value and self.db.add_indicator(indicator):
                        added += 1

                self.db.record_sync(FeedSource.CISA_KEV.value, added, updated, "success")
                logger.info(f"CISA KEV sync complete: {added} added")

        except Exception as e:
            logger.error(f"CISA KEV fetch failed: {e}")
            self.db.record_sync(FeedSource.CISA_KEV.value, 0, 0, "error", str(e))

        return added, updated

    async def fetch_feodo_tracker(self) -> Tuple[int, int]:
        """Fetch botnet C2 IPs from Feodo Tracker."""
        logger.info("Fetching Feodo Tracker feed...")
        session = await self._get_session()
        added = updated = 0
        now = datetime.now(timezone.utc).isoformat()

        try:
            async with session.get(FEED_URLS[FeedSource.FEODO_TRACKER]) as resp:
                if resp.status != 200:
                    raise Exception(f"Feodo Tracker returned {resp.status}")

                data = await resp.json()
                entries = data if isinstance(data, list) else []
                logger.info(f"Feodo Tracker returned {len(entries)} C2 IPs")

                for entry in entries:
                    if isinstance(entry, dict):
                        ip = entry.get("ip_address", entry.get("dst_ip", ""))
                        malware = entry.get("malware", entry.get("malware_printable", "unknown"))
                        first_seen = entry.get("first_seen", now)
                        last_online = entry.get("last_online", first_seen)
                    else:
                        continue

                    indicator = ThreatIndicator(
                        indicator_type=ThreatType.IP.value,
                        value=ip,
                        threat_type="botnet_c2",
                        malware_family=malware,
                        source=FeedSource.FEODO_TRACKER.value,
                        first_seen=first_seen,
                        last_seen=last_online,
                        confidence=90,
                        severity=ThreatSeverity.CRITICAL.value,
                        tags=["botnet", "c2", malware],
                        reference_url="https://feodotracker.abuse.ch/",
                        description=f"Feodo Tracker: {malware} C2 server"
                    )

                    if ip and self.db.add_indicator(indicator):
                        added += 1

                self.db.record_sync(FeedSource.FEODO_TRACKER.value, added, updated, "success")
                logger.info(f"Feodo Tracker sync complete: {added} added")

        except Exception as e:
            logger.error(f"Feodo Tracker fetch failed: {e}")
            self.db.record_sync(FeedSource.FEODO_TRACKER.value, 0, 0, "error", str(e))

        return added, updated

    async def sync_all_feeds(self) -> Dict[str, Tuple[int, int]]:
        """Sync all threat intelligence feeds."""
        logger.info("Starting full feed sync...")
        results = {}

        # Run all fetchers
        results["threatfox"] = await self.fetch_threatfox()
        results["urlhaus"] = await self.fetch_urlhaus()
        results["cisa_kev"] = await self.fetch_cisa_kev()
        results["feodo_tracker"] = await self.fetch_feodo_tracker()

        total_added = sum(r[0] for r in results.values())
        logger.info(f"Full sync complete: {total_added} total indicators added")

        return results

    def _map_threatfox_type(self, ioc_type: str) -> str:
        """Map ThreatFox IOC type to our type."""
        type_map = {
            "ip:port": ThreatType.IP.value,
            "domain": ThreatType.DOMAIN.value,
            "url": ThreatType.URL.value,
            "md5_hash": ThreatType.HASH_MD5.value,
            "sha256_hash": ThreatType.HASH_SHA256.value,
        }
        return type_map.get(ioc_type.lower(), ioc_type)

    def _map_threatfox_severity(self, threat_type: str) -> str:
        """Map ThreatFox threat type to severity."""
        severity_map = {
            "botnet_cc": ThreatSeverity.CRITICAL.value,
            "c2": ThreatSeverity.CRITICAL.value,
            "payload_delivery": ThreatSeverity.HIGH.value,
            "payload": ThreatSeverity.HIGH.value,
        }
        return severity_map.get(threat_type.lower(), ThreatSeverity.MEDIUM.value)

    def _map_confidence(self, confidence: int) -> int:
        """Normalize confidence to 0-100."""
        return max(0, min(100, confidence))


class ThreatChecker:
    """Checks various inputs against threat intelligence."""

    def __init__(self, db: ThreatIntelDatabase):
        self.db = db

        # Regex patterns for extraction
        self.ip_pattern = re.compile(
            r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
            r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
        )
        self.url_pattern = re.compile(
            r'https?://[^\s<>"{}|\\^`\[\]]+'
        )
        self.domain_pattern = re.compile(
            r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'
        )
        self.md5_pattern = re.compile(r'\b[a-fA-F0-9]{32}\b')
        self.sha256_pattern = re.compile(r'\b[a-fA-F0-9]{64}\b')
        self.cve_pattern = re.compile(r'\bCVE-\d{4}-\d{4,}\b', re.IGNORECASE)

    def check_indicator(self, value: str, context: str = "") -> ThreatMatch:
        """Check a single indicator against threat database."""
        matches = self.db.lookup(value)

        if not matches:
            return ThreatMatch(
                found=False,
                indicator=value,
                matches=[],
                risk_score=0,
                recommendation="No known threats found for this indicator."
            )

        # Calculate risk score based on matches
        max_confidence = max(m.confidence for m in matches)
        severity_scores = {
            ThreatSeverity.CRITICAL.value: 100,
            ThreatSeverity.HIGH.value: 75,
            ThreatSeverity.MEDIUM.value: 50,
            ThreatSeverity.LOW.value: 25,
            ThreatSeverity.INFO.value: 10,
        }
        max_severity_score = max(
            severity_scores.get(m.severity, 50) for m in matches
        )

        risk_score = int((max_confidence + max_severity_score) / 2)

        # Generate recommendation
        if risk_score >= 80:
            recommendation = "CRITICAL: This indicator is associated with known malicious activity. Block immediately and investigate."
        elif risk_score >= 60:
            recommendation = "HIGH RISK: This indicator has multiple threat associations. Review and consider blocking."
        elif risk_score >= 40:
            recommendation = "MEDIUM RISK: This indicator appears in threat feeds. Monitor closely."
        else:
            recommendation = "LOW RISK: Limited threat data available. Continue monitoring."

        # Record alert if significant
        if risk_score >= 60:
            self.db.record_alert(
                value,
                matches[0].indicator_type,
                context,
                matches[0].severity
            )

        return ThreatMatch(
            found=True,
            indicator=value,
            matches=matches,
            risk_score=risk_score,
            recommendation=recommendation
        )

    def scan_text(self, text: str, context: str = "") -> Dict[str, List[ThreatMatch]]:
        """Scan text for any IOCs and check them against threat database."""
        results = {
            "ips": [],
            "urls": [],
            "domains": [],
            "hashes": [],
            "cves": [],
        }

        # Extract and check IPs
        for ip in set(self.ip_pattern.findall(text)):
            match = self.check_indicator(ip, context)
            if match.found:
                results["ips"].append(match)

        # Extract and check URLs
        for url in set(self.url_pattern.findall(text)):
            match = self.check_indicator(url, context)
            if match.found:
                results["urls"].append(match)

        # Extract and check domains (exclude common ones)
        common_domains = {"google.com", "github.com", "microsoft.com", "apple.com"}
        for domain in set(self.domain_pattern.findall(text)):
            if domain.lower() not in common_domains:
                match = self.check_indicator(domain, context)
                if match.found:
                    results["domains"].append(match)

        # Extract and check hashes
        for hash_val in set(self.md5_pattern.findall(text)):
            match = self.check_indicator(hash_val, context)
            if match.found:
                results["hashes"].append(match)

        for hash_val in set(self.sha256_pattern.findall(text)):
            match = self.check_indicator(hash_val, context)
            if match.found:
                results["hashes"].append(match)

        # Extract and check CVEs
        for cve in set(self.cve_pattern.findall(text)):
            match = self.check_indicator(cve.upper(), context)
            if match.found:
                results["cves"].append(match)

        return results


# Initialize components
db = ThreatIntelDatabase()
fetcher = ThreatFeedFetcher(db)
checker = ThreatChecker(db)

# Create MCP server
server = Server("threat-intel-mcp")


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available threat intelligence tools."""
    return [
        Tool(
            name="threat_check",
            description="Check an indicator (IP, URL, domain, hash, CVE) against threat intelligence feeds. Returns risk score and threat details.",
            inputSchema={
                "type": "object",
                "properties": {
                    "indicator": {
                        "type": "string",
                        "description": "The indicator to check (IP, URL, domain, MD5/SHA256 hash, or CVE ID)"
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional context about where this indicator was found"
                    }
                },
                "required": ["indicator"]
            }
        ),
        Tool(
            name="threat_scan_text",
            description="Scan a block of text (logs, code, config) for any known threat indicators. Automatically extracts IPs, URLs, domains, hashes, and CVEs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to scan for threat indicators"
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional context about the source of this text"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="threat_sync_feeds",
            description="Synchronize all threat intelligence feeds (ThreatFox, URLhaus, CISA KEV, Feodo Tracker). Usually runs automatically but can be triggered manually.",
            inputSchema={
                "type": "object",
                "properties": {
                    "feed": {
                        "type": "string",
                        "description": "Optional: specific feed to sync (threatfox, urlhaus, cisa_kev, feodo_tracker). If not specified, syncs all.",
                        "enum": ["threatfox", "urlhaus", "cisa_kev", "feodo_tracker", "all"]
                    }
                }
            }
        ),
        Tool(
            name="threat_stats",
            description="Get threat intelligence database statistics including indicator counts, feed sync status, and recent activity.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="threat_search",
            description="Search threat indicators by partial match, type, or severity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (partial match on indicator value)"
                    },
                    "indicator_type": {
                        "type": "string",
                        "description": "Filter by indicator type",
                        "enum": ["ip", "domain", "url", "hash_md5", "hash_sha256", "cve"]
                    },
                    "severity": {
                        "type": "string",
                        "description": "Filter by severity",
                        "enum": ["critical", "high", "medium", "low", "info"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return (default 50)",
                        "default": 50
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="threat_add_indicator",
            description="Manually add a threat indicator to the database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "indicator_type": {
                        "type": "string",
                        "description": "Type of indicator",
                        "enum": ["ip", "domain", "url", "hash_md5", "hash_sha256", "cve", "email", "filename"]
                    },
                    "value": {
                        "type": "string",
                        "description": "The indicator value"
                    },
                    "threat_type": {
                        "type": "string",
                        "description": "Type of threat (e.g., malware, phishing, c2)"
                    },
                    "severity": {
                        "type": "string",
                        "description": "Severity level",
                        "enum": ["critical", "high", "medium", "low", "info"]
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the threat"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for the indicator"
                    }
                },
                "required": ["indicator_type", "value", "threat_type", "severity"]
            }
        ),
        Tool(
            name="threat_daily_briefing",
            description="Generate a daily threat intelligence briefing summarizing new indicators, top threats, and recommendations.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""

    if name == "threat_check":
        indicator = arguments.get("indicator", "")
        context = arguments.get("context", "")

        result = checker.check_indicator(indicator, context)

        output = {
            "found": result.found,
            "indicator": result.indicator,
            "risk_score": result.risk_score,
            "recommendation": result.recommendation,
            "matches": [asdict(m) for m in result.matches] if result.matches else []
        }

        return [TextContent(type="text", text=json.dumps(output, indent=2))]

    elif name == "threat_scan_text":
        text = arguments.get("text", "")
        context = arguments.get("context", "")

        results = checker.scan_text(text, context)

        # Summarize findings
        total_found = sum(len(v) for v in results.values())

        output = {
            "total_threats_found": total_found,
            "summary": {
                "malicious_ips": len(results["ips"]),
                "malicious_urls": len(results["urls"]),
                "malicious_domains": len(results["domains"]),
                "malicious_hashes": len(results["hashes"]),
                "known_cves": len(results["cves"]),
            },
            "details": {
                category: [
                    {
                        "indicator": m.indicator,
                        "risk_score": m.risk_score,
                        "recommendation": m.recommendation,
                        "threat_types": list(set(match.threat_type for match in m.matches))
                    }
                    for m in matches
                ]
                for category, matches in results.items()
            }
        }

        return [TextContent(type="text", text=json.dumps(output, indent=2))]

    elif name == "threat_sync_feeds":
        feed = arguments.get("feed", "all")

        if feed == "all":
            results = await fetcher.sync_all_feeds()
            output = {
                "status": "success",
                "feeds_synced": {
                    name: {"added": r[0], "updated": r[1]}
                    for name, r in results.items()
                },
                "total_added": sum(r[0] for r in results.values())
            }
        else:
            feed_methods = {
                "threatfox": fetcher.fetch_threatfox,
                "urlhaus": fetcher.fetch_urlhaus,
                "cisa_kev": fetcher.fetch_cisa_kev,
                "feodo_tracker": fetcher.fetch_feodo_tracker,
            }

            if feed in feed_methods:
                added, updated = await feed_methods[feed]()
                output = {
                    "status": "success",
                    "feed": feed,
                    "indicators_added": added,
                    "indicators_updated": updated
                }
            else:
                output = {"status": "error", "message": f"Unknown feed: {feed}"}

        return [TextContent(type="text", text=json.dumps(output, indent=2))]

    elif name == "threat_stats":
        stats = db.get_stats()
        return [TextContent(type="text", text=json.dumps(stats, indent=2))]

    elif name == "threat_search":
        query = arguments.get("query", "")
        indicator_type = arguments.get("indicator_type")
        severity = arguments.get("severity")
        limit = arguments.get("limit", 50)

        results = db.search(query, indicator_type, severity, limit)

        output = {
            "query": query,
            "results_count": len(results),
            "indicators": [asdict(r) for r in results]
        }

        return [TextContent(type="text", text=json.dumps(output, indent=2))]

    elif name == "threat_add_indicator":
        indicator = ThreatIndicator(
            indicator_type=arguments["indicator_type"],
            value=arguments["value"],
            threat_type=arguments["threat_type"],
            malware_family=arguments.get("malware_family"),
            source=FeedSource.MANUAL.value,
            first_seen=datetime.utcnow().isoformat(),
            last_seen=datetime.utcnow().isoformat(),
            confidence=arguments.get("confidence", 80),
            severity=arguments["severity"],
            tags=arguments.get("tags", []),
            reference_url=arguments.get("reference_url"),
            description=arguments.get("description")
        )

        success = db.add_indicator(indicator)

        output = {
            "status": "success" if success else "failed",
            "indicator": asdict(indicator)
        }

        return [TextContent(type="text", text=json.dumps(output, indent=2))]

    elif name == "threat_daily_briefing":
        stats = db.get_stats()

        # Get critical/high severity indicators added in last 24h
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()

        cursor.execute("""
            SELECT indicator_type, value, threat_type, malware_family, severity, source
            FROM indicators
            WHERE created_at > ? AND severity IN ('critical', 'high')
            ORDER BY severity, created_at DESC
            LIMIT 20
        """, (yesterday,))

        critical_indicators = [
            {
                "type": row[0],
                "value": row[1],
                "threat": row[2],
                "malware": row[3],
                "severity": row[4],
                "source": row[5]
            }
            for row in cursor.fetchall()
        ]

        # Get recent alerts
        cursor.execute("""
            SELECT indicator_value, indicator_type, severity, alert_time, context
            FROM alert_history
            WHERE alert_time > ?
            ORDER BY alert_time DESC
            LIMIT 10
        """, (yesterday,))

        recent_alerts = [
            {
                "indicator": row[0],
                "type": row[1],
                "severity": row[2],
                "time": row[3],
                "context": row[4]
            }
            for row in cursor.fetchall()
        ]

        conn.close()

        briefing = {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "summary": {
                "total_indicators": stats["total_indicators"],
                "added_last_24h": stats["added_last_24h"],
                "critical_high_new": len(critical_indicators),
                "alerts_triggered": len(recent_alerts)
            },
            "threat_landscape": {
                "by_type": stats["by_type"],
                "by_severity": stats["by_severity"],
                "by_source": stats["by_source"]
            },
            "new_critical_threats": critical_indicators[:10],
            "recent_alerts": recent_alerts,
            "feed_status": stats["last_syncs"],
            "recommendations": [
                "Review any new critical/high severity indicators",
                "Ensure all feeds synced within last 24 hours",
                "Investigate any triggered alerts",
                "Update blocklists with new C2 IPs"
            ]
        }

        return [TextContent(type="text", text=json.dumps(briefing, indent=2))]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


async def main():
    """Main entry point."""
    logger.info("Starting Threat Intelligence MCP Server...")
    logger.info(f"Database: {DB_PATH}")

    # Initial feed sync on startup (async)
    asyncio.create_task(initial_sync())

    # Run MCP server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


async def initial_sync():
    """Perform initial feed sync after startup."""
    await asyncio.sleep(5)  # Wait for server to stabilize
    logger.info("Performing initial threat feed sync...")
    try:
        await fetcher.sync_all_feeds()
    except Exception as e:
        logger.error(f"Initial sync failed: {e}")
    finally:
        await fetcher.close()


if __name__ == "__main__":
    asyncio.run(main())
