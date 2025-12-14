#!/usr/bin/env python3
"""
Agentic Sound System - Roland-Style Synthesizers with Ambient Sequencer

Comprehensive sound system using Roland-style synthesized sounds to indicate
different agentic actions. Includes drums, bass, keyboards, and system utility sounds.

Features an ambient sequencer that quantizes sounds to a musical grid for fluid,
less jarring audio feedback. Activity sounds blend into ambient soundscape.

Sound Categories:

DRUMS (TR-808/TR-909 Style):
- agent_spawn:      TR-808 Kick (deep bass)
- agent_terminate:  TR-808 Snare (crisp snare)
- task_start:       TR-808 Hi-Hat Closed
- task_complete:    TR-808 Hi-Hat Open
- error:            TR-808 Clap (layered)
- warning:          TR-808 Cowbell
- memory_store:     TR-808 Tom (low)
- memory_retrieve:  TR-808 Tom (high)
- api_call:         TR-808 Rimshot
- cluster_sync:     TR-808 Cymbal (crash)
- health_check:     TR-808 Maracas (tick)
- heartbeat:        Soft metronome pulse

BASS (TB-303 Style):
- workflow_start:   TB-303 Acid Bass (resonant sweep)
- workflow_end:     TB-303 Sub Bass (deep fundamental)
- ai_inference:     TB-303 Squelch Bass (filter modulation)
- model_load:       TB-303 Pluck Bass (sharp attack)
- database_query:   TB-303 Growl Bass (distorted)

KEYBOARDS (Juno/Jupiter Style):
- session_start:    Jupiter Pad (warm evolving)
- session_end:      Jupiter Strings (orchestral sweep)
- success:          Juno Stab (bright chord)
- notification:     Juno Bell (crystalline)
- thinking:         Jupiter Arp (sequenced pattern)
- voice_activity:   Juno Lead (monophonic)
- cluster_message:  Jupiter Brass (fanfare)

SYSTEM UTILITY (Claude Code Operations):
- context_compact:     Descending sweep (compression feel)
- file_read:           Quick ascending blip
- file_write:          Quick descending blip
- tool_call:           Mechanical click sequence
- memory_consolidate:  Dreamy sleep-like pad
- code_execute:        Digital/mechanical processing
- search:              Scanning sweep sound
- web_fetch:           Network transmission chirp
- cache_hit:           Quick positive ding
- cache_miss:          Quick negative buzz
- planning:            Thoughtful ascending arpeggio
- streaming:           Continuous flowing sound
- token_limit:         Urgent descending warning
- agent_thinking:      Gentle pulsing meditation
- permission_request:  Attention-getting two-tone
- git_commit:          Satisfying lock-in click

AMBIENT SEQUENCER:
- Quantizes sounds to musical grid (eighth notes by default)
- 75 BPM default for chill ambient feel
- Activity-aware: more ambient when idle, responsive when active
- Background ambient layer plays contextually
- HTTP control: /sequencer endpoint for start/stop/bpm/ambient/quantize
"""

import asyncio
import json
import time
import os
import sys
import math
import struct
import wave
from pathlib import Path
from typing import Dict, Optional, Callable, List, Tuple
from dataclasses import dataclass, field
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import subprocess
import urllib.request
import signal
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import random
from collections import deque


# Sound synthesis parameters
SAMPLE_RATE = 44100
CHANNELS = 2  # STEREO for spatial audio!
SAMPLE_WIDTH = 2  # 16-bit


# ============================================================================
# MUSICAL THEORY ENGINE - Chord Progressions & Scales
# ============================================================================

class Scale(Enum):
    """Musical scales for melodic content."""
    MAJOR = [0, 2, 4, 5, 7, 9, 11]
    MINOR = [0, 2, 3, 5, 7, 8, 10]
    DORIAN = [0, 2, 3, 5, 7, 9, 10]  # Great for tech-house
    MIXOLYDIAN = [0, 2, 4, 5, 7, 9, 10]  # Funky
    PENTATONIC = [0, 2, 4, 7, 9]  # Safe for ambient
    BLUES = [0, 3, 5, 6, 7, 10]


class ChordType(Enum):
    """Chord types for harmonic progressions."""
    MAJOR = [0, 4, 7]
    MINOR = [0, 3, 7]
    SEVENTH = [0, 4, 7, 10]
    MINOR_SEVENTH = [0, 3, 7, 10]
    MAJOR_SEVENTH = [0, 4, 7, 11]
    SUS2 = [0, 2, 7]
    SUS4 = [0, 5, 7]
    ADD9 = [0, 4, 7, 14]


# Common chord progressions by mood
CHORD_PROGRESSIONS = {
    'ambient': [
        [(0, 'major'), (5, 'major'), (3, 'minor'), (4, 'major')],  # I-V-vi-IV
        [(0, 'major'), (4, 'major'), (5, 'major'), (0, 'major')],  # I-IV-V-I
        [(3, 'minor'), (4, 'major'), (0, 'major'), (0, 'major')],  # vi-IV-I-I
    ],
    'tension': [
        [(0, 'minor'), (5, 'minor'), (4, 'major'), (0, 'minor')],  # i-v-IV-i
        [(0, 'minor'), (3, 'major'), (5, 'minor'), (4, 'major')],  # i-III-v-IV
        [(0, 'minor7'), (1, 'minor7'), (2, 'minor7'), (5, 'dom7')],  # ii-V-I jazz
    ],
    'triumphant': [
        [(0, 'major'), (4, 'major'), (5, 'major'), (5, 'major')],  # I-IV-V-V (build)
        [(4, 'major'), (5, 'major'), (0, 'major'), (0, 'major')],  # IV-V-I-I (resolution)
    ],
    'driving': [
        [(0, 'minor'), (0, 'minor'), (5, 'minor'), (4, 'major')],  # i-i-v-IV (tech)
        [(0, 'minor'), (3, 'major'), (4, 'major'), (5, 'minor')],  # i-III-IV-v
    ]
}


# ============================================================================
# GENRE/MOOD PRESETS - Different vibes for different work states
# ============================================================================

@dataclass
class GenrePreset:
    """Musical genre configuration for the soundtrack."""
    name: str
    bpm_range: Tuple[int, int]  # Min/max BPM
    base_key: int  # MIDI note for root (60 = C4)
    scale: Scale
    chord_mood: str  # Key into CHORD_PROGRESSIONS
    drum_density: float  # 0-1, how busy the drums
    bass_prominence: float  # 0-1, how much bass
    pad_sustain: float  # How long pads ring
    swing: float  # 0-1, rhythmic swing
    reverb_amount: float  # 0-1
    delay_feedback: float  # 0-1
    master_volume: float = 0.3  # 0-1, overall volume (SUBTLE by default!)
    pad_prominence: float = 0.5  # 0-1, how much pads are emphasized


# FINAL FANTASY STYLE - Subtle, adaptive soundtrack that builds with activity
# All presets tuned for BACKGROUND music - never intrusive!

GENRE_PRESETS = {
    # === CALM/PEACEFUL MODES (idle, light work) ===
    'ambient': GenrePreset(
        name='Ambient Calm',
        bpm_range=(55, 70),
        base_key=48,  # C3
        scale=Scale.PENTATONIC,
        chord_mood='ambient',
        drum_density=0.1,  # Very sparse drums
        bass_prominence=0.2,
        pad_sustain=4.0,  # Long, lush pads
        swing=0.0,
        reverb_amount=0.85,
        delay_feedback=0.7,
        master_volume=0.5,  # Audible background
        pad_prominence=0.8  # Pads dominate
    ),
    'lofi': GenrePreset(
        name='Lo-Fi Chill',
        bpm_range=(65, 80),
        base_key=55,  # G3
        scale=Scale.MINOR,
        chord_mood='ambient',
        drum_density=0.18,  # Gentle occasional beat
        bass_prominence=0.3,
        pad_sustain=2.0,
        swing=0.18,  # Relaxed feel
        reverb_amount=0.5,
        delay_feedback=0.4,
        master_volume=0.55,
        pad_prominence=0.65
    ),

    # === WORKING MODES (moderate activity) ===
    'minimal': GenrePreset(
        name='Minimal Focus',
        bpm_range=(60, 80),  # Slower, more relaxed
        base_key=48,  # C3
        scale=Scale.MAJOR,
        chord_mood='ambient',
        drum_density=0.25,  # Light rhythmic pulse
        bass_prominence=0.3,
        pad_sustain=1.5,
        swing=0.0,
        reverb_amount=0.5,
        delay_feedback=0.25,
        master_volume=0.55,
        pad_prominence=0.55
    ),
    'synthwave': GenrePreset(
        name='Synthwave Flow',
        bpm_range=(75, 92),  # Slower, groove-oriented
        base_key=50,  # D3
        scale=Scale.MINOR,
        chord_mood='tension',
        drum_density=0.35,  # Moderate beat
        bass_prominence=0.45,
        pad_sustain=2.5,
        swing=0.0,
        reverb_amount=0.65,
        delay_feedback=0.5,
        master_volume=0.6,
        pad_prominence=0.6
    ),

    # === INTENSE MODES (high activity - battle scene vibes) ===
    'tech_house': GenrePreset(
        name='Tech Focus',
        bpm_range=(90, 105),  # Calmer, still driving
        base_key=43,  # G2
        scale=Scale.DORIAN,
        chord_mood='driving',
        drum_density=0.45,  # Driving beat
        bass_prominence=0.55,
        pad_sustain=0.8,
        swing=0.05,
        reverb_amount=0.35,
        delay_feedback=0.4,
        master_volume=0.6,
        pad_prominence=0.4
    ),
    'epic': GenrePreset(
        name='Epic Battle',
        bpm_range=(78, 95),  # More deliberate, dramatic
        base_key=45,  # A2
        scale=Scale.MINOR,
        chord_mood='triumphant',
        drum_density=0.4,  # Driving but not overwhelming
        bass_prominence=0.5,
        pad_sustain=2.0,  # Dramatic pads
        swing=0.0,
        reverb_amount=0.7,
        delay_feedback=0.55,
        master_volume=0.65,
        pad_prominence=0.55
    ),

    # === SPECIAL FF-STYLE ADAPTIVE PRESETS ===
    'ff_prelude': GenrePreset(
        name='FF Prelude',  # Crystal theme vibes
        bpm_range=(50, 65),
        base_key=60,  # C4 - higher, crystalline
        scale=Scale.MAJOR,
        chord_mood='ambient',
        drum_density=0.05,  # Very sparse soft percussion
        bass_prominence=0.15,
        pad_sustain=5.0,  # Very long ethereal pads
        swing=0.0,
        reverb_amount=0.9,
        delay_feedback=0.75,
        master_volume=0.5,  # Audible but gentle
        pad_prominence=0.95  # Almost all pads
    ),
    'ff_field': GenrePreset(
        name='FF Field Theme',  # Calm exploration - subtle background
        bpm_range=(70, 80),  # Narrower range centered on 75
        base_key=53,  # F3
        scale=Scale.PENTATONIC,
        chord_mood='ambient',
        drum_density=0.08,  # Very sparse, gentle percussion
        bass_prominence=0.18,  # Subtle bass presence
        pad_sustain=4.0,  # Longer, more ethereal pads
        swing=0.05,  # Minimal swing
        reverb_amount=0.75,  # More reverb for dreaminess
        delay_feedback=0.6,
        master_volume=0.40,  # Lower - true background level
        pad_prominence=0.85  # Mostly pads, very atmospheric
    ),
    'ff_boss': GenrePreset(
        name='FF Boss Battle',  # Intense but still background
        bpm_range=(95, 115),  # Slower but intense - classic FF boss tempo
        base_key=41,  # F2 - low, powerful
        scale=Scale.MINOR,
        chord_mood='tension',
        drum_density=0.50,  # Driving but not frantic
        bass_prominence=0.60,
        pad_sustain=1.2,
        swing=0.0,
        reverb_amount=0.45,
        delay_feedback=0.35,
        master_volume=0.60,  # Battle energy without overwhelming
        pad_prominence=0.45
    )
}


# ============================================================================
# INTELLIGENT DRUM PATTERN ENGINE
# ============================================================================

@dataclass
class DrumPattern:
    """A drum pattern with per-instrument step sequences."""
    name: str
    steps: int  # Typically 16 or 32
    kick: List[float]  # 0-1 velocity per step
    snare: List[float]
    hihat: List[float]
    hihat_open: List[float]
    clap: List[float]
    perc: List[float]  # Generic percussion
    swing: float = 0.0


# Classic patterns
DRUM_PATTERNS = {
    'four_on_floor': DrumPattern(
        name='Four on Floor',
        steps=16,
        kick=[1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
        snare=[0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        hihat=[1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
        hihat_open=[0,0,0,0, 0,0,0,1, 0,0,0,0, 0,0,0,1],
        clap=[0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        perc=[0,0,0,0, 0,0,1,0, 0,0,0,0, 0,0,1,0],
    ),
    'breakbeat': DrumPattern(
        name='Breakbeat',
        steps=16,
        kick=[1,0,0,0, 0,0,1,0, 0,0,1,0, 0,0,0,0],
        snare=[0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,1],
        hihat=[1,1,1,1, 1,1,1,1, 1,1,1,1, 1,1,1,1],
        hihat_open=[0,0,0,0, 0,0,0,0, 0,1,0,0, 0,0,0,0],
        clap=[0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        perc=[0,0,0,1, 0,0,0,0, 0,0,0,1, 0,0,0,0],
        swing=0.1
    ),
    'ambient_minimal': DrumPattern(
        name='Ambient Minimal',
        steps=16,
        kick=[1,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0],
        snare=[0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0],
        hihat=[0,0,1,0, 0,0,1,0, 0,0,1,0, 0,0,1,0],
        hihat_open=[0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,1],
        clap=[0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0],
        perc=[0,0,0,0, 0,0,0,0, 0,0,0,0, 0,1,0,0],
    ),
    'lofi_groove': DrumPattern(
        name='Lo-Fi Groove',
        steps=16,
        kick=[1,0,0,0, 0,0,0,0, 1,0,1,0, 0,0,0,0],
        snare=[0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        hihat=[1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
        hihat_open=[0,0,0,1, 0,0,0,0, 0,0,0,1, 0,0,0,0],
        clap=[0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0],
        perc=[0,1,0,0, 0,0,0,1, 0,1,0,0, 0,0,0,0],
        swing=0.15
    ),
    'tech_driving': DrumPattern(
        name='Tech Driving',
        steps=16,
        kick=[1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
        snare=[0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0],
        hihat=[1,1,1,1, 1,1,1,1, 1,1,1,1, 1,1,1,1],
        hihat_open=[0,0,0,0, 0,0,0,0, 0,0,1,0, 0,0,0,0],
        clap=[0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        perc=[0,0,1,0, 0,0,0,0, 0,0,1,0, 0,0,0,0],
    ),
    'silent': DrumPattern(
        name='Silent',
        steps=16,
        kick=[0]*16,
        snare=[0]*16,
        hihat=[0]*16,
        hihat_open=[0]*16,
        clap=[0]*16,
        perc=[0]*16,
    )
}


# ============================================================================
# SELF-LEARNING MUSICAL INTELLIGENCE
# ============================================================================

class MusicLearner:
    """Self-learning system for musical pattern optimization.

    Tracks which patterns, genres, and settings produce good results,
    then adjusts weights to improve musicality over time.
    """

    def __init__(self, learning_rate: float = 0.1):
        self.learning_rate = learning_rate

        # Pattern affinity scores (learned preferences)
        self.pattern_scores: Dict[str, float] = {}  # pattern_name -> score
        self.genre_scores: Dict[str, float] = {}    # genre_name -> score
        self.transition_scores: Dict[str, float] = {}  # "from_to" -> score

        # Session tracking
        self.current_session: Dict[str, Any] = {
            'patterns_played': [],
            'genres_played': [],
            'transitions': [],
            'start_time': time.time(),
            'positive_feedback': 0,
            'negative_feedback': 0
        }

        # Load learned preferences from file
        self.preferences_file = Path.home() / '.claude' / 'soundtrack_preferences.json'
        self._load_preferences()

    def _load_preferences(self):
        """Load learned preferences from disk."""
        try:
            if self.preferences_file.exists():
                with open(self.preferences_file) as f:
                    data = json.load(f)
                    self.pattern_scores = data.get('patterns', {})
                    self.genre_scores = data.get('genres', {})
                    self.transition_scores = data.get('transitions', {})
                    print(f"🎵 Loaded music preferences: {len(self.pattern_scores)} patterns, {len(self.genre_scores)} genres")
        except Exception as e:
            print(f"Could not load preferences: {e}")

    def _save_preferences(self):
        """Save learned preferences to disk."""
        try:
            self.preferences_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.preferences_file, 'w') as f:
                json.dump({
                    'patterns': self.pattern_scores,
                    'genres': self.genre_scores,
                    'transitions': self.transition_scores,
                    'updated_at': time.time()
                }, f, indent=2)
        except Exception as e:
            print(f"Could not save preferences: {e}")

    def record_pattern(self, pattern_name: str, genre: str):
        """Record that a pattern was played in current session."""
        self.current_session['patterns_played'].append(pattern_name)
        self.current_session['genres_played'].append(genre)

    def record_transition(self, from_genre: str, to_genre: str):
        """Record a genre transition."""
        key = f"{from_genre}->{to_genre}"
        self.current_session['transitions'].append(key)

    def feedback_positive(self):
        """User liked current music (explicit or implicit)."""
        self.current_session['positive_feedback'] += 1
        self._reinforce_current_session(positive=True)

    def feedback_negative(self):
        """User didn't like current music."""
        self.current_session['negative_feedback'] += 1
        self._reinforce_current_session(positive=False)

    def _reinforce_current_session(self, positive: bool):
        """Update scores based on feedback."""
        delta = self.learning_rate if positive else -self.learning_rate * 0.5

        # Update pattern scores
        recent_patterns = self.current_session['patterns_played'][-10:]
        for pattern in recent_patterns:
            current = self.pattern_scores.get(pattern, 0.5)
            self.pattern_scores[pattern] = max(0.1, min(1.0, current + delta))

        # Update genre scores
        recent_genres = self.current_session['genres_played'][-5:]
        for genre in recent_genres:
            current = self.genre_scores.get(genre, 0.5)
            self.genre_scores[genre] = max(0.1, min(1.0, current + delta))

        # Update transition scores
        recent_transitions = self.current_session['transitions'][-3:]
        for trans in recent_transitions:
            current = self.transition_scores.get(trans, 0.5)
            self.transition_scores[trans] = max(0.1, min(1.0, current + delta))

        # Save periodically
        if random.random() < 0.3:
            self._save_preferences()

    def get_pattern_weight(self, pattern_name: str) -> float:
        """Get learned weight for a pattern (affects selection probability)."""
        return self.pattern_scores.get(pattern_name, 0.5)

    def get_genre_affinity(self, genre: str) -> float:
        """Get learned affinity for a genre."""
        return self.genre_scores.get(genre, 0.5)

    def should_transition(self, from_genre: str, to_genre: str) -> bool:
        """Decide if transition is good based on learning."""
        key = f"{from_genre}->{to_genre}"
        score = self.transition_scores.get(key, 0.5)
        # Higher score = more likely to allow transition
        return random.random() < score

    def auto_feedback_from_eval(self, eval_data: dict):
        """Automatically generate feedback from eval metrics.

        High action success + low errors = positive feedback
        This allows the system to learn what music works during productive sessions.
        """
        # Check for positive indicators
        intensity_accuracy = eval_data.get('intensity', {}).get('accuracy', 0.5)
        events_per_min = eval_data.get('workload', {}).get('events_per_minute', 0)

        # Good session = high accuracy and steady activity
        if intensity_accuracy > 0.8 and events_per_min > 5:
            # Implicit positive - session is going well
            if random.random() < 0.1:  # Don't over-reinforce
                self._reinforce_current_session(positive=True)

    def get_stats(self) -> dict:
        """Get learning statistics."""
        return {
            'patterns_learned': len(self.pattern_scores),
            'genres_learned': len(self.genre_scores),
            'transitions_learned': len(self.transition_scores),
            'session_feedback': {
                'positive': self.current_session['positive_feedback'],
                'negative': self.current_session['negative_feedback']
            },
            'top_patterns': sorted(
                self.pattern_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            'top_genres': sorted(
                self.genre_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }


# ============================================================================
# ADAPTIVE WORKLOAD DETECTION
# ============================================================================

@dataclass
class WorkloadState:
    """Tracks agent workload for adaptive music."""
    events_per_minute: float = 0.0
    event_history: deque = field(default_factory=lambda: deque(maxlen=100))
    current_intensity: float = 0.3  # 0-1
    target_intensity: float = 0.3
    last_event_time: float = 0.0

    # Event weights for intensity calculation
    # Higher = more contribution to intensity escalation
    event_weights: Dict[str, float] = field(default_factory=lambda: {
        'heartbeat': 0.02,   # Silent activity bump - almost no intensity change
        'file_read': 0.05,   # Reading is calm
        'file_write': 0.15,  # Writing is a bit more significant
        'search': 0.08,      # Searching is exploratory
        'tool_call': 0.2,    # General tool use
        'code_execute': 0.35,
        'agent_spawn': 0.4,  # Spawning agents is significant
        'ai_inference': 0.5,
        'thinking': 0.3,
        'error': 0.6,        # Errors are notable but not extreme
        'warning': 0.3,
        'success': -0.3,     # Completion lowers intensity
        'task_complete': -0.4,
        'session_start': 0.05,
        'session_end': -0.6,
    })

    def record_event(self, event_type: str):
        """Record an event and update intensity.

        Heartbeats and ambient sounds don't count as real activity
        for decay timing - only significant actions do.
        """
        now = time.time()
        self.event_history.append((now, event_type))

        # Only real actions update the idle timer (not heartbeats/ambient)
        non_idle_events = {'heartbeat', 'pad', 'pad_warm', 'pad_crystal', 'pad_dark'}
        if event_type not in non_idle_events:
            self.last_event_time = now

        # Calculate events per minute (only meaningful events)
        one_minute_ago = now - 60
        meaningful_events = [e for e in self.event_history
                           if e[0] > one_minute_ago and e[1] not in non_idle_events]
        self.events_per_minute = len(meaningful_events)

        # Update target intensity
        weight = self.event_weights.get(event_type, 0.2)
        self.target_intensity = min(1.0, max(0.0, self.target_intensity + weight * 0.1))

    def update(self):
        """Decay intensity toward target over time.

        Aggressive decay for better dynamics - intensity should drop
        noticeably within 10-15 seconds of inactivity.
        """
        # Faster interpolation toward target (was 0.05, too slow)
        self.current_intensity += (self.target_intensity - self.current_intensity) * 0.15

        # Aggressive decay when idle - starts after 2 seconds
        idle_time = time.time() - self.last_event_time
        if idle_time > 2:
            # Decay rate increases with idle time for natural "breakdown"
            # After 2s: 0.90, after 5s: 0.85, after 10s: 0.80
            decay_rate = max(0.80, 0.92 - (idle_time - 2) * 0.015)
            self.target_intensity *= decay_rate

            # Hard floor to ensure we reach idle state
            if self.target_intensity < 0.25:
                self.target_intensity = max(0.1, self.target_intensity * 0.95)

    def get_intensity_level(self) -> str:
        """Get descriptive intensity level.

        Thresholds raised for better dynamic range - requires sustained
        high activity to reach intense mode (FF-style adaptive music).
        """
        if self.current_intensity < 0.35:
            return 'idle'
        elif self.current_intensity < 0.6:
            return 'light'
        elif self.current_intensity < 0.85:
            return 'active'
        else:
            return 'intense'


# ============================================================================
# STEREO SPATIAL AUDIO ENGINE
# ============================================================================

def pan_to_stereo(mono_samples: List[int], pan: float = 0.0) -> Tuple[List[int], List[int]]:
    """Convert mono to stereo with panning.

    Args:
        mono_samples: Mono audio samples
        pan: -1.0 (full left) to 1.0 (full right), 0.0 = center

    Returns:
        Tuple of (left_channel, right_channel)
    """
    # Equal power panning for smooth transitions
    pan_normalized = (pan + 1) / 2  # Convert to 0-1 range
    left_gain = math.cos(pan_normalized * math.pi / 2)
    right_gain = math.sin(pan_normalized * math.pi / 2)

    left = [int(s * left_gain) for s in mono_samples]
    right = [int(s * right_gain) for s in mono_samples]

    return left, right


def interleave_stereo(left: List[int], right: List[int]) -> bytes:
    """Interleave left/right channels for stereo WAV format."""
    stereo_samples = []
    for l, r in zip(left, right):
        stereo_samples.append(l)
        stereo_samples.append(r)
    return struct.pack(f'{len(stereo_samples)}h', *stereo_samples)


# Sound spatial positions (pan values)
SOUND_SPATIAL_MAP = {
    # Drums - spread across stereo field
    'kick': 0.0,        # Center (kick anchors the mix)
    'snare': 0.0,       # Center
    'hihat_closed': 0.3,  # Slightly right
    'hihat_open': 0.4,    # More right
    'clap': -0.1,       # Slightly left
    'tom_low': -0.4,    # Left
    'tom_high': 0.4,    # Right
    'cowbell': 0.5,     # Right
    'rimshot': -0.2,    # Slight left
    'cymbal': 0.0,      # Center (wide)
    'maracas': 0.6,     # Far right
    'heartbeat': 0.0,   # Center

    # Bass - center (mono-compatible)
    'bass_acid': 0.0,
    'bass_sub': 0.0,
    'bass_squelch': 0.0,
    'bass_pluck': 0.0,
    'bass_growl': 0.0,

    # Keys - spread for width
    'pad': 0.0,         # Center (wide)
    'strings': 0.0,     # Center (wide)
    'stab': 0.2,        # Slight right
    'bell': -0.3,       # Left
    'arp': 0.4,         # Right (movement)
    'lead': -0.2,       # Slight left
    'brass': 0.0,       # Center

    # System sounds - positional cues
    'file_read': -0.5,
    'file_write': 0.5,
    'search': 0.0,      # Sweeping
    'tool_call': 0.3,
    'context_compact': 0.0,
    'memory_consolidate': 0.0,
    'code_execute': -0.3,
    'web_fetch': 0.4,
    'cache_hit': 0.2,
    'cache_miss': -0.2,
    'planning': 0.0,
    'streaming': 0.0,
    'token_limit': 0.0,
    'agent_thinking': 0.0,
    'permission_request': 0.0,
    'git_commit': 0.0,
}


# ============================================================================
# EFFECTS PROCESSOR - Reverb, Delay, Compression
# ============================================================================

class EffectsProcessor:
    """Audio effects chain for professional sound."""

    def __init__(self):
        self.reverb_amount = 0.3
        self.delay_time = 0.25  # seconds
        self.delay_feedback = 0.4
        self.compression_threshold = 0.7
        self.compression_ratio = 4.0

    def apply_reverb(self, samples: List[float], amount: float = None,
                     room_size: float = 0.5) -> List[float]:
        """Apply simple algorithmic reverb."""
        if amount is None:
            amount = self.reverb_amount
        if amount <= 0:
            return samples

        # Multiple delay taps for reverb-like effect
        tap_delays = [
            int(SAMPLE_RATE * 0.023 * room_size),  # Early reflections
            int(SAMPLE_RATE * 0.037 * room_size),
            int(SAMPLE_RATE * 0.051 * room_size),
            int(SAMPLE_RATE * 0.073 * room_size),  # Late reflections
            int(SAMPLE_RATE * 0.091 * room_size),
        ]
        tap_gains = [0.5, 0.4, 0.3, 0.2, 0.15]  # Decreasing gains

        result = list(samples)
        for delay, gain in zip(tap_delays, tap_gains):
            for i in range(delay, len(result)):
                result[i] += samples[i - delay] * gain * amount

        return result

    def apply_delay(self, samples: List[float], delay_time: float = None,
                    feedback: float = None) -> List[float]:
        """Apply tempo-synced delay effect."""
        if delay_time is None:
            delay_time = self.delay_time
        if feedback is None:
            feedback = self.delay_feedback

        delay_samples = int(SAMPLE_RATE * delay_time)
        result = list(samples)

        for i in range(delay_samples, len(result)):
            result[i] += result[i - delay_samples] * feedback

        return result

    def apply_compression(self, samples: List[float], threshold: float = None,
                          ratio: float = None) -> List[float]:
        """Apply dynamic range compression."""
        if threshold is None:
            threshold = self.compression_threshold
        if ratio is None:
            ratio = self.compression_ratio

        result = []
        for sample in samples:
            abs_sample = abs(sample)
            if abs_sample > threshold:
                # Compress signal above threshold
                over = abs_sample - threshold
                compressed_over = over / ratio
                new_level = threshold + compressed_over
                sign = 1 if sample >= 0 else -1
                result.append(sign * new_level)
            else:
                result.append(sample)

        return result

    def apply_soft_clip(self, samples: List[float], drive: float = 1.0) -> List[float]:
        """Apply soft clipping/saturation for warmth."""
        return [math.tanh(s * drive) for s in samples]

    def process_chain(self, samples: List[float],
                      reverb: bool = True, delay: bool = False,
                      compress: bool = True,
                      genre_preset: GenrePreset = None) -> List[float]:
        """Apply full effects chain based on genre preset."""
        result = samples

        if genre_preset:
            if compress:
                result = self.apply_compression(result)
            if reverb and genre_preset.reverb_amount > 0:
                result = self.apply_reverb(result, genre_preset.reverb_amount)
            if delay and genre_preset.delay_feedback > 0:
                result = self.apply_delay(result, feedback=genre_preset.delay_feedback)
        else:
            if compress:
                result = self.apply_compression(result)
            if reverb:
                result = self.apply_reverb(result)
            if delay:
                result = self.apply_delay(result)

        # Final soft clip to prevent harsh clipping
        result = self.apply_soft_clip(result, 0.8)

        return result


# Global effects processor instance
EFFECTS = EffectsProcessor()


# ============================================================================
# ENHANCED SYNTHESIZER SOUNDS - Moog, Juno-60, Jupiter-8, Prophet-5
# ============================================================================

class MoogSynthesizer:
    """Authentic Moog-style synthesizer sounds.

    Features the iconic Moog ladder filter, fat oscillators,
    and creamy analog warmth. Perfect for bass and leads.
    """

    def __init__(self, sounds_dir: str = None):
        self.sounds_dir = Path(sounds_dir) if sounds_dir else Path(__file__).parent.parent / "sounds"
        self.sounds_dir.mkdir(exist_ok=True)
        self.sounds: Dict[str, str] = {}

    def _save_wav(self, name: str, samples: bytes) -> str:
        """Save samples as WAV file."""
        filepath = self.sounds_dir / f"{name}.wav"
        with wave.open(str(filepath), 'w') as wav:
            wav.setnchannels(1)  # Mono
            wav.setsampwidth(SAMPLE_WIDTH)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(samples)
        return str(filepath)

    def _moog_ladder_filter(self, samples: List[float], cutoff: float,
                            resonance: float, env_mod: List[float] = None) -> List[float]:
        """Authentic 4-pole Moog ladder filter simulation."""
        result = []
        # 4-pole cascade state
        stage = [0.0, 0.0, 0.0, 0.0]

        for i, sample in enumerate(samples):
            # Modulate cutoff with envelope
            fc = cutoff
            if env_mod and i < len(env_mod):
                fc = cutoff * (1 + env_mod[i] * 4)

            # Limit cutoff
            fc = min(fc, SAMPLE_RATE / 2 - 500)
            fc = max(fc, 20)

            # Calculate filter coefficient
            f = 2 * math.sin(math.pi * fc / SAMPLE_RATE)
            k = resonance * 4  # Resonance feedback

            # Ladder filter topology with feedback
            input_sample = sample - k * stage[3]  # Feedback from output

            # 4 cascaded one-pole stages
            for j in range(4):
                stage[j] += f * (math.tanh(input_sample) - math.tanh(stage[j]))
                input_sample = stage[j]

            result.append(stage[3])

        return result

    def generate_moog_bass(self) -> str:
        """Fat Moog bass with ladder filter sweep - the classic sound."""
        duration = 0.6
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        base_freq = 41.2  # E1 - deep

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Three detuned sawtooth oscillators for fat sound
            saw1 = 2 * ((base_freq * t) % 1) - 1
            saw2 = 2 * ((base_freq * 1.003 * t) % 1) - 1
            saw3 = 2 * ((base_freq * 0.997 * t) % 1) - 1
            # Sub oscillator (one octave down, square)
            sub = 1 if ((base_freq * 0.5 * t) % 1) < 0.5 else -1
            value = (saw1 + saw2 + saw3) / 3 * 0.7 + sub * 0.3
            samples.append(value)

        # Create filter envelope - fast attack, medium decay
        env = []
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            if t < 0.01:
                env.append(t / 0.01)
            else:
                env.append(math.exp(-(t - 0.01) / 0.15))

        # Apply Moog ladder filter
        filtered = self._moog_ladder_filter(samples, 150, 0.7, env)

        # Amplitude envelope
        result = []
        for i, sample in enumerate(filtered):
            t = i / SAMPLE_RATE
            amp = math.exp(-t * 3)
            value = int(math.tanh(sample * 1.5) * amp * 32767 * 0.8)
            result.append(max(-32767, min(32767, value)))

        return self._save_wav("moog_bass", struct.pack(f'{len(result)}h', *result))

    def generate_moog_lead(self) -> str:
        """Screaming Moog lead with high resonance."""
        duration = 0.5
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        base_freq = 440  # A4

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Vibrato
            vibrato = math.sin(2 * math.pi * 5.5 * t) * 0.015
            freq = base_freq * (1 + vibrato)
            # Two detuned saws
            saw1 = 2 * ((freq * t) % 1) - 1
            saw2 = 2 * ((freq * 1.007 * t) % 1) - 1
            samples.append((saw1 + saw2) / 2)

        # Filter envelope with high resonance
        env = [math.exp(-i / SAMPLE_RATE * 6) for i in range(n_samples)]
        filtered = self._moog_ladder_filter(samples, 800, 0.85, env)

        result = []
        for i, sample in enumerate(filtered):
            t = i / SAMPLE_RATE
            if t < 0.02:
                amp = t / 0.02
            elif t > duration - 0.1:
                amp = (duration - t) / 0.1
            else:
                amp = 1.0
            value = int(math.tanh(sample * 1.2) * amp * 32767 * 0.6)
            result.append(max(-32767, min(32767, value)))

        return self._save_wav("moog_lead", struct.pack(f'{len(result)}h', *result))

    def generate_all_sounds(self) -> Dict[str, str]:
        """Generate all Moog sounds."""
        print("Generating Moog synthesizer sounds...")
        self.sounds = {
            'moog_bass': self.generate_moog_bass(),
            'moog_lead': self.generate_moog_lead(),
        }
        print(f"Generated {len(self.sounds)} Moog sounds")
        return self.sounds


class Juno60Synthesizer:
    """Roland Juno-60 style synthesizer.

    Famous for its iconic chorus effect, fat DCO oscillators,
    and lush pads. Perfect for ambient and synthpop.
    """

    def __init__(self, sounds_dir: str = None):
        self.sounds_dir = Path(sounds_dir) if sounds_dir else Path(__file__).parent.parent / "sounds"
        self.sounds_dir.mkdir(exist_ok=True)
        self.sounds: Dict[str, str] = {}

    def _save_wav(self, name: str, samples: bytes) -> str:
        filepath = self.sounds_dir / f"{name}.wav"
        with wave.open(str(filepath), 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(SAMPLE_WIDTH)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(samples)
        return str(filepath)

    def _juno_chorus(self, samples: List[float], mode: int = 1) -> List[float]:
        """Iconic Juno chorus effect with BBD modeling.

        Modes: 1 = subtle, 2 = lush, 3 = both (ensemble)
        """
        # BBD delay line parameters
        if mode == 1:
            delay_time = 0.003
            mod_depth = 0.0004
            rate = 0.5
        elif mode == 2:
            delay_time = 0.005
            mod_depth = 0.001
            rate = 0.35
        else:  # Both - chorus I + II
            delay_time = 0.004
            mod_depth = 0.0012
            rate = 0.4

        delay_samples = int(delay_time * SAMPLE_RATE)
        mod_samples = int(mod_depth * SAMPLE_RATE)

        result = []
        for i, sample in enumerate(samples):
            # LFO modulates delay time
            mod = math.sin(2 * math.pi * rate * i / SAMPLE_RATE)
            mod2 = math.sin(2 * math.pi * rate * 1.12 * i / SAMPLE_RATE)  # Second voice

            # Calculate modulated delay indices
            delay1 = delay_samples + int(mod * mod_samples)
            delay2 = delay_samples + int(mod2 * mod_samples * 0.7)

            idx1 = i - delay1
            idx2 = i - delay2

            # Sum original + delayed signals
            delayed1 = samples[idx1] if idx1 >= 0 else 0
            delayed2 = samples[idx2] if idx2 >= 0 else 0

            if mode == 3:
                result.append((sample * 0.5 + delayed1 * 0.35 + delayed2 * 0.35) / 1.2)
            else:
                result.append((sample * 0.6 + delayed1 * 0.5) / 1.1)

        return result

    def generate_juno_pad(self) -> str:
        """Lush Juno-60 pad with iconic chorus."""
        duration = 2.5
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        # Rich chord: Cmaj7 (C3, E3, G3, B3)
        freqs = [130.8, 164.8, 196.0, 246.9]

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            value = 0
            for j, freq in enumerate(freqs):
                # Juno DCO - slightly detuned pulse waves
                pwm = 0.45 + 0.1 * math.sin(2 * math.pi * 0.2 * t + j)  # Slow PWM
                phase = (freq * t) % 1
                pulse = 1 if phase < pwm else -1
                # Add saw component
                saw = 2 * phase - 1
                value += (pulse * 0.6 + saw * 0.4)
            value /= len(freqs)
            samples.append(value)

        # Apply Juno chorus (mode 3 = both I and II)
        samples = self._juno_chorus(samples, mode=3)

        # Slow pad envelope
        result = []
        attack = 0.4
        release_start = duration - 0.6
        for i, sample in enumerate(samples):
            t = i / SAMPLE_RATE
            if t < attack:
                env = t / attack
            elif t > release_start:
                env = (duration - t) / 0.6
            else:
                env = 1.0
            result.append(int(sample * env * 32767 * 0.45))

        return self._save_wav("juno_pad", struct.pack(f'{len(result)}h', *result))

    def generate_juno_bass(self) -> str:
        """Punchy Juno bass with that 80s vibe."""
        duration = 0.4
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        base_freq = 55  # A1

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Sawtooth with sub
            saw = 2 * ((base_freq * t) % 1) - 1
            sub = math.sin(2 * math.pi * base_freq * 0.5 * t)
            samples.append(saw * 0.7 + sub * 0.3)

        # Light chorus
        samples = self._juno_chorus(samples, mode=1)

        # Punchy envelope
        result = []
        for i, sample in enumerate(samples):
            t = i / SAMPLE_RATE
            env = math.exp(-t * 8)
            result.append(int(sample * env * 32767 * 0.7))

        return self._save_wav("juno_bass", struct.pack(f'{len(result)}h', *result))

    def generate_juno_arp(self) -> str:
        """Shimmering Juno arpeggio."""
        note_duration = 0.1
        notes = [261.6, 329.6, 392.0, 523.2, 392.0, 329.6]  # C E G C' G E
        total_duration = note_duration * len(notes)
        n_samples = int(SAMPLE_RATE * total_duration)
        samples = [0.0] * n_samples

        for note_idx, freq in enumerate(notes):
            start = int(note_idx * note_duration * SAMPLE_RATE)
            end = min(start + int(note_duration * 1.3 * SAMPLE_RATE), n_samples)

            for i in range(start, end):
                t = (i - start) / SAMPLE_RATE
                # Bright pulse
                pwm = 0.3 + 0.15 * math.sin(2 * math.pi * 4 * t)
                phase = (freq * t) % 1
                pulse = 1 if phase < pwm else -1
                env = math.exp(-t * 12)
                samples[i] += pulse * env * 0.5

        # Heavy chorus for shimmer
        samples = self._juno_chorus(samples, mode=3)

        result = [int(s * 32767 * 0.5) for s in samples]
        return self._save_wav("juno_arp", struct.pack(f'{len(result)}h', *result))

    def generate_all_sounds(self) -> Dict[str, str]:
        """Generate all Juno-60 sounds."""
        print("Generating Juno-60 synthesizer sounds...")
        self.sounds = {
            'juno_pad': self.generate_juno_pad(),
            'juno_bass': self.generate_juno_bass(),
            'juno_arp': self.generate_juno_arp(),
        }
        print(f"Generated {len(self.sounds)} Juno-60 sounds")
        return self.sounds


class Jupiter8Synthesizer:
    """Roland Jupiter-8 synthesizer sounds.

    The legendary polysynth with cross-modulation, sync,
    and that unmistakable warm analog character.
    """

    def __init__(self, sounds_dir: str = None):
        self.sounds_dir = Path(sounds_dir) if sounds_dir else Path(__file__).parent.parent / "sounds"
        self.sounds_dir.mkdir(exist_ok=True)
        self.sounds: Dict[str, str] = {}

    def _save_wav(self, name: str, samples: bytes) -> str:
        filepath = self.sounds_dir / f"{name}.wav"
        with wave.open(str(filepath), 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(SAMPLE_WIDTH)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(samples)
        return str(filepath)

    def _jupiter_unison(self, samples: List[float], voices: int = 4,
                        detune: float = 0.015) -> List[float]:
        """Jupiter-8 unison mode with voice stacking."""
        n_samples = len(samples)
        result = [0.0] * n_samples

        for voice in range(voices):
            # Each voice slightly detuned
            detune_factor = 1 + (voice - voices/2) * detune / voices
            for i in range(n_samples):
                src_idx = int(i * detune_factor)
                if src_idx < n_samples:
                    result[i] += samples[src_idx]

        # Normalize
        return [s / voices for s in result]

    def generate_jupiter_brass(self) -> str:
        """Majestic Jupiter brass stab."""
        duration = 0.6
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        # Brass chord: Cmaj (C4, E4, G4)
        freqs = [261.6, 329.6, 392.0]

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            value = 0
            for freq in freqs:
                # Dual oscillators per voice
                saw1 = 2 * ((freq * t) % 1) - 1
                saw2 = 2 * ((freq * 1.004 * t) % 1) - 1
                value += (saw1 + saw2) / 2
            value /= len(freqs)
            samples.append(value)

        # Unison thickening
        samples = self._jupiter_unison(samples, voices=2, detune=0.008)

        # Brass envelope - quick attack, slight decay, sustain
        result = []
        for i, sample in enumerate(samples):
            t = i / SAMPLE_RATE
            if t < 0.08:
                env = t / 0.08
            elif t < 0.15:
                env = 1.0 - (t - 0.08) * 2
            elif t > duration - 0.15:
                env = 0.8 * (duration - t) / 0.15
            else:
                env = 0.8
            result.append(int(sample * env * 32767 * 0.55))

        return self._save_wav("jupiter_brass", struct.pack(f'{len(result)}h', *result))

    def generate_jupiter_strings(self) -> str:
        """Lush Jupiter string ensemble."""
        duration = 2.0
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        # String chord: Dm7 (D3, F3, A3, C4)
        freqs = [146.8, 174.6, 220.0, 261.6]

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            value = 0
            for j, freq in enumerate(freqs):
                # Vibrato
                vib = math.sin(2 * math.pi * 5 * t + j) * 0.008
                f = freq * (1 + vib)
                # Dual detuned saws
                saw1 = 2 * ((f * t) % 1) - 1
                saw2 = 2 * ((f * 1.002 * t) % 1) - 1
                value += (saw1 + saw2) / 2
            value /= len(freqs)
            samples.append(value)

        # Unison spread
        samples = self._jupiter_unison(samples, voices=3, detune=0.012)

        # String envelope
        result = []
        attack = 0.3
        release_start = duration - 0.4
        for i, sample in enumerate(samples):
            t = i / SAMPLE_RATE
            if t < attack:
                env = t / attack
            elif t > release_start:
                env = (duration - t) / 0.4
            else:
                env = 1.0
            result.append(int(sample * env * 32767 * 0.4))

        return self._save_wav("jupiter_strings", struct.pack(f'{len(result)}h', *result))

    def generate_jupiter_sync_lead(self) -> str:
        """Hard sync lead - that tearing sound!"""
        duration = 0.5
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        master_freq = 220  # A3
        slave_ratio = 2.5  # Creates the sync character

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Slave ratio sweep for movement
            ratio = slave_ratio + math.exp(-t * 3) * 2

            # Hard sync: slave resets when master completes cycle
            master_phase = (master_freq * t) % 1
            slave_phase = (master_freq * ratio * t) % 1

            # Reset slave at master zero crossing
            if i > 0:
                prev_master = (master_freq * (i-1) / SAMPLE_RATE) % 1
                if master_phase < prev_master:  # Zero crossing
                    slave_phase = 0

            # Slave is a saw
            value = 2 * slave_phase - 1
            samples.append(value)

        # Lead envelope
        result = []
        for i, sample in enumerate(samples):
            t = i / SAMPLE_RATE
            if t < 0.02:
                env = t / 0.02
            elif t > duration - 0.1:
                env = (duration - t) / 0.1
            else:
                env = 1.0
            result.append(int(sample * env * 32767 * 0.5))

        return self._save_wav("jupiter_sync", struct.pack(f'{len(result)}h', *result))

    def generate_all_sounds(self) -> Dict[str, str]:
        """Generate all Jupiter-8 sounds."""
        print("Generating Jupiter-8 synthesizer sounds...")
        self.sounds = {
            'jupiter_brass': self.generate_jupiter_brass(),
            'jupiter_strings': self.generate_jupiter_strings(),
            'jupiter_sync': self.generate_jupiter_sync_lead(),
        }
        print(f"Generated {len(self.sounds)} Jupiter-8 sounds")
        return self.sounds


class ElectroPop909Synthesizer:
    """Modern electro-pop and EDM drum sounds.

    Punchy TR-909 inspired sounds with modern processing
    for that contemporary electronic feel.
    """

    def __init__(self, sounds_dir: str = None):
        self.sounds_dir = Path(sounds_dir) if sounds_dir else Path(__file__).parent.parent / "sounds"
        self.sounds_dir.mkdir(exist_ok=True)
        self.sounds: Dict[str, str] = {}

    def _save_wav(self, name: str, samples: bytes) -> str:
        filepath = self.sounds_dir / f"{name}.wav"
        with wave.open(str(filepath), 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(SAMPLE_WIDTH)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(samples)
        return str(filepath)

    def generate_909_kick(self) -> str:
        """Punchy 909-style kick with click and body."""
        duration = 0.5
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Pitch sweep from high to low
            freq = 180 * math.exp(-t * 15) + 50
            # Click at start
            click = math.sin(2 * math.pi * 2500 * t) * math.exp(-t * 200) if t < 0.01 else 0
            # Body
            body = math.sin(2 * math.pi * freq * t) * math.exp(-t * 8)
            value = body * 0.9 + click * 0.3
            samples.append(int(value * 32767 * 0.85))

        return self._save_wav("909_kick", struct.pack(f'{len(samples)}h', *samples))

    def generate_909_snare(self) -> str:
        """Crispy 909 snare with snap and body."""
        duration = 0.35
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Tone component (two tones)
            tone1 = math.sin(2 * math.pi * 189 * t) * math.exp(-t * 25)
            tone2 = math.sin(2 * math.pi * 282 * t) * math.exp(-t * 30)
            # Noise
            noise = (random.random() * 2 - 1) * math.exp(-t * 12)
            value = (tone1 + tone2) * 0.4 + noise * 0.6
            samples.append(int(value * 32767 * 0.75))

        return self._save_wav("909_snare", struct.pack(f'{len(samples)}h', *samples))

    def generate_909_hihat(self) -> str:
        """Sizzling 909 hi-hat."""
        duration = 0.08
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        # 909 uses 6 square wave oscillators
        freqs = [800, 1053, 1405, 1878, 2500, 3333]

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            value = 0
            for freq in freqs:
                # Square waves at metallic frequencies
                value += (1 if ((freq * t) % 1) < 0.5 else -1)
            value /= len(freqs)
            # Noise component
            noise = (random.random() * 2 - 1) * 0.5
            value = (value * 0.6 + noise * 0.4) * math.exp(-t * 60)
            samples.append(int(value * 32767 * 0.5))

        return self._save_wav("909_hihat", struct.pack(f'{len(samples)}h', *samples))

    def generate_909_clap(self) -> str:
        """Layered 909 hand clap."""
        duration = 0.35
        n_samples = int(SAMPLE_RATE * duration)
        samples = [0] * n_samples

        # Multiple noise bursts
        bursts = [0, 0.012, 0.024, 0.036]
        for burst_time in bursts:
            start = int(burst_time * SAMPLE_RATE)
            for i in range(start, min(start + int(0.03 * SAMPLE_RATE), n_samples)):
                t = (i - start) / SAMPLE_RATE
                # Band-passed noise
                noise = (random.random() * 2 - 1)
                env = math.exp(-t * 35)
                samples[i] += int(noise * env * 32767 * 0.3)

        # Normalize
        max_val = max(abs(s) for s in samples) or 1
        if max_val > 32767:
            samples = [int(s * 32767 / max_val) for s in samples]

        return self._save_wav("909_clap", struct.pack(f'{len(samples)}h', *samples))

    def generate_edm_riser(self) -> str:
        """Classic EDM riser/sweep."""
        duration = 2.0
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            progress = t / duration
            # Exponential frequency rise
            freq = 100 * (2 ** (progress * 4))
            # White noise + filtered sweep
            noise = (random.random() * 2 - 1)
            osc = math.sin(2 * math.pi * freq * t)
            # Mix changes over time
            mix = progress * 0.7
            value = osc * (1 - mix) + noise * mix
            # Rising amplitude
            amp = progress ** 1.5
            samples.append(int(value * amp * 32767 * 0.5))

        return self._save_wav("edm_riser", struct.pack(f'{len(samples)}h', *samples))

    def generate_edm_drop_impact(self) -> str:
        """Big EDM drop impact sound."""
        duration = 1.0
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Low impact
            freq = 60 * math.exp(-t * 3) + 30
            impact = math.sin(2 * math.pi * freq * t)
            # White burst
            burst = (random.random() * 2 - 1) * math.exp(-t * 20) if t < 0.1 else 0
            # Combine
            value = impact * math.exp(-t * 4) * 0.8 + burst * 0.3
            samples.append(int(value * 32767 * 0.9))

        return self._save_wav("edm_impact", struct.pack(f'{len(samples)}h', *samples))

    def generate_all_sounds(self) -> Dict[str, str]:
        """Generate all electro-pop/EDM sounds."""
        print("Generating Electro-Pop/EDM sounds...")
        self.sounds = {
            '909_kick': self.generate_909_kick(),
            '909_snare': self.generate_909_snare(),
            '909_hihat': self.generate_909_hihat(),
            '909_clap': self.generate_909_clap(),
            'edm_riser': self.generate_edm_riser(),
            'edm_impact': self.generate_edm_drop_impact(),
        }
        print(f"Generated {len(self.sounds)} Electro-Pop/EDM sounds")
        return self.sounds


def generate_sine_wave(freq: float, duration: float, amplitude: float = 0.5) -> bytes:
    """Generate a sine wave."""
    n_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(n_samples):
        t = i / SAMPLE_RATE
        value = amplitude * math.sin(2 * math.pi * freq * t)
        samples.append(int(value * 32767))
    return struct.pack(f'{len(samples)}h', *samples)


def apply_envelope(samples: bytes, attack: float, decay: float, sustain: float, release: float) -> bytes:
    """Apply ADSR envelope to samples."""
    unpacked = struct.unpack(f'{len(samples)//2}h', samples)
    n_samples = len(unpacked)
    attack_samples = int(attack * SAMPLE_RATE)
    decay_samples = int(decay * SAMPLE_RATE)
    release_samples = int(release * SAMPLE_RATE)

    result = []
    for i, sample in enumerate(unpacked):
        if i < attack_samples:
            env = i / attack_samples
        elif i < attack_samples + decay_samples:
            env = 1.0 - ((1.0 - sustain) * (i - attack_samples) / decay_samples)
        elif i < n_samples - release_samples:
            env = sustain
        else:
            remaining = n_samples - i
            env = sustain * (remaining / release_samples)
        result.append(int(sample * env))
    return struct.pack(f'{len(result)}h', *result)


def mix_samples(*sample_lists: bytes) -> bytes:
    """Mix multiple sample lists together."""
    max_len = max(len(s) for s in sample_lists) // 2
    result = [0] * max_len

    for samples in sample_lists:
        unpacked = struct.unpack(f'{len(samples)//2}h', samples)
        for i, value in enumerate(unpacked):
            result[i] += value

    # Normalize to prevent clipping
    max_val = max(abs(v) for v in result) or 1
    if max_val > 32767:
        result = [int(v * 32767 / max_val) for v in result]

    return struct.pack(f'{len(result)}h', *result)


class RolandDrumSynthesizer:
    """Synthesizes Roland TR-808/909 style drum sounds."""

    def __init__(self, sounds_dir: str = None):
        self.sounds_dir = Path(sounds_dir or Path(__file__).parent.parent / "sounds")
        self.sounds_dir.mkdir(exist_ok=True)
        self.sounds: Dict[str, str] = {}

    def _save_wav(self, name: str, samples: bytes) -> str:
        """Save samples as WAV file."""
        filepath = self.sounds_dir / f"{name}.wav"
        with wave.open(str(filepath), 'w') as wav:
            wav.setnchannels(CHANNELS)
            wav.setsampwidth(SAMPLE_WIDTH)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(samples)
        return str(filepath)

    def generate_808_kick(self) -> str:
        """TR-808 style bass drum - deep, punchy, with pitch sweep."""
        duration = 0.4
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Pitch sweep from 150Hz to 50Hz
            freq = 150 * math.exp(-t * 8) + 50
            # Amplitude decay
            amp = math.exp(-t * 10) * 0.9
            value = amp * math.sin(2 * math.pi * freq * t)
            samples.append(int(value * 32767))

        return self._save_wav("808_kick", struct.pack(f'{len(samples)}h', *samples))

    def generate_808_snare(self) -> str:
        """TR-808 style snare - tone + noise."""
        duration = 0.3
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        import random
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Tone component (200Hz)
            tone = math.sin(2 * math.pi * 200 * t) * 0.4 * math.exp(-t * 20)
            # Noise component
            noise = (random.random() * 2 - 1) * 0.6 * math.exp(-t * 15)
            value = tone + noise
            samples.append(int(value * 32767))

        return self._save_wav("808_snare", struct.pack(f'{len(samples)}h', *samples))

    def generate_808_hihat_closed(self) -> str:
        """TR-808 closed hi-hat - metallic click."""
        duration = 0.1
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        import random
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # High-frequency noise with metallic overtones
            noise = (random.random() * 2 - 1)
            # Band-pass effect with multiple frequencies
            metal = sum(math.sin(2 * math.pi * f * t) for f in [4000, 6000, 8000, 10000]) / 4
            value = (noise * 0.3 + metal * 0.7) * math.exp(-t * 50)
            samples.append(int(value * 32767))

        return self._save_wav("808_hihat_closed", struct.pack(f'{len(samples)}h', *samples))

    def generate_808_hihat_open(self) -> str:
        """TR-808 open hi-hat - longer decay."""
        duration = 0.4
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        import random
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            noise = (random.random() * 2 - 1)
            metal = sum(math.sin(2 * math.pi * f * t) for f in [4000, 6000, 8000, 10000]) / 4
            value = (noise * 0.3 + metal * 0.7) * math.exp(-t * 8)
            samples.append(int(value * 32767))

        return self._save_wav("808_hihat_open", struct.pack(f'{len(samples)}h', *samples))

    def generate_808_clap(self) -> str:
        """TR-808 hand clap - layered noise bursts."""
        duration = 0.3
        n_samples = int(SAMPLE_RATE * duration)
        samples = [0] * n_samples

        import random
        # Multiple noise bursts
        for burst in [0, 0.015, 0.03, 0.045]:
            start = int(burst * SAMPLE_RATE)
            for i in range(start, min(start + int(0.08 * SAMPLE_RATE), n_samples)):
                t = (i - start) / SAMPLE_RATE
                noise = (random.random() * 2 - 1) * math.exp(-t * 25)
                samples[i] += int(noise * 32767 * 0.4)

        # Normalize
        max_val = max(abs(s) for s in samples) or 1
        samples = [int(s * 32767 / max_val) for s in samples]

        return self._save_wav("808_clap", struct.pack(f'{len(samples)}h', *samples))

    def generate_808_cowbell(self) -> str:
        """TR-808 cowbell - metallic ring."""
        duration = 0.2
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Two detuned tones for metallic sound
            value = (math.sin(2 * math.pi * 540 * t) + math.sin(2 * math.pi * 845 * t)) / 2
            value *= math.exp(-t * 12)
            samples.append(int(value * 32767 * 0.7))

        return self._save_wav("808_cowbell", struct.pack(f'{len(samples)}h', *samples))

    def generate_808_tom_low(self) -> str:
        """TR-808 low tom - deep resonant."""
        duration = 0.35
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            freq = 120 * math.exp(-t * 4) + 80
            value = math.sin(2 * math.pi * freq * t) * math.exp(-t * 8)
            samples.append(int(value * 32767 * 0.8))

        return self._save_wav("808_tom_low", struct.pack(f'{len(samples)}h', *samples))

    def generate_808_tom_high(self) -> str:
        """TR-808 high tom - brighter."""
        duration = 0.25
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            freq = 200 * math.exp(-t * 5) + 150
            value = math.sin(2 * math.pi * freq * t) * math.exp(-t * 12)
            samples.append(int(value * 32767 * 0.7))

        return self._save_wav("808_tom_high", struct.pack(f'{len(samples)}h', *samples))

    def generate_808_rimshot(self) -> str:
        """TR-808 rimshot - sharp click."""
        duration = 0.1
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        import random
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Short sharp attack
            click = math.sin(2 * math.pi * 1500 * t) * math.exp(-t * 80)
            noise = (random.random() * 2 - 1) * 0.3 * math.exp(-t * 60)
            value = click * 0.7 + noise
            samples.append(int(value * 32767 * 0.9))

        return self._save_wav("808_rimshot", struct.pack(f'{len(samples)}h', *samples))

    def generate_808_cymbal(self) -> str:
        """TR-808 crash cymbal - long metallic decay."""
        duration = 1.0
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        import random
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            noise = (random.random() * 2 - 1)
            # Multiple metallic frequencies
            metal = sum(math.sin(2 * math.pi * f * t) for f in [2000, 3500, 5000, 7500, 10000]) / 5
            value = (noise * 0.4 + metal * 0.6) * math.exp(-t * 3)
            samples.append(int(value * 32767 * 0.6))

        return self._save_wav("808_cymbal", struct.pack(f'{len(samples)}h', *samples))

    def generate_808_maracas(self) -> str:
        """TR-808 maracas/tick - soft rhythmic noise."""
        duration = 0.05
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        import random
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            noise = (random.random() * 2 - 1) * math.exp(-t * 100)
            samples.append(int(noise * 32767 * 0.3))

        return self._save_wav("808_maracas", struct.pack(f'{len(samples)}h', *samples))

    def generate_heartbeat(self) -> str:
        """Soft metronome pulse."""
        duration = 0.15
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            freq = 60
            value = math.sin(2 * math.pi * freq * t) * math.exp(-t * 15)
            samples.append(int(value * 32767 * 0.2))

        return self._save_wav("heartbeat", struct.pack(f'{len(samples)}h', *samples))

    def generate_all_sounds(self) -> Dict[str, str]:
        """Generate all drum sounds."""
        print("Generating Roland TR-808 style drum sounds...")

        self.sounds = {
            'kick': self.generate_808_kick(),
            'snare': self.generate_808_snare(),
            'hihat_closed': self.generate_808_hihat_closed(),
            'hihat_open': self.generate_808_hihat_open(),
            'clap': self.generate_808_clap(),
            'cowbell': self.generate_808_cowbell(),
            'tom_low': self.generate_808_tom_low(),
            'tom_high': self.generate_808_tom_high(),
            'rimshot': self.generate_808_rimshot(),
            'cymbal': self.generate_808_cymbal(),
            'maracas': self.generate_808_maracas(),
            'heartbeat': self.generate_heartbeat(),
        }

        print(f"Generated {len(self.sounds)} drum sounds in {self.sounds_dir}")
        return self.sounds


class RolandBassSynthesizer:
    """Synthesizes Roland TB-303 style acid bass sounds."""

    def __init__(self, sounds_dir: str = None):
        self.sounds_dir = Path(sounds_dir or Path(__file__).parent.parent / "sounds")
        self.sounds_dir.mkdir(exist_ok=True)
        self.sounds: Dict[str, str] = {}

    def _save_wav(self, name: str, samples: bytes) -> str:
        """Save samples as WAV file."""
        filepath = self.sounds_dir / f"{name}.wav"
        with wave.open(str(filepath), 'w') as wav:
            wav.setnchannels(CHANNELS)
            wav.setsampwidth(SAMPLE_WIDTH)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(samples)
        return str(filepath)

    def _resonant_filter(self, samples: list, cutoff: float, resonance: float, mod_env: list = None) -> list:
        """Apply resonant low-pass filter (TB-303 style)."""
        result = []
        y1, y2 = 0.0, 0.0

        for i, sample in enumerate(samples):
            # Modulate cutoff with envelope if provided
            if mod_env and i < len(mod_env):
                freq = cutoff * (1 + mod_env[i] * 3)  # Envelope modulates cutoff
            else:
                freq = cutoff

            # Simple 2-pole filter approximation
            freq = min(freq, SAMPLE_RATE / 2 - 100)
            w = 2 * math.pi * freq / SAMPLE_RATE
            k = math.tan(w / 2)
            q = resonance

            a0 = 1 + k / q + k * k
            b0 = k * k / a0
            b1 = 2 * k * k / a0
            b2 = k * k / a0
            a1 = 2 * (k * k - 1) / a0
            a2 = (1 - k / q + k * k) / a0

            y = b0 * sample + b1 * y1 + b2 * y2 - a1 * y1 - a2 * y2
            y2 = y1
            y1 = y

            # Add resonance feedback
            y = y + y * resonance * 0.3

            result.append(y)

        return result

    def generate_303_acid(self) -> str:
        """TB-303 acid bass - signature squelchy resonant sweep."""
        duration = 0.5
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        base_freq = 55  # A1

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Sawtooth oscillator (TB-303 signature)
            phase = (base_freq * t) % 1
            saw = 2 * phase - 1
            # Add slight detuned square for thickness
            square = 1 if ((base_freq * 1.005 * t) % 1) < 0.5 else -1
            value = saw * 0.7 + square * 0.3
            samples.append(value)

        # Create envelope for filter modulation
        env = []
        attack = 0.01
        decay = 0.2
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            if t < attack:
                env.append(t / attack)
            else:
                env.append(math.exp(-(t - attack) / decay))

        # Apply resonant filter with envelope modulation
        filtered = self._resonant_filter(samples, 200, 8.0, env)

        # Apply amplitude envelope with soft clipping
        result = []
        for i, sample in enumerate(filtered):
            t = i / SAMPLE_RATE
            amp = math.exp(-t * 4)
            # Soft clip to prevent overflow
            clipped = math.tanh(sample * 0.5)
            value = int(clipped * amp * 32767 * 0.6)
            # Hard clamp as safety
            value = max(-32767, min(32767, value))
            result.append(value)

        return self._save_wav("303_acid", struct.pack(f'{len(result)}h', *result))

    def generate_303_sub(self) -> str:
        """TB-303 sub bass - deep fundamental with slight warmth."""
        duration = 0.6
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        base_freq = 41.2  # E1 - deep sub

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Mostly sine with subtle harmonics
            sine = math.sin(2 * math.pi * base_freq * t)
            sine2 = math.sin(2 * math.pi * base_freq * 2 * t) * 0.3
            sine3 = math.sin(2 * math.pi * base_freq * 3 * t) * 0.1
            value = (sine + sine2 + sine3) / 1.4

            # Amplitude envelope
            amp = math.exp(-t * 3)
            samples.append(int(value * amp * 32767 * 0.8))

        return self._save_wav("303_sub", struct.pack(f'{len(samples)}h', *samples))

    def generate_303_squelch(self) -> str:
        """TB-303 squelch bass - extreme filter modulation."""
        duration = 0.4
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        base_freq = 65.4  # C2

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Square wave for more harmonics
            phase = (base_freq * t) % 1
            square = 1 if phase < 0.5 else -1
            samples.append(square)

        # Extreme envelope modulation
        env = []
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Sharp attack, quick sweep
            env.append(math.exp(-t * 15))

        # Heavy resonance
        filtered = self._resonant_filter(samples, 150, 12.0, env)

        result = []
        for i, sample in enumerate(filtered):
            t = i / SAMPLE_RATE
            amp = math.exp(-t * 6)
            # Soft clipping for that dirty 303 sound
            clipped = math.tanh(sample * 0.5)
            value = int(clipped * amp * 32767 * 0.5)
            value = max(-32767, min(32767, value))
            result.append(value)

        return self._save_wav("303_squelch", struct.pack(f'{len(result)}h', *result))

    def generate_303_pluck(self) -> str:
        """TB-303 pluck bass - sharp attack, quick decay."""
        duration = 0.25
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        base_freq = 73.4  # D2

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Sawtooth with pitch drop
            freq = base_freq * (1 + math.exp(-t * 30) * 0.5)
            phase = (freq * t) % 1
            saw = 2 * phase - 1
            samples.append(saw)

        # Quick filter sweep
        env = [math.exp(-i / SAMPLE_RATE * 20) for i in range(n_samples)]
        filtered = self._resonant_filter(samples, 400, 6.0, env)

        result = []
        for i, sample in enumerate(filtered):
            t = i / SAMPLE_RATE
            amp = math.exp(-t * 12)
            # Soft clip to prevent overflow
            clipped = math.tanh(sample * 0.5)
            value = int(clipped * amp * 32767 * 0.7)
            value = max(-32767, min(32767, value))
            result.append(value)

        return self._save_wav("303_pluck", struct.pack(f'{len(result)}h', *result))

    def generate_303_growl(self) -> str:
        """TB-303 growl bass - distorted and aggressive."""
        duration = 0.4
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        base_freq = 49.0  # G1

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Detuned oscillators
            saw1 = 2 * ((base_freq * t) % 1) - 1
            saw2 = 2 * ((base_freq * 1.01 * t) % 1) - 1
            saw3 = 2 * ((base_freq * 0.99 * t) % 1) - 1
            value = (saw1 + saw2 + saw3) / 3
            samples.append(value)

        # Filter with modulation
        env = [math.exp(-i / SAMPLE_RATE * 8) for i in range(n_samples)]
        filtered = self._resonant_filter(samples, 250, 10.0, env)

        result = []
        for i, sample in enumerate(filtered):
            t = i / SAMPLE_RATE
            amp = math.exp(-t * 5)
            # Heavy distortion with soft clipping
            clipped = math.tanh(sample * 0.5)
            value = int(clipped * amp * 32767 * 0.5)
            value = max(-32767, min(32767, value))
            result.append(value)

        return self._save_wav("303_growl", struct.pack(f'{len(result)}h', *result))

    def generate_all_sounds(self) -> Dict[str, str]:
        """Generate all bass sounds."""
        print("Generating Roland TB-303 style bass sounds...")

        self.sounds = {
            'bass_acid': self.generate_303_acid(),
            'bass_sub': self.generate_303_sub(),
            'bass_squelch': self.generate_303_squelch(),
            'bass_pluck': self.generate_303_pluck(),
            'bass_growl': self.generate_303_growl(),
        }

        print(f"Generated {len(self.sounds)} bass sounds in {self.sounds_dir}")
        return self.sounds


class SystemSoundSynthesizer:
    """Synthesizes system/utility sounds for agentic operations."""

    def __init__(self, sounds_dir: str = None):
        self.sounds_dir = Path(sounds_dir or Path(__file__).parent.parent / "sounds")
        self.sounds_dir.mkdir(exist_ok=True)
        self.sounds: Dict[str, str] = {}

    def _save_wav(self, name: str, samples: bytes) -> str:
        """Save samples as WAV file."""
        filepath = self.sounds_dir / f"{name}.wav"
        with wave.open(str(filepath), 'w') as wav:
            wav.setnchannels(CHANNELS)
            wav.setsampwidth(SAMPLE_WIDTH)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(samples)
        return str(filepath)

    def generate_context_compact(self) -> str:
        """Context compaction - descending sweep with compression feel."""
        duration = 0.5
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Descending frequency sweep (compression metaphor)
            freq = 800 * math.exp(-t * 4) + 100
            # Multiple harmonics for richness
            value = math.sin(2 * math.pi * freq * t) * 0.6
            value += math.sin(2 * math.pi * freq * 1.5 * t) * 0.3
            value += math.sin(2 * math.pi * freq * 0.5 * t) * 0.4
            # Amplitude envelope with quick attack
            amp = math.exp(-t * 5) * (1 - math.exp(-t * 50))
            samples.append(int(value * amp * 32767 * 0.5))

        return self._save_wav("context_compact", struct.pack(f'{len(samples)}h', *samples))

    def generate_file_read(self) -> str:
        """File read - quick ascending blip."""
        duration = 0.08
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Quick ascending tone
            freq = 600 + t * 2000
            value = math.sin(2 * math.pi * freq * t)
            amp = math.exp(-t * 30)
            samples.append(int(value * amp * 32767 * 0.4))

        return self._save_wav("file_read", struct.pack(f'{len(samples)}h', *samples))

    def generate_file_write(self) -> str:
        """File write - quick descending blip."""
        duration = 0.1
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Quick descending tone
            freq = 1000 - t * 3000
            freq = max(freq, 200)
            value = math.sin(2 * math.pi * freq * t)
            amp = math.exp(-t * 25)
            samples.append(int(value * amp * 32767 * 0.45))

        return self._save_wav("file_write", struct.pack(f'{len(samples)}h', *samples))

    def generate_tool_call(self) -> str:
        """Tool call - mechanical click sequence."""
        duration = 0.15
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        import random
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Two-tone click
            click1 = math.sin(2 * math.pi * 1200 * t) * math.exp(-t * 60)
            click2 = math.sin(2 * math.pi * 800 * t) * math.exp(-(t - 0.03) * 40) if t > 0.03 else 0
            noise = (random.random() * 2 - 1) * 0.15 * math.exp(-t * 80)
            value = click1 * 0.5 + click2 * 0.4 + noise
            samples.append(int(value * 32767 * 0.6))

        return self._save_wav("tool_call", struct.pack(f'{len(samples)}h', *samples))

    def generate_memory_consolidate(self) -> str:
        """Memory consolidation - dreamy, sleep-like pad sweep."""
        duration = 1.2
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        # Slow chord sweep (dream-like)
        freqs = [196.0, 246.9, 293.7]  # G3, B3, D4 (G major)

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            value = 0
            for j, freq in enumerate(freqs):
                # Detuned oscillators with slow LFO
                lfo = math.sin(2 * math.pi * 0.3 * t + j) * 0.02
                saw = 2 * ((freq * (1 + lfo) * t) % 1) - 1
                value += saw
            value /= len(freqs)
            # Soft envelope - slow fade in/out
            if t < 0.3:
                env = t / 0.3
            elif t > duration - 0.4:
                env = (duration - t) / 0.4
            else:
                env = 1.0
            samples.append(int(value * env * 32767 * 0.3))

        return self._save_wav("memory_consolidate", struct.pack(f'{len(samples)}h', *samples))

    def generate_code_execute(self) -> str:
        """Code execution - digital/mechanical processing sound."""
        duration = 0.25
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        import random
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Bitcrushed digital sound
            freq = 440
            square = 1 if ((freq * t) % 1) < 0.5 else -1
            # Add digital noise
            noise = (random.random() * 2 - 1) * 0.2
            value = square * 0.6 + noise
            # Stepped envelope for digital feel
            step = int(t * 20) / 20
            env = math.exp(-step * 8)
            samples.append(int(value * env * 32767 * 0.4))

        return self._save_wav("code_execute", struct.pack(f'{len(samples)}h', *samples))

    def generate_search(self) -> str:
        """Search/grep - scanning sweep sound."""
        duration = 0.3
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Scanning frequency sweep up and down
            phase = (t / duration) * 2 * math.pi
            freq = 500 + 300 * math.sin(phase * 2)
            value = math.sin(2 * math.pi * freq * t)
            # Add subtle harmonics
            value += math.sin(2 * math.pi * freq * 2 * t) * 0.2
            amp = (1 - math.exp(-t * 30)) * math.exp(-max(0, t - duration + 0.1) * 10)
            sample = int(value * amp * 32767 * 0.35)
            samples.append(max(-32767, min(32767, sample)))

        return self._save_wav("search", struct.pack(f'{len(samples)}h', *samples))

    def generate_web_fetch(self) -> str:
        """Web fetch - network transmission sound."""
        duration = 0.35
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        import random
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Modem-like chirp with data noise
            freq = 1200 + math.sin(2 * math.pi * 30 * t) * 400
            carrier = math.sin(2 * math.pi * freq * t)
            # Data burst noise
            data = (random.random() * 2 - 1) * 0.3 if (int(t * 100) % 3) == 0 else 0
            value = carrier * 0.5 + data
            amp = math.exp(-t * 4)
            samples.append(int(value * amp * 32767 * 0.4))

        return self._save_wav("web_fetch", struct.pack(f'{len(samples)}h', *samples))

    def generate_cache_hit(self) -> str:
        """Cache hit - quick positive ding."""
        duration = 0.12
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Bright positive tone
            freq = 1047  # C6
            value = math.sin(2 * math.pi * freq * t)
            value += math.sin(2 * math.pi * freq * 2 * t) * 0.3
            amp = math.exp(-t * 25)
            samples.append(int(value * amp * 32767 * 0.4))

        return self._save_wav("cache_hit", struct.pack(f'{len(samples)}h', *samples))

    def generate_cache_miss(self) -> str:
        """Cache miss - quick negative buzz."""
        duration = 0.1
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Lower, slightly dissonant
            freq1, freq2 = 220, 233  # Slight dissonance
            value = math.sin(2 * math.pi * freq1 * t) + math.sin(2 * math.pi * freq2 * t)
            amp = math.exp(-t * 30)
            samples.append(int(value * amp * 32767 * 0.25))

        return self._save_wav("cache_miss", struct.pack(f'{len(samples)}h', *samples))

    def generate_planning(self) -> str:
        """Planning mode - thoughtful ascending arpeggio."""
        duration = 0.6
        n_samples = int(SAMPLE_RATE * duration)
        samples = [0] * n_samples

        # Ascending notes: C4, E4, G4, C5
        notes = [261.6, 329.6, 392.0, 523.2]
        note_len = 0.12

        for idx, freq in enumerate(notes):
            start = int(idx * note_len * SAMPLE_RATE)
            end = min(start + int(note_len * 1.5 * SAMPLE_RATE), n_samples)
            for i in range(start, end):
                t = (i - start) / SAMPLE_RATE
                value = math.sin(2 * math.pi * freq * t)
                value += math.sin(2 * math.pi * freq * 2 * t) * 0.2
                amp = math.exp(-t * 12)
                samples[i] += int(value * amp * 32767 * 0.35)

        # Normalize
        max_val = max(abs(s) for s in samples) or 1
        if max_val > 32767:
            samples = [int(s * 32767 / max_val) for s in samples]

        return self._save_wav("planning", struct.pack(f'{len(samples)}h', *samples))

    def generate_streaming(self) -> str:
        """Streaming output - continuous flowing sound."""
        duration = 0.4
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Flowing frequency with gentle modulation
            freq = 350 + math.sin(2 * math.pi * 4 * t) * 50
            value = math.sin(2 * math.pi * freq * t)
            # Soft pulsing amplitude
            pulse = 0.7 + 0.3 * math.sin(2 * math.pi * 8 * t)
            attack = 1 - math.exp(-t * 20)
            release = math.exp(-max(0, t - duration + 0.15) * 10)
            amp = pulse * attack * release
            sample = int(value * amp * 32767 * 0.3)
            samples.append(max(-32767, min(32767, sample)))

        return self._save_wav("streaming", struct.pack(f'{len(samples)}h', *samples))

    def generate_token_limit(self) -> str:
        """Token limit warning - urgent descending tone."""
        duration = 0.3
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Urgent descending
            freq = 800 - t * 1000
            freq = max(freq, 200)
            value = math.sin(2 * math.pi * freq * t)
            # Pulsing urgency
            pulse = 1 if (int(t * 20) % 2) == 0 else 0.6
            amp = pulse * math.exp(-t * 5)
            samples.append(int(value * amp * 32767 * 0.5))

        return self._save_wav("token_limit", struct.pack(f'{len(samples)}h', *samples))

    def generate_agent_thinking(self) -> str:
        """Agent thinking - gentle pulsing meditation tone."""
        duration = 0.5
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Soft pulsing tone
            freq = 330  # E4
            # Subtle frequency wobble
            wobble = math.sin(2 * math.pi * 2 * t) * 5
            value = math.sin(2 * math.pi * (freq + wobble) * t)
            # Add soft harmonic
            value += math.sin(2 * math.pi * freq * 2 * t) * 0.15
            # Gentle pulsing envelope
            pulse = 0.6 + 0.4 * math.sin(2 * math.pi * 3 * t)
            attack = 1 - math.exp(-t * 15)
            release = math.exp(-max(0, t - duration + 0.15) * 10)
            amp = pulse * attack * release
            sample = int(value * amp * 32767 * 0.25)
            samples.append(max(-32767, min(32767, sample)))

        return self._save_wav("agent_thinking", struct.pack(f'{len(samples)}h', *samples))

    def generate_permission_request(self) -> str:
        """Permission request - attention-getting two-tone."""
        duration = 0.25
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Two-tone attention signal
            if t < 0.12:
                freq = 880  # A5
            else:
                freq = 1047  # C6
            value = math.sin(2 * math.pi * freq * t)
            value += math.sin(2 * math.pi * freq * 2 * t) * 0.25
            # Quick attack, sustained
            if t < 0.02:
                amp = t / 0.02
            else:
                amp = math.exp(-(t - 0.02) * 8)
            samples.append(int(value * amp * 32767 * 0.45))

        return self._save_wav("permission_request", struct.pack(f'{len(samples)}h', *samples))

    def generate_git_commit(self) -> str:
        """Git commit - satisfying 'lock-in' sound."""
        duration = 0.2
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        import random
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Click with resonant tail
            click = math.sin(2 * math.pi * 2000 * t) * math.exp(-t * 100)
            resonance = math.sin(2 * math.pi * 400 * t) * math.exp(-t * 15)
            noise = (random.random() * 2 - 1) * 0.1 * math.exp(-t * 50)
            value = click * 0.4 + resonance * 0.5 + noise
            samples.append(int(value * 32767 * 0.6))

        return self._save_wav("git_commit", struct.pack(f'{len(samples)}h', *samples))

    def generate_all_sounds(self) -> Dict[str, str]:
        """Generate all system sounds."""
        print("Generating system/utility sounds...")

        self.sounds = {
            'context_compact': self.generate_context_compact(),
            'file_read': self.generate_file_read(),
            'file_write': self.generate_file_write(),
            'tool_call': self.generate_tool_call(),
            'memory_consolidate': self.generate_memory_consolidate(),
            'code_execute': self.generate_code_execute(),
            'search': self.generate_search(),
            'web_fetch': self.generate_web_fetch(),
            'cache_hit': self.generate_cache_hit(),
            'cache_miss': self.generate_cache_miss(),
            'planning': self.generate_planning(),
            'streaming': self.generate_streaming(),
            'token_limit': self.generate_token_limit(),
            'agent_thinking': self.generate_agent_thinking(),
            'permission_request': self.generate_permission_request(),
            'git_commit': self.generate_git_commit(),
        }

        print(f"Generated {len(self.sounds)} system sounds in {self.sounds_dir}")
        return self.sounds


class RolandKeyboardSynthesizer:
    """Synthesizes Roland Juno/Jupiter style keyboard sounds."""

    def __init__(self, sounds_dir: str = None):
        self.sounds_dir = Path(sounds_dir or Path(__file__).parent.parent / "sounds")
        self.sounds_dir.mkdir(exist_ok=True)
        self.sounds: Dict[str, str] = {}

    def _save_wav(self, name: str, samples: bytes) -> str:
        """Save samples as WAV file."""
        filepath = self.sounds_dir / f"{name}.wav"
        with wave.open(str(filepath), 'w') as wav:
            wav.setnchannels(CHANNELS)
            wav.setsampwidth(SAMPLE_WIDTH)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(samples)
        return str(filepath)

    def _chorus_effect(self, samples: list, depth: float = 0.002, rate: float = 0.5) -> list:
        """Apply Roland-style chorus effect."""
        delay_samples = int(0.02 * SAMPLE_RATE)  # 20ms base delay
        result = []

        for i, sample in enumerate(samples):
            # Modulated delay
            mod = math.sin(2 * math.pi * rate * i / SAMPLE_RATE)
            delay_offset = int(delay_samples + depth * SAMPLE_RATE * mod)
            delay_idx = i - delay_offset

            if delay_idx >= 0:
                delayed = samples[delay_idx]
                result.append((sample + delayed * 0.6) / 1.6)
            else:
                result.append(sample)

        return result

    def generate_jupiter_pad(self) -> str:
        """Jupiter-8 style warm pad - evolving and lush."""
        duration = 2.0
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        # Chord: C major (C4, E4, G4)
        freqs = [261.6, 329.6, 392.0]

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            value = 0

            for j, freq in enumerate(freqs):
                # Detuned sawtooth oscillators (classic Jupiter)
                saw1 = 2 * ((freq * t) % 1) - 1
                saw2 = 2 * ((freq * 1.003 * t) % 1) - 1
                saw3 = 2 * ((freq * 0.997 * t) % 1) - 1
                value += (saw1 + saw2 + saw3) / 3

            value /= len(freqs)
            samples.append(value)

        # Apply chorus
        samples = self._chorus_effect(samples, 0.003, 0.3)

        # Slow attack, sustain, slow release
        result = []
        attack = 0.3
        release_start = duration - 0.5
        for i, sample in enumerate(samples):
            t = i / SAMPLE_RATE
            if t < attack:
                env = t / attack
            elif t > release_start:
                env = (duration - t) / 0.5
            else:
                env = 1.0

            # Simple low-pass for warmth
            result.append(int(sample * env * 32767 * 0.4))

        return self._save_wav("jupiter_pad", struct.pack(f'{len(result)}h', *result))

    def generate_jupiter_strings(self) -> str:
        """Jupiter string ensemble - orchestral sweep."""
        duration = 1.5
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        # String chord: D minor (D4, F4, A4)
        freqs = [293.7, 349.2, 440.0]

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            value = 0

            for freq in freqs:
                # Sawtooth with subtle detuning
                saw1 = 2 * ((freq * t) % 1) - 1
                saw2 = 2 * ((freq * 1.002 * t) % 1) - 1
                # Add vibrato
                vibrato = math.sin(2 * math.pi * 5 * t) * 0.01
                saw3 = 2 * ((freq * (1 + vibrato) * t) % 1) - 1
                value += (saw1 + saw2 + saw3) / 3

            value /= len(freqs)
            samples.append(value)

        # Heavy chorus for string effect
        samples = self._chorus_effect(samples, 0.005, 0.2)

        result = []
        attack = 0.2
        release_start = duration - 0.3
        for i, sample in enumerate(samples):
            t = i / SAMPLE_RATE
            if t < attack:
                env = t / attack
            elif t > release_start:
                env = (duration - t) / 0.3
            else:
                env = 1.0
            result.append(int(sample * env * 32767 * 0.35))

        return self._save_wav("jupiter_strings", struct.pack(f'{len(result)}h', *result))

    def generate_juno_stab(self) -> str:
        """Juno-106 stab - bright punchy chord."""
        duration = 0.4
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        # Bright chord: E major (E4, G#4, B4)
        freqs = [329.6, 415.3, 493.9]

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            value = 0

            for freq in freqs:
                # Pulse wave with PWM
                pwm = 0.5 + 0.2 * math.sin(2 * math.pi * 2 * t)
                phase = (freq * t) % 1
                pulse = 1 if phase < pwm else -1
                value += pulse

            value /= len(freqs)
            samples.append(value)

        # Light chorus
        samples = self._chorus_effect(samples, 0.002, 0.8)

        result = []
        for i, sample in enumerate(samples):
            t = i / SAMPLE_RATE
            # Quick attack, medium decay
            env = math.exp(-t * 6)
            result.append(int(sample * env * 32767 * 0.5))

        return self._save_wav("juno_stab", struct.pack(f'{len(result)}h', *result))

    def generate_juno_bell(self) -> str:
        """Juno bell - crystalline metallic tone."""
        duration = 1.0
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        base_freq = 880  # A5

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # FM synthesis for bell-like tones
            mod = math.sin(2 * math.pi * base_freq * 3.5 * t) * 2
            carrier = math.sin(2 * math.pi * base_freq * t + mod)
            # Add harmonics
            harm2 = math.sin(2 * math.pi * base_freq * 2 * t) * 0.3
            harm3 = math.sin(2 * math.pi * base_freq * 4 * t) * 0.15
            value = carrier * 0.6 + harm2 + harm3
            samples.append(value)

        result = []
        for i, sample in enumerate(samples):
            t = i / SAMPLE_RATE
            # Bell-like decay
            env = math.exp(-t * 3)
            result.append(int(sample * env * 32767 * 0.4))

        return self._save_wav("juno_bell", struct.pack(f'{len(result)}h', *result))

    def generate_jupiter_arp(self) -> str:
        """Jupiter arpeggiator pattern - sequenced notes."""
        note_duration = 0.12
        notes = [261.6, 329.6, 392.0, 523.2]  # C4, E4, G4, C5
        total_duration = note_duration * len(notes) * 2
        n_samples = int(SAMPLE_RATE * total_duration)
        samples = [0] * n_samples

        for note_idx in range(len(notes) * 2):
            freq = notes[note_idx % len(notes)]
            start = int(note_idx * note_duration * SAMPLE_RATE)
            end = min(start + int(note_duration * SAMPLE_RATE), n_samples)

            for i in range(start, end):
                t = (i - start) / SAMPLE_RATE
                # Pulse wave
                pwm = 0.5 + 0.1 * math.sin(2 * math.pi * 3 * t)
                phase = (freq * t) % 1
                pulse = 1 if phase < pwm else -1
                # Note envelope
                env = math.exp(-t * 15)
                samples[i] = pulse * env

        # Apply chorus
        samples = self._chorus_effect(samples, 0.002, 0.6)

        result = [int(s * 32767 * 0.5) for s in samples]
        return self._save_wav("jupiter_arp", struct.pack(f'{len(result)}h', *result))

    def generate_juno_lead(self) -> str:
        """Juno lead - monophonic singing lead."""
        duration = 0.6
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        base_freq = 440  # A4

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # Vibrato
            vibrato = math.sin(2 * math.pi * 5 * t) * 0.02
            freq = base_freq * (1 + vibrato)

            # PWM square
            pwm = 0.3 + 0.2 * math.sin(2 * math.pi * 0.5 * t)
            phase = (freq * t) % 1
            pulse = 1 if phase < pwm else -1
            samples.append(pulse)

        # Light chorus
        samples = self._chorus_effect(samples, 0.001, 1.0)

        result = []
        for i, sample in enumerate(samples):
            t = i / SAMPLE_RATE
            # Sustaining envelope
            if t < 0.05:
                env = t / 0.05
            elif t > duration - 0.1:
                env = (duration - t) / 0.1
            else:
                env = 1.0
            result.append(int(sample * env * 32767 * 0.5))

        return self._save_wav("juno_lead", struct.pack(f'{len(result)}h', *result))

    def generate_jupiter_brass(self) -> str:
        """Jupiter brass - fanfare-style brass chord."""
        duration = 0.8
        n_samples = int(SAMPLE_RATE * duration)
        samples = []

        # Brass chord: F major (F4, A4, C5)
        freqs = [349.2, 440.0, 523.2]

        for i in range(n_samples):
            t = i / SAMPLE_RATE
            value = 0

            for freq in freqs:
                # Sawtooth for brass
                saw = 2 * ((freq * t) % 1) - 1
                # Add second oscillator slightly detuned
                saw2 = 2 * ((freq * 1.005 * t) % 1) - 1
                value += (saw + saw2) / 2

            value /= len(freqs)
            samples.append(value)

        result = []
        for i, sample in enumerate(samples):
            t = i / SAMPLE_RATE
            # Brass attack-decay envelope
            if t < 0.1:
                env = t / 0.1
            elif t < 0.2:
                env = 1.0 - (t - 0.1) * 2  # Quick initial decay
            else:
                env = 0.8 * math.exp(-(t - 0.2) * 2)
            result.append(int(sample * env * 32767 * 0.5))

        return self._save_wav("jupiter_brass", struct.pack(f'{len(result)}h', *result))

    def generate_all_sounds(self) -> Dict[str, str]:
        """Generate all keyboard sounds."""
        print("Generating Roland Juno/Jupiter style keyboard sounds...")

        self.sounds = {
            'pad': self.generate_jupiter_pad(),
            'strings': self.generate_jupiter_strings(),
            'stab': self.generate_juno_stab(),
            'bell': self.generate_juno_bell(),
            'arp': self.generate_jupiter_arp(),
            'lead': self.generate_juno_lead(),
            'brass': self.generate_jupiter_brass(),
        }

        print(f"Generated {len(self.sounds)} keyboard sounds in {self.sounds_dir}")
        return self.sounds


# Action to sound mapping - organized by category
ACTION_SOUND_MAP = {
    # ═══════════════════════════════════════════════════════════════════════
    # DRUMS (TR-808/909) - Quick status events, rhythm foundation
    # ═══════════════════════════════════════════════════════════════════════
    'agent_spawn': 'kick',           # Deep kick for new agent
    'agent_terminate': 'snare',      # Snare for agent done
    'task_start': 'hihat_closed',    # Hi-hat closed for task start
    'task_complete': 'hihat_open',   # Hi-hat open for task done
    'error': 'clap',                 # Clap for errors
    'warning': 'cowbell',            # Cowbell for warnings
    'memory_store': 'tom_low',       # Low tom for memory write
    'memory_retrieve': 'tom_high',   # High tom for memory read
    'api_call': 'rimshot',           # Rimshot for API calls
    'cluster_sync': 'cymbal',        # Crash for cluster sync
    'health_check': 'maracas',       # Tick for health checks
    'heartbeat': 'heartbeat',        # Soft pulse for heartbeat

    # Modern EDM drums (when in tech_house/synthwave mode)
    'edm_kick': '909_kick',          # Punchy 909 kick
    'edm_snare': '909_snare',        # Crispy 909 snare
    'edm_hat': '909_hihat',          # Sizzling hat
    'edm_clap': '909_clap',          # Layered clap

    # ═══════════════════════════════════════════════════════════════════════
    # BASS (TB-303 + MOOG) - Workflow and process events
    # ═══════════════════════════════════════════════════════════════════════
    'workflow_start': 'bass_acid',   # Acid bass for workflow start
    'workflow_end': 'bass_sub',      # Sub bass for workflow completion
    'ai_inference': 'moog_bass',     # FAT Moog bass for AI processing
    'model_load': 'bass_pluck',      # Pluck bass for model loading
    'database_query': 'bass_growl',  # Growl bass for DB operations
    'mcp_call': 'bass_acid',         # Acid for MCP tool calls
    'thinking': 'bass_squelch',      # Squelch for deep thinking
    'deep_work': 'moog_bass',        # Moog bass for intensive processing
    'compilation': 'juno_bass',      # Juno bass for code compilation

    # ═══════════════════════════════════════════════════════════════════════
    # PADS & STRINGS (Juno-60 + Jupiter-8) - Ambient & session events
    # ═══════════════════════════════════════════════════════════════════════
    'session_start': 'juno_pad',     # Lush Juno pad for session start
    'session_end': 'jupiter_strings', # Jupiter strings for session end
    'ambient_layer': 'juno_pad',     # Background ambient pad
    'mood_shift': 'jupiter_strings', # Mood/genre transition
    'contemplation': 'juno_pad',     # Thinking/planning phase

    # ═══════════════════════════════════════════════════════════════════════
    # LEADS & STABS (Jupiter-8 + Moog) - Action & achievement events
    # ═══════════════════════════════════════════════════════════════════════
    'success': 'jupiter_brass',      # Majestic Jupiter brass for success
    'notification': 'bell',          # Crystal bell for notifications
    'reasoning': 'juno_arp',         # Shimmering Juno arp for reasoning
    'voice_activity': 'moog_lead',   # Screaming Moog lead for voice
    'cluster_message': 'jupiter_brass', # Jupiter brass for cluster comms
    'goal_achieved': 'jupiter_brass', # Brass fanfare for goal completion
    'learning': 'juno_arp',          # Juno arp for learning events
    'breakthrough': 'jupiter_sync',  # Hard sync lead for breakthroughs
    'creative': 'moog_lead',         # Moog lead for creative work

    # ═══════════════════════════════════════════════════════════════════════
    # EDM & TRANSITIONS - Energy builds and drops
    # ═══════════════════════════════════════════════════════════════════════
    'buildup': 'edm_riser',          # Rising tension for complex tasks
    'drop': 'edm_impact',            # Impact for task completion
    'intensity_increase': 'edm_riser', # Workload increasing
    'intensity_decrease': 'jupiter_strings', # Workload decreasing

    # ═══════════════════════════════════════════════════════════════════════
    # WAVE EVENTS - Parallel agent coordination
    # ═══════════════════════════════════════════════════════════════════════
    'wave_detected': 'jupiter_brass', # Jupiter brass for wave detection
    'wave_complete': 'jupiter_strings', # Strings for wave completion
    'infinite_loop': 'cymbal',       # Cymbal crash for infinite loop

    # ═══════════════════════════════════════════════════════════════════════
    # SYSTEM SOUNDS - Claude Code operations
    # ═══════════════════════════════════════════════════════════════════════
    'context_compact': 'context_compact',      # Session context compaction
    'file_read': 'file_read',                  # File read operation
    'file_write': 'file_write',                # File write operation
    'tool_call': 'tool_call',                  # Tool execution
    'memory_consolidate': 'memory_consolidate', # Memory consolidation (sleep)
    'code_execute': 'code_execute',            # Bash/code execution
    'search': 'search',                        # Grep/glob search
    'web_fetch': 'web_fetch',                  # Web fetch operation
    'cache_hit': 'cache_hit',                  # Cache hit (fast)
    'cache_miss': 'cache_miss',                # Cache miss
    'planning': 'planning',                    # Plan mode entered
    'streaming': 'streaming',                  # Streaming output
    'token_limit': 'token_limit',              # Token limit warning
    'agent_thinking': 'agent_thinking',        # Agent deep thinking
    'permission_request': 'permission_request', # Permission needed
    'git_commit': 'git_commit',                # Git commit made

    # ═══════════════════════════════════════════════════════════════════════
    # LEGACY MAPPINGS - Backward compatibility
    # ═══════════════════════════════════════════════════════════════════════
    'pad': 'juno_pad',               # Use Juno for pads
    'strings': 'jupiter_strings',    # Use Jupiter for strings
    'stab': 'jupiter_brass',         # Use Jupiter brass for stabs
    'arp': 'juno_arp',               # Use Juno for arps
    'lead': 'moog_lead',             # Use Moog for leads
    'brass': 'jupiter_brass',        # Use Jupiter for brass
}


# ═══════════════════════════════════════════════════════════════════════════
# GENRE-SPECIFIC SOUND MAPPINGS
# ═══════════════════════════════════════════════════════════════════════════

GENRE_SOUND_OVERRIDES = {
    'ambient': {
        'kick': 'kick',
        'snare': 'snare',
        'pad': 'juno_pad',
        'bass': 'bass_sub',
    },
    'lofi': {
        'kick': 'kick',
        'snare': 'snare',
        'pad': 'juno_pad',
        'bass': 'juno_bass',
        'arp': 'juno_arp',
    },
    'tech_house': {
        'kick': '909_kick',
        'snare': '909_clap',
        'hihat': '909_hihat',
        'bass': 'moog_bass',
        'stab': 'jupiter_brass',
    },
    'synthwave': {
        'kick': '909_kick',
        'snare': '909_snare',
        'bass': 'moog_bass',
        'pad': 'juno_pad',
        'lead': 'moog_lead',
        'arp': 'juno_arp',
    },
    'minimal': {
        'kick': 'kick',
        'hihat': 'hihat_closed',
        'bass': 'bass_pluck',
        'pad': 'juno_pad',
    },
    'epic': {
        'kick': '909_kick',
        'snare': '909_snare',
        'bass': 'moog_bass',
        'strings': 'jupiter_strings',
        'brass': 'jupiter_brass',
        'impact': 'edm_impact',
    },
}


class RealtimeSoundtrackEngine:
    """Advanced realtime soundtrack engine for agentic operations.

    Features:
    - Intelligent drum pattern sequencing with genre presets
    - Adaptive tempo based on workload intensity
    - Chord progression engine for evolving harmonies
    - Stereo spatial positioning for immersive audio
    - Effects processing (reverb, delay, compression)
    - Real-time event integration for dynamic response

    This transforms random beeps into a cohesive musical experience!
    """

    def __init__(self, bpm: float = 90, time_signature: tuple = (4, 4)):
        self.bpm = bpm
        self.target_bpm = bpm
        self.beats_per_bar = time_signature[0]
        self.beat_unit = time_signature[1]
        self.beat_duration = 60.0 / bpm
        self.bar_duration = self.beat_duration * self.beats_per_bar

        # Sound queue for triggered events
        self.sound_queue = []
        self.queue_lock = threading.Lock()

        # Sequencer state
        self.running = False
        self.current_step = 0  # 0-15 for 16-step pattern
        self.current_bar = 0
        self.current_beat = 0
        self.start_time = 0.0

        # Genre/mood system - Start with FF Field (subtle background like FF towns)
        self.current_genre = 'ff_field'  # Calm exploration vibes
        self.genre_preset: GenrePreset = GENRE_PRESETS['ff_field']
        self.transition_bars = 0  # Bars until genre change completes

        # Drum pattern system
        self.current_pattern = DRUM_PATTERNS['ambient_minimal']
        self.pattern_variation = 0.0  # 0-1, adds randomness to patterns
        self.fill_probability = 0.1  # Chance of drum fill at bar end

        # Chord progression system
        self.current_progression_idx = 0
        self.current_chord_idx = 0
        self.chord_change_bars = 4  # Bars per chord
        self.bars_on_current_chord = 0

        # Workload tracking for adaptive music
        self.workload = WorkloadState()

        # Self-learning musical intelligence
        self.learner = MusicLearner()

        # Activity and ambient settings
        self.ambient_mode = True
        self.drums_enabled = True
        self.bass_enabled = True
        self.pads_enabled = True
        self.activity_level = 0.0
        self.activity_decay = 0.75  # Faster decay for better dynamic range

        # Quantization settings
        self.quantize_to = 'sixteenth'  # Finer quantization for patterns
        self.humanize = 0.015  # Subtle timing variation
        self.swing = 0.0  # Updated from genre preset

        # Sound priorities
        self.priority_map = {
            'pad': 1, 'strings': 1, 'memory_consolidate': 1,
            'kick': 5, 'snare': 5, 'bass_acid': 5,
            'hihat_closed': 3, 'hihat_open': 3, 'maracas': 3,
            'stab': 7, 'brass': 7, 'bell': 7,
            'context_compact': 6, 'success': 8, 'error': 9,
        }

        # Ambient layer sounds
        self.ambient_sounds = ['pad', 'strings', 'memory_consolidate']

    def set_genre(self, genre_name: str, transition_bars: int = 4):
        """Smoothly transition to a new genre."""
        if genre_name not in GENRE_PRESETS:
            print(f"Unknown genre: {genre_name}. Available: {list(GENRE_PRESETS.keys())}")
            return

        # Record transition for learning
        old_genre = self.current_genre
        self.learner.record_transition(old_genre, genre_name)

        self.current_genre = genre_name
        self.genre_preset = GENRE_PRESETS[genre_name]
        self.transition_bars = transition_bars

        # Update settings from genre preset
        self.target_bpm = random.randint(*self.genre_preset.bpm_range)
        self.swing = self.genre_preset.swing

        # Record genre for learning
        self.learner.record_pattern(self.current_pattern or 'default', genre_name)

        # Select appropriate drum pattern
        if genre_name == 'ambient':
            self.current_pattern = DRUM_PATTERNS['ambient_minimal']
        elif genre_name == 'lofi':
            self.current_pattern = DRUM_PATTERNS['lofi_groove']
        elif genre_name == 'tech_house':
            self.current_pattern = DRUM_PATTERNS['tech_driving']
        elif genre_name == 'synthwave':
            self.current_pattern = DRUM_PATTERNS['four_on_floor']
        elif genre_name == 'minimal':
            self.current_pattern = DRUM_PATTERNS['ambient_minimal']
        elif genre_name == 'epic':
            self.current_pattern = DRUM_PATTERNS['breakbeat']

        print(f"Transitioning to {self.genre_preset.name} ({self.target_bpm} BPM) over {transition_bars} bars")

    def adapt_to_workload(self):
        """Automatically adjust music based on workload intensity.

        Final Fantasy style - smooth transitions between calm and intense:
        - idle: Pure ambient pads (ff_prelude)
        - light: Gentle field theme (ff_field)
        - active: Building energy (minimal/synthwave)
        - intense: Battle theme (epic/ff_boss)
        """
        self.workload.update()
        intensity = self.workload.current_intensity
        level = self.workload.get_intensity_level()

        # FF-style genre mapping - gradual peaceful-to-battle transitions
        # Use longer transition times for smoother feel
        if level == 'idle':
            # Pure ambient - ethereal pads only
            if self.current_genre not in ['ambient', 'ff_prelude']:
                self.set_genre('ff_prelude', transition_bars=16)  # Very slow transition
        elif level == 'light':
            # Calm exploration
            if self.current_genre not in ['ff_field', 'lofi', 'ambient']:
                self.set_genre('ff_field', transition_bars=8)
        elif level == 'active':
            # Building tension - choose based on intensity within level
            if intensity < 0.65:
                if self.current_genre not in ['minimal', 'lofi']:
                    self.set_genre('minimal', transition_bars=4)
            else:
                if self.current_genre not in ['synthwave', 'minimal']:
                    self.set_genre('synthwave', transition_bars=4)
        elif level == 'intense':
            # Battle mode! But still subtle background
            if intensity < 0.85:
                if self.current_genre not in ['epic', 'synthwave']:
                    self.set_genre('epic', transition_bars=2)
            else:
                # Full boss battle mode - only for very high activity
                if self.current_genre != 'ff_boss':
                    self.set_genre('ff_boss', transition_bars=2)

        # Adjust BPM based on intensity within genre range
        # Cap at 75 BPM for subtle background music
        preset = self.genre_preset
        bpm_range = preset.bpm_range[1] - preset.bpm_range[0]
        calculated_bpm = preset.bpm_range[0] + int(bpm_range * intensity)
        self.target_bpm = min(calculated_bpm, 75)  # Never exceed 75 BPM

        # Very smooth BPM interpolation for cinematic feel
        bpm_diff = self.target_bpm - self.bpm
        self.bpm += bpm_diff * 0.01  # Extra smooth interpolation
        self.beat_duration = 60.0 / self.bpm

        # Auto-learning: Record current state and provide implicit feedback
        # High intensity accuracy = music is tracking workload well = positive
        if hasattr(self, 'learner'):
            eval_data = {
                'intensity': {
                    'accuracy': 1.0 - abs(intensity - self.activity_level)
                },
                'workload': {
                    'events_per_minute': self.workload.events_per_minute
                }
            }
            self.learner.auto_feedback_from_eval(eval_data)

    def get_current_chord(self) -> List[int]:
        """Get current chord notes based on progression."""
        mood = self.genre_preset.chord_mood
        progressions = CHORD_PROGRESSIONS.get(mood, CHORD_PROGRESSIONS['ambient'])
        progression = progressions[self.current_progression_idx % len(progressions)]
        chord_info = progression[self.current_chord_idx % len(progression)]

        root_offset, chord_type = chord_info
        base_note = self.genre_preset.base_key + root_offset

        # Get chord intervals
        if 'major' in chord_type:
            intervals = ChordType.MAJOR.value
        elif 'minor7' in chord_type:
            intervals = ChordType.MINOR_SEVENTH.value
        elif 'dom7' in chord_type:
            intervals = ChordType.SEVENTH.value
        elif 'minor' in chord_type:
            intervals = ChordType.MINOR.value
        else:
            intervals = ChordType.MAJOR.value

        return [base_note + i for i in intervals]

    def advance_chord(self):
        """Move to next chord in progression."""
        self.bars_on_current_chord += 1
        if self.bars_on_current_chord >= self.chord_change_bars:
            self.bars_on_current_chord = 0
            self.current_chord_idx += 1

            mood = self.genre_preset.chord_mood
            progressions = CHORD_PROGRESSIONS.get(mood, CHORD_PROGRESSIONS['ambient'])
            progression = progressions[self.current_progression_idx % len(progressions)]

            if self.current_chord_idx >= len(progression):
                self.current_chord_idx = 0
                self.current_progression_idx += 1

    def get_pattern_step(self, step: int) -> Dict[str, float]:
        """Get drum sounds to play at this step."""
        pattern = self.current_pattern
        step_idx = step % pattern.steps

        sounds = {}

        # Add variation based on genre intensity
        variation = self.genre_preset.drum_density * self.pattern_variation

        if pattern.kick[step_idx] > 0:
            sounds['kick'] = pattern.kick[step_idx]
        if pattern.snare[step_idx] > 0:
            sounds['snare'] = pattern.snare[step_idx]
        if pattern.hihat[step_idx] > 0:
            sounds['hihat_closed'] = pattern.hihat[step_idx]
        if pattern.hihat_open[step_idx] > 0:
            sounds['hihat_open'] = pattern.hihat_open[step_idx]
        if pattern.clap[step_idx] > 0:
            sounds['clap'] = pattern.clap[step_idx]
        if pattern.perc[step_idx] > 0:
            sounds['cowbell'] = pattern.perc[step_idx]

        # Random ghost notes based on drum density
        if random.random() < variation * 0.3:
            if random.random() < 0.5:
                sounds['hihat_closed'] = sounds.get('hihat_closed', 0) + random.uniform(0.2, 0.5)

        return sounds

    def should_play_fill(self) -> bool:
        """Check if we should play a drum fill."""
        # More fills at bar end, especially during transitions
        if self.current_step >= 12:  # Last 4 steps of 16
            probability = self.fill_probability
            if self.transition_bars > 0:
                probability *= 2
            return random.random() < probability
        return False

    def get_swing_offset(self, step: int) -> float:
        """Calculate swing timing offset for a step."""
        if self.swing <= 0:
            return 0.0

        # Swing affects off-beats (odd steps)
        if step % 2 == 1:
            return self.swing * self.beat_duration * 0.3
        return 0.0


# Create backward-compatible alias
class AmbientSequencer(RealtimeSoundtrackEngine):
    """Backward-compatible alias for RealtimeSoundtrackEngine.

    Musical sequencer for ambient, fluid sound generation.
    Queues sounds to play on beat for more musical, less jarring output.
    Provides ambient background rhythm and quantizes action sounds to grid.
    """
    pass


# Keep old AmbientSequencer methods available
AmbientSequencer.queue_sound = lambda self, sound_name, immediate=False: self._queue_sound(sound_name, immediate)


def _queue_sound_impl(self, sound_name: str, immediate: bool = False):
    """Queue a sound for playback on next beat/division.

    Sound stacking consolidation: Instead of playing 5 hits stacked,
    consolidate into 1-2 LOUDER hits for better dynamics and rhythm.
    """
    with self.queue_lock:
        now = time.time()
        priority = self.priority_map.get(sound_name, 5)

        # Check for recent duplicate sounds - consolidate into louder hit
        existing = None
        for item in self.sound_queue:
            if item['sound'] == sound_name and (now - item['queued_at']) < 0.5:
                existing = item
                break

        if existing:
            # Boost velocity/priority instead of adding duplicate
            # Cap at 1.5x volume to avoid distortion
            existing['velocity'] = min(1.5, existing.get('velocity', 1.0) + 0.15)
            existing['priority'] = min(10, existing['priority'] + 1)
            # Don't add another sound - just boosted existing
        else:
            # Max 2 of same sound in queue
            same_count = sum(1 for s in self.sound_queue if s['sound'] == sound_name)
            if same_count < 2:
                self.sound_queue.append({
                    'sound': sound_name,
                    'priority': priority,
                    'velocity': 1.0,  # Base velocity
                    'immediate': immediate,
                    'queued_at': now
                })

        # Activity bump varies by sound type for better dynamic range
        activity_bumps = {
            'heartbeat': 0.01,      # Barely affects activity
            'pad': 0.0,             # Ambient pads don't add activity
            'pad_warm': 0.0,
            'pad_crystal': 0.0,
            'pad_dark': 0.0,
            'file_read': 0.03,      # Reading is calm
            'search': 0.04,
            'file_write': 0.06,
            'error': 0.12,          # Errors are notable
            'agent_spawn': 0.08,
        }
        bump = activity_bumps.get(sound_name, 0.05)  # Default 0.05 (was 0.1)
        self.activity_level = min(1.0, self.activity_level + bump)

        # Record event for workload tracking
        self.workload.record_event(sound_name)


AmbientSequencer._queue_sound = _queue_sound_impl
AmbientSequencer.queue_sound = lambda self, sound_name, immediate=False: self._queue_sound(sound_name, immediate)

# Also add to RealtimeSoundtrackEngine (which extends/replaces AmbientSequencer)
RealtimeSoundtrackEngine._queue_sound = _queue_sound_impl
RealtimeSoundtrackEngine.queue_sound = lambda self, sound_name, immediate=False: self._queue_sound(sound_name, immediate)


# Add remaining methods to RealtimeSoundtrackEngine class
def _get_quantize_divisions(self) -> int:
    """Get number of divisions per beat based on quantize setting."""
    divisions = {
        'beat': 1, 'half': 2, 'quarter': 1,
        'eighth': 2, 'sixteenth': 4
    }
    return divisions.get(self.quantize_to, 2)


def _time_to_next_division(self) -> float:
    """Calculate time until next quantized division."""
    if not self.running or self.start_time == 0:
        return 0

    now = time.time()
    elapsed = now - self.start_time
    division_duration = self.beat_duration / self.get_quantize_divisions()
    current_division = elapsed / division_duration
    next_division = math.ceil(current_division)
    time_to_next = (next_division * division_duration) - elapsed

    # Add humanization
    if self.humanize > 0:
        time_to_next += random.uniform(-self.humanize, self.humanize)

    return max(0, time_to_next)


def _get_queued_sounds(self) -> list:
    """Get sounds ready to play, sorted by priority."""
    with self.queue_lock:
        # Sort by priority (higher first), then by queue time
        sounds = sorted(self.sound_queue,
                       key=lambda x: (-x['priority'], x['queued_at']))
        self.sound_queue = []
        return sounds


def _update_activity(self):
    """Decay activity level over time."""
    self.activity_level *= self.activity_decay


def _get_ambient_intensity(self) -> float:
    """Get ambient layer intensity based on activity."""
    # Less ambient when more active, more ambient when idle
    return max(0.2, 1.0 - self.activity_level * 0.8)


def _should_play_ambient(self) -> bool:
    """Determine if ambient sound should play this beat."""
    if not self.ambient_mode:
        return False
    # Higher chance when activity is low
    threshold = 0.3 * self.get_ambient_intensity()
    return random.random() < threshold


def _get_beat_info(self) -> dict:
    """Get current beat position info."""
    return {
        'bar': self.current_bar,
        'beat': self.current_beat,
        'step': self.current_step,
        'bpm': self.bpm,
        'genre': self.current_genre,
        'intensity': self.workload.current_intensity,
        'activity': self.activity_level,
        'ambient_intensity': self.get_ambient_intensity()
    }


# Attach methods to RealtimeSoundtrackEngine
RealtimeSoundtrackEngine.get_quantize_divisions = _get_quantize_divisions
RealtimeSoundtrackEngine.time_to_next_division = _time_to_next_division
RealtimeSoundtrackEngine.get_queued_sounds = _get_queued_sounds
RealtimeSoundtrackEngine.update_activity = _update_activity
RealtimeSoundtrackEngine.get_ambient_intensity = _get_ambient_intensity
RealtimeSoundtrackEngine.should_play_ambient = _should_play_ambient
RealtimeSoundtrackEngine.get_beat_info = _get_beat_info


class AgenticSoundSystem:
    """Complete synthesizer sound system for agentic actions.

    Includes:
    - TR-808/909 drums (classic analog drum machine)
    - TB-303 bass (acid bass lines)
    - Juno/Jupiter keyboards (lush pads and brass)
    - Moog synthesizers (fat bass and screaming leads)
    - Juno-60 (iconic chorus pads and arps)
    - Jupiter-8 (legendary polysynth brass and strings)
    - Electro-pop/EDM sounds (909 drums, risers, impacts)
    - System utility sounds (Claude Code operations)

    Features:
    - Realtime adaptive soundtrack engine
    - Genre/mood presets (ambient, lofi, tech_house, synthwave, minimal, epic)
    - Intelligent drum pattern sequencing
    - Workload-adaptive tempo and intensity
    - Stereo spatial audio positioning
    """

    def __init__(self, sounds_dir: str = None):
        # Original Roland synths
        self.drum_synth = RolandDrumSynthesizer(sounds_dir)
        self.bass_synth = RolandBassSynthesizer(sounds_dir)
        self.keyboard_synth = RolandKeyboardSynthesizer(sounds_dir)
        self.system_synth = SystemSoundSynthesizer(sounds_dir)

        # Enhanced vintage synths
        self.moog_synth = MoogSynthesizer(sounds_dir)
        self.juno_synth = Juno60Synthesizer(sounds_dir)
        self.jupiter_synth = Jupiter8Synthesizer(sounds_dir)
        self.electro_synth = ElectroPop909Synthesizer(sounds_dir)

        self.sounds = {}
        self.running = False
        self.http_port = 8766
        self.last_played = {}
        self.min_interval = 0.1  # Minimum seconds between same sound
        # ThreadPoolExecutor for non-blocking sound playback without zombies
        self._executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="sound_player")
        # Set up SIGCHLD handler to auto-reap any stray children
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)

        # Realtime soundtrack engine (enhanced sequencer)
        self.sequencer = RealtimeSoundtrackEngine(bpm=75)  # FF-style background tempo
        self.ambient_mode = True  # Enable ambient mode by default
        self.sequencer_thread = None

        # Current genre/mood - Start with FF field theme (subtle background)
        self.current_genre = 'ff_field'

    def initialize(self):
        """Initialize and generate all sounds from all synthesizers."""
        print("\n" + "=" * 70)
        print("🎹 AGENTIC REALTIME SOUNDTRACK ENGINE 🎹")
        print("   Vintage Synth Collection: Moog • Juno-60 • Jupiter-8 • TR-808/909")
        print("=" * 70 + "\n")

        # Generate sounds from all synthesizers
        print("Loading synthesizers...\n")

        # Original Roland synths
        drum_sounds = self.drum_synth.generate_all_sounds()
        bass_sounds = self.bass_synth.generate_all_sounds()
        keyboard_sounds = self.keyboard_synth.generate_all_sounds()
        system_sounds = self.system_synth.generate_all_sounds()

        # Enhanced vintage synths
        moog_sounds = self.moog_synth.generate_all_sounds()
        juno_sounds = self.juno_synth.generate_all_sounds()
        jupiter_sounds = self.jupiter_synth.generate_all_sounds()
        electro_sounds = self.electro_synth.generate_all_sounds()

        # Merge all sounds
        self.sounds = {
            **drum_sounds,
            **bass_sounds,
            **keyboard_sounds,
            **system_sounds,
            **moog_sounds,
            **juno_sounds,
            **jupiter_sounds,
            **electro_sounds
        }

        # Configure ambient sounds for sequencer (use lush synths)
        self.sequencer.ambient_sounds = [
            'juno_pad', 'jupiter_strings', 'pad', 'strings',
            'memory_consolidate', 'heartbeat'
        ]

        print(f"\n{'─' * 70}")
        print(f"✨ Total: {len(self.sounds)} sounds generated across 8 synthesizers")
        print(f"{'─' * 70}")
        print("\n" + "-" * 60)
        print("Action-to-Sound Mapping:")
        print("-" * 60)

        # Group by category
        print("\n[DRUMS - TR-808/909]")
        for action in ['agent_spawn', 'agent_terminate', 'task_start', 'task_complete',
                      'error', 'warning', 'memory_store', 'memory_retrieve',
                      'api_call', 'cluster_sync', 'health_check', 'heartbeat']:
            if action in ACTION_SOUND_MAP:
                print(f"  {action:20} -> {ACTION_SOUND_MAP[action]}")

        print("\n[BASS - TB-303]")
        for action in ['workflow_start', 'workflow_end', 'ai_inference', 'model_load',
                      'database_query', 'mcp_call', 'thinking']:
            if action in ACTION_SOUND_MAP:
                print(f"  {action:20} -> {ACTION_SOUND_MAP[action]}")

        print("\n[KEYBOARDS - Juno/Jupiter]")
        for action in ['session_start', 'session_end', 'success', 'notification',
                      'reasoning', 'voice_activity', 'cluster_message', 'goal_achieved', 'learning']:
            if action in ACTION_SOUND_MAP:
                print(f"  {action:20} -> {ACTION_SOUND_MAP[action]}")

        print("\n[SYSTEM - Claude Code Operations]")
        for action in ['context_compact', 'file_read', 'file_write', 'tool_call',
                      'memory_consolidate', 'code_execute', 'search', 'web_fetch',
                      'cache_hit', 'cache_miss', 'planning', 'streaming',
                      'token_limit', 'agent_thinking', 'permission_request', 'git_commit']:
            if action in ACTION_SOUND_MAP:
                print(f"  {action:20} -> {ACTION_SOUND_MAP[action]}")

    def play_sound(self, sound_name: str, use_sequencer: bool = None):
        """Play a sound file.

        Args:
            sound_name: Name of the sound to play
            use_sequencer: If True, queue for sequencer. If None, use self.ambient_mode
        """
        if sound_name not in self.sounds:
            print(f"Unknown sound: {sound_name}")
            return

        # Determine if we should use sequencer
        should_sequence = use_sequencer if use_sequencer is not None else self.ambient_mode

        if should_sequence and self.sequencer.running:
            # Queue sound for quantized playback
            self.sequencer.queue_sound(sound_name)
            return

        # Direct playback
        self._play_sound_direct(sound_name)

    def _play_sound_direct(self, sound_name: str, volume_override: float = None):
        """Play sound immediately without sequencing.

        Args:
            sound_name: Name of sound to play
            volume_override: Override master volume (0.0-1.0), or use genre's master_volume
        """
        # Rate limit
        now = time.time()
        if sound_name in self.last_played:
            if now - self.last_played[sound_name] < self.min_interval:
                return
        self.last_played[sound_name] = now

        filepath = self.sounds[sound_name]

        # Get volume from genre preset (0.0-1.0) - subtle by default!
        volume = volume_override if volume_override is not None else self.sequencer.genre_preset.master_volume
        # Convert to PulseAudio percentage (65536 = 100%)
        pa_volume = int(volume * 65536)

        def _play_in_thread():
            """Play sound in thread using subprocess.run() to avoid zombies."""
            try:
                # Use afplay on macOS, paplay on Linux (with volume control!)
                # subprocess.run() waits for completion and properly reaps the process
                if sys.platform == 'darwin':
                    # macOS afplay: volume is 0.0-1.0
                    subprocess.run(['afplay', '-v', str(volume), filepath],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    # Linux paplay: volume in PulseAudio units (65536 = 100%)
                    # Falls back to aplay if paplay isn't available
                    try:
                        subprocess.run(['paplay', '--volume=' + str(pa_volume), filepath],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        # Fallback to aplay (no volume control, but works)
                        subprocess.run(['aplay', '-q', filepath],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"Error playing sound: {e}")

        # Submit to thread pool - non-blocking, no zombies
        self._executor.submit(_play_in_thread)

    def play_action(self, action: str, immediate: bool = False):
        """Play sound for an agentic action.

        Args:
            action: Action name from ACTION_SOUND_MAP
            immediate: If True, play immediately even in sequencer mode
        """
        sound_name = ACTION_SOUND_MAP.get(action)
        if sound_name:
            if immediate:
                self._play_sound_direct(sound_name)
            else:
                self.play_sound(sound_name)
        else:
            print(f"Unknown action: {action}")

    def start_sequencer(self):
        """Start the ambient sequencer loop."""
        if self.sequencer_thread and self.sequencer_thread.is_alive():
            print("Sequencer already running")
            return

        self.sequencer.running = True
        self.sequencer.start_time = time.time()

        def sequencer_loop():
            """Main sequencer loop - plays actual drum patterns!"""
            # 16-step sequencer at sixteenth note resolution
            step_duration = self.sequencer.beat_duration / 4  # 4 steps per beat
            last_bar = -1

            print(f"🎵 Starting pattern sequencer: {self.sequencer.bpm:.0f} BPM, genre: {self.sequencer.current_genre}")

            while self.sequencer.running and self.running:
                loop_start = time.time()

                # Calculate current position
                elapsed = loop_start - self.sequencer.start_time
                total_steps = int(elapsed / step_duration)
                self.sequencer.current_step = total_steps % 16  # 16-step pattern
                self.sequencer.current_beat = (total_steps // 4) % self.sequencer.beats_per_bar
                new_bar = total_steps // 16

                # Bar changed - advance chord, maybe change pattern
                if new_bar != last_bar:
                    last_bar = new_bar
                    self.sequencer.current_bar = new_bar
                    self.sequencer.advance_chord()

                    # Decrease transition countdown
                    if self.sequencer.transition_bars > 0:
                        self.sequencer.transition_bars -= 1

                    # Adapt to workload every few bars
                    if new_bar % 4 == 0:
                        self.sequencer.adapt_to_workload()

                    # Play ambient pad based on genre's pad_prominence
                    pad_chance = self.sequencer.genre_preset.pad_prominence * 0.6  # Scale to reasonable range
                    if self.sequencer.pads_enabled and random.random() < pad_chance:
                        ambient = random.choice(self.sequencer.ambient_sounds)
                        if ambient in self.sounds:
                            self._play_sound_direct(ambient)

                # === PLAY DRUM PATTERN ===
                if self.sequencer.drums_enabled:
                    step_sounds = self.sequencer.get_pattern_step(self.sequencer.current_step)

                    for sound_name, velocity in step_sounds.items():
                        if velocity > 0 and random.random() < velocity:
                            # Map to genre-specific sound if available
                            genre = self.sequencer.current_genre
                            if genre in GENRE_SOUND_OVERRIDES:
                                overrides = GENRE_SOUND_OVERRIDES[genre]
                                sound_name = overrides.get(sound_name, sound_name)

                            if sound_name in self.sounds:
                                self._play_sound_direct(sound_name)

                # === PLAY BASS ON DOWNBEATS ===
                if self.sequencer.bass_enabled and self.sequencer.current_step in [0, 8]:
                    if random.random() < self.sequencer.genre_preset.bass_prominence * 0.3:
                        genre = self.sequencer.current_genre
                        bass_sound = GENRE_SOUND_OVERRIDES.get(genre, {}).get('bass', 'bass_acid')
                        if bass_sound in self.sounds:
                            self._play_sound_direct(bass_sound)

                # === PLAY QUEUED EVENT SOUNDS ===
                # Use velocity for volume dynamics - louder hits instead of more hits
                queued = self.sequencer.get_queued_sounds()
                for item in queued[:2]:  # Limit to 2 concurrent (was 3)
                    sound = item['sound']
                    if sound in self.sounds:
                        # Scale volume by velocity (1.0-1.5x based on stacked events)
                        velocity = item.get('velocity', 1.0)
                        base_volume = self.sequencer.genre_preset.master_volume
                        volume = min(0.9, base_volume * velocity)  # Cap at 0.9 for headroom
                        self._play_sound_direct(sound, volume_override=volume)

                # Update activity decay
                self.sequencer.update_activity()

                # Smooth BPM changes
                if abs(self.sequencer.target_bpm - self.sequencer.bpm) > 0.5:
                    self.sequencer.bpm += (self.sequencer.target_bpm - self.sequencer.bpm) * 0.02
                    self.sequencer.beat_duration = 60.0 / self.sequencer.bpm
                    step_duration = self.sequencer.beat_duration / 4

                # Apply swing to off-beats
                swing_offset = self.sequencer.get_swing_offset(self.sequencer.current_step)

                # Wait until next step
                elapsed_in_loop = time.time() - loop_start
                sleep_time = step_duration + swing_offset - elapsed_in_loop
                if sleep_time > 0:
                    time.sleep(sleep_time)

        self.sequencer_thread = threading.Thread(target=sequencer_loop, daemon=True)
        self.sequencer_thread.start()
        print(f"Sequencer started: {self.sequencer.bpm} BPM, quantize to {self.sequencer.quantize_to}")

    def stop_sequencer(self):
        """Stop the ambient sequencer."""
        self.sequencer.running = False
        print("Sequencer stopped")

    def set_bpm(self, bpm: float):
        """Change sequencer BPM."""
        self.sequencer.bpm = bpm
        self.sequencer.beat_duration = 60.0 / bpm
        self.sequencer.bar_duration = self.sequencer.beat_duration * self.sequencer.beats_per_bar
        print(f"BPM set to {bpm}")

    def start_http_server(self):
        """Start HTTP server for receiving action notifications."""
        sound_system = self

        class ActionHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path == '/action':
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode()
                    try:
                        data = json.loads(body)
                        action = data.get('action')
                        if action:
                            sound_system.play_action(action)
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({'success': True, 'action': action}).encode())
                        else:
                            self.send_response(400)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({'error': 'action required'}).encode())
                    except Exception as e:
                        self.send_response(400)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': str(e)}).encode())

                elif self.path == '/sound':
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode()
                    try:
                        data = json.loads(body)
                        sound = data.get('sound')
                        if sound:
                            sound_system.play_sound(sound)
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({'success': True, 'sound': sound}).encode())
                        else:
                            self.send_response(400)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({'error': 'sound required'}).encode())
                    except Exception as e:
                        self.send_response(400)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': str(e)}).encode())

                elif self.path == '/sequence':
                    # Play a sequence of sounds (for musical patterns)
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode()
                    try:
                        data = json.loads(body)
                        sounds = data.get('sounds', [])
                        delay = data.get('delay', 0.2)
                        for sound in sounds:
                            sound_system.play_sound(sound)
                            time.sleep(delay)
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'success': True, 'played': len(sounds)}).encode())
                    except Exception as e:
                        self.send_response(400)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': str(e)}).encode())

                elif self.path == '/sequencer':
                    # Sequencer control
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode()
                    try:
                        data = json.loads(body)
                        cmd = data.get('command')
                        result = {'success': True}

                        if cmd == 'start':
                            sound_system.start_sequencer()
                            result['status'] = 'started'
                        elif cmd == 'stop':
                            sound_system.stop_sequencer()
                            result['status'] = 'stopped'
                        elif cmd == 'bpm':
                            bpm = data.get('bpm', 75)
                            sound_system.set_bpm(float(bpm))
                            result['bpm'] = bpm
                        elif cmd == 'ambient':
                            enabled = data.get('enabled', True)
                            sound_system.ambient_mode = enabled
                            sound_system.sequencer.ambient_mode = enabled
                            result['ambient_mode'] = enabled
                        elif cmd == 'quantize':
                            quantize = data.get('quantize', 'eighth')
                            sound_system.sequencer.quantize_to = quantize
                            result['quantize'] = quantize
                        else:
                            result = {'error': 'Unknown command. Use: start, stop, bpm, ambient, quantize'}

                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(result).encode())
                    except Exception as e:
                        self.send_response(400)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': str(e)}).encode())

                elif self.path == '/learn/feedback':
                    # Submit feedback: POST {"type": "positive"} or {"type": "negative"}
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode()
                    try:
                        data = json.loads(body)
                        fb_type = data.get('type', 'positive')
                        learner = sound_system.sequencer.learner
                        if fb_type == 'positive':
                            learner.feedback_positive()
                        else:
                            learner.feedback_negative()
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            'success': True,
                            'feedback': fb_type,
                            'message': f'Recorded {fb_type} feedback - learning updated!'
                        }).encode())
                    except Exception as e:
                        self.send_response(400)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': str(e)}).encode())

                else:
                    self.send_response(404)
                    self.end_headers()

            def do_GET(self):
                if self.path == '/sounds':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()

                    # Categorize sounds
                    drums = ['kick', 'snare', 'hihat_closed', 'hihat_open', 'clap',
                            'cowbell', 'tom_low', 'tom_high', 'rimshot', 'cymbal',
                            'maracas', 'heartbeat']
                    bass = ['bass_acid', 'bass_sub', 'bass_squelch', 'bass_pluck', 'bass_growl']
                    keys = ['pad', 'strings', 'stab', 'bell', 'arp', 'lead', 'brass']
                    system = ['context_compact', 'file_read', 'file_write', 'tool_call',
                             'memory_consolidate', 'code_execute', 'search', 'web_fetch',
                             'cache_hit', 'cache_miss', 'planning', 'streaming',
                             'token_limit', 'agent_thinking', 'permission_request', 'git_commit']

                    self.wfile.write(json.dumps({
                        'sounds': list(sound_system.sounds.keys()),
                        'categories': {
                            'drums_808': drums,
                            'bass_303': bass,
                            'keyboards_juno_jupiter': keys,
                            'system_utility': system
                        },
                        'actions': list(ACTION_SOUND_MAP.keys()),
                        'mapping': ACTION_SOUND_MAP
                    }, indent=2).encode())

                elif self.path == '/health':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'status': 'running',
                        'sounds_loaded': len(sound_system.sounds),
                        'actions_mapped': len(ACTION_SOUND_MAP),
                        'sequencer_running': sound_system.sequencer.running,
                        'ambient_mode': sound_system.ambient_mode,
                        'bpm': sound_system.sequencer.bpm
                    }).encode())

                elif self.path == '/sequencer/status':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    beat_info = sound_system.sequencer.get_beat_info()
                    self.wfile.write(json.dumps({
                        'running': sound_system.sequencer.running,
                        'ambient_mode': sound_system.ambient_mode,
                        'bpm': sound_system.sequencer.bpm,
                        'quantize': sound_system.sequencer.quantize_to,
                        'current_bar': beat_info['bar'],
                        'current_beat': beat_info['beat'],
                        'activity_level': round(beat_info['activity'], 3),
                        'ambient_intensity': round(beat_info['ambient_intensity'], 3)
                    }).encode())

                elif self.path == '/eval':
                    # Comprehensive eval metrics for self-improvement
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()

                    seq = sound_system.sequencer
                    workload = seq.workload
                    intensity_level = workload.get_intensity_level()

                    # Calculate intensity accuracy (how well we match target)
                    intensity_targets = {'idle': 0.15, 'light': 0.4, 'active': 0.7, 'intense': 0.95}
                    target = intensity_targets.get(intensity_level, 0.5)
                    accuracy = 1.0 - abs(workload.current_intensity - target)

                    eval_data = {
                        'timestamp': time.time(),
                        'intensity': {
                            'level': intensity_level,
                            'current': round(workload.current_intensity, 3),
                            'target': round(workload.target_intensity, 3),
                            'accuracy': round(accuracy, 3)
                        },
                        'workload': {
                            'events_per_minute': round(workload.events_per_minute, 1),
                            'event_history_size': len(workload.event_history),
                            'seconds_since_last_event': round(time.time() - workload.last_event_time, 1)
                        },
                        'sequencer': {
                            'bpm': seq.bpm,
                            'genre': seq.genre_preset.name if seq.genre_preset else 'unknown',
                            'activity_level': round(seq.activity_level, 3),
                            'sounds_queued': len(seq.sound_queue),
                            'running': seq.running
                        },
                        'performance': {
                            'sounds_loaded': len(sound_system.sounds),
                            'uptime_seconds': round(time.time() - seq.start_time, 1) if seq.start_time else 0
                        }
                    }

                    # Record to database (async, non-blocking)
                    try:
                        import subprocess
                        db_path = os.path.expanduser('~/.claude/enhanced_memories/memory.db')
                        sql = f'''INSERT INTO soundtrack_evals
                            (target_intensity, actual_intensity, intensity_accuracy, genre_preset,
                             bpm, activity_level, workload_events_per_min)
                            VALUES ('{intensity_level}', {workload.current_intensity}, {accuracy},
                                    '{seq.genre_preset.name if seq.genre_preset else "unknown"}',
                                    {seq.bpm}, {seq.activity_level}, {workload.events_per_minute});'''
                        subprocess.Popen(['sqlite3', db_path, sql],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except:
                        pass

                    self.wfile.write(json.dumps(eval_data, indent=2).encode())

                elif self.path == '/eval/history':
                    # Get eval history from database
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    try:
                        import subprocess
                        db_path = os.path.expanduser('~/.claude/enhanced_memories/memory.db')
                        result = subprocess.run(
                            ['sqlite3', '-json', db_path,
                             'SELECT * FROM soundtrack_evals ORDER BY recorded_at DESC LIMIT 50'],
                            capture_output=True, text=True, timeout=5
                        )
                        self.wfile.write(result.stdout.encode() if result.stdout else b'[]')
                    except:
                        self.wfile.write(b'[]')

                elif self.path == '/learn/stats':
                    # Get learning statistics
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    stats = sound_system.sequencer.learner.get_stats()
                    self.wfile.write(json.dumps(stats, indent=2).encode())

                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass

        def run_server():
            # Create server with SO_REUSEADDR to avoid "Address already in use"
            class ReusableHTTPServer(HTTPServer):
                allow_reuse_address = True
            server = ReusableHTTPServer(('0.0.0.0', self.http_port), ActionHandler)
            server.serve_forever()

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        print(f"\n" + "-" * 60)
        print(f"HTTP API Server - Port {self.http_port}")
        print("-" * 60)
        print(f"  POST /action     {{\"action\": \"context_compact\"}} - Play action sound")
        print(f"  POST /sound      {{\"sound\": \"kick\"}} - Play specific sound")
        print(f"  POST /sequence   {{\"sounds\": [...], \"delay\": 0.2}} - Play sequence")
        print(f"  POST /sequencer  {{\"command\": \"start|stop|bpm|ambient|quantize\"}}")
        print(f"  GET  /sounds     - List all sounds and mappings")
        print(f"  GET  /health     - Health check with sequencer status")
        print(f"  GET  /sequencer/status - Detailed sequencer state")
        print(f"  GET  /learn/stats - Self-learning statistics")
        print(f"  POST /learn/feedback {{\"type\": \"positive|negative\"}} - Submit feedback")

    async def run(self):
        """Run the sound system."""
        self.running = True

        # Initialize all synthesizers
        self.initialize()

        # Start HTTP server
        self.start_http_server()

        # Start ambient sequencer if enabled
        if self.ambient_mode:
            self.start_sequencer()

        print("\n" + "=" * 60)
        print("AGENTIC SOUND SYSTEM - READY")
        print("=" * 60)
        print("Listening for action events...")
        print("Synthesizers: TR-808/909 Drums, TB-303 Bass, Juno/Jupiter Keys, System Utility")
        print(f"Sequencer: {'ACTIVE' if self.sequencer.running else 'OFF'} @ {self.sequencer.bpm} BPM")
        print(f"Ambient Mode: {'ON' if self.ambient_mode else 'OFF'}")
        print("")

        # Play startup sequence (direct, not through sequencer)
        await asyncio.sleep(0.5)
        self._play_sound_direct('pad')  # Warm pad intro
        await asyncio.sleep(1.5)
        self._play_sound_direct('stab')  # Bright stab announcement

        while self.running:
            await asyncio.sleep(1)


# Keep backward compatibility alias
AgenticDrumMachine = AgenticSoundSystem


async def main():
    sound_system = AgenticSoundSystem()

    # Handle graceful shutdown on SIGTERM/SIGINT
    def signal_handler(signum, frame):
        print("\n[SHUTDOWN] Signal received, cleaning up...")
        sound_system.running = False
        sound_system._executor.shutdown(wait=False)
        print("[SHUTDOWN] Sound system stopped.")
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        await sound_system.run()
    finally:
        # Cleanup executor on normal exit
        sound_system._executor.shutdown(wait=True)


if __name__ == '__main__':
    asyncio.run(main())
