"""
Caveman compression utilities for agentic system
Integrates semantic compression with TOON format
"""

import re
from pathlib import Path
import sys

# Add caveman-compression to path
CAVEMAN_PATH = Path(__file__).parent.parent / 'caveman-compression'
sys.path.insert(0, str(CAVEMAN_PATH))

from simple_caveman_compress import compress_text, calculate_compression_ratio


class CavemanCompressor:
    """Intelligent compression for natural language content"""

    def __init__(self, min_length=100, target_reduction=0.10):
        """
        Args:
            min_length: Minimum text length to consider compression (default: 100)
            target_reduction: Target compression ratio (default: 0.10 = 10% reduction)
        """
        self.min_length = min_length
        self.target_reduction = target_reduction
        self.stats = {
            'total_compressions': 0,
            'total_skipped': 0,
            'total_tokens_saved': 0,
            'total_original_tokens': 0
        }

    def should_compress(self, content, content_type):
        """Decide if content should be compressed"""

        # Handle empty or very short content
        if not content or len(content) < self.min_length:
            return False

        # Check content type
        no_compress_types = ['code', 'command', 'json', 'yaml', 'config', 'toon']
        if content_type in no_compress_types:
            return False

        # Check if already compressed (low redundancy)
        if self._is_already_compressed(content):
            return False

        return True

    def _is_already_compressed(self, content):
        """Detect if content is already compressed/concise"""

        words = content.split()
        if len(words) < 10:
            return True  # Too short to analyze

        # High ratio of technical terms (capitalized words)
        caps_count = sum(1 for w in words if w and w[0].isupper())
        caps_ratio = caps_count / len(words)
        if caps_ratio > 0.3:
            return True

        # High punctuation density (code-like)
        punct_count = len(re.findall(r'[{}()\[\];,.]', content))
        punct_ratio = punct_count / len(content)
        if punct_ratio > 0.1:
            return True

        # Short average word length (already compressed)
        avg_word_len = sum(len(w) for w in words) / len(words)
        if avg_word_len < 4.5:
            return True

        return False

    def compress(self, content, content_type='text', preserve_original=True):
        """
        Compress content if beneficial

        Args:
            content: Text to compress
            content_type: Type of content ('text', 'observation', 'summary', etc.)
            preserve_original: Include original text in result

        Returns:
            dict with 'compressed', 'original' (optional), and 'stats'
        """

        if not self.should_compress(content, content_type):
            self.stats['total_skipped'] += 1
            return {
                'compressed': content,
                'original': content if preserve_original else None,
                'stats': {
                    'compressed': False,
                    'reason': 'not beneficial',
                    'content_type': content_type
                }
            }

        compressed = compress_text(content)
        stats = calculate_compression_ratio(content, compressed)

        # If compression isn't significant, return original
        reduction_threshold = self.target_reduction * 100
        if stats['token_reduction_pct'] < reduction_threshold:
            self.stats['total_skipped'] += 1
            return {
                'compressed': content,
                'original': content if preserve_original else None,
                'stats': {
                    'compressed': False,
                    'reason': f'insufficient reduction ({stats["token_reduction_pct"]:.1f}% < {reduction_threshold}%)',
                    'content_type': content_type
                }
            }

        # Update global stats
        self.stats['total_compressions'] += 1
        self.stats['total_tokens_saved'] += (stats['original_tokens'] - stats['compressed_tokens'])
        self.stats['total_original_tokens'] += stats['original_tokens']

        return {
            'compressed': compressed,
            'original': content if preserve_original else None,
            'stats': {
                'compressed': True,
                'token_reduction_pct': stats['token_reduction_pct'],
                'original_tokens': stats['original_tokens'],
                'compressed_tokens': stats['compressed_tokens'],
                'content_type': content_type
            }
        }

    def compress_observations(self, observations, content_type='observation'):
        """
        Compress array of observation strings

        Args:
            observations: List of observation strings
            content_type: Type of observations

        Returns:
            (compressed_observations, compression_stats)
        """
        results = []
        compression_results = []
        total_original = 0
        total_compressed = 0
        num_compressed = 0

        for obs in observations:
            result = self.compress(obs, content_type=content_type, preserve_original=False)
            results.append(result['compressed'])
            compression_results.append(result)

            if result['stats'].get('compressed'):
                num_compressed += 1
                total_original += result['stats']['original_tokens']
                total_compressed += result['stats']['compressed_tokens']

        compression_stats = {
            'total_observations': len(observations),
            'observations_compressed': num_compressed,
            'observations_skipped': len(observations) - num_compressed,
            'total_original_tokens': total_original,
            'total_compressed_tokens': total_compressed,
            'token_reduction_pct': ((total_original - total_compressed) / total_original * 100) if total_original > 0 else 0
        }

        return results, compression_stats

    def get_stats(self):
        """Get global compression statistics"""
        if self.stats['total_original_tokens'] > 0:
            overall_reduction = (self.stats['total_tokens_saved'] / self.stats['total_original_tokens']) * 100
        else:
            overall_reduction = 0

        return {
            **self.stats,
            'overall_reduction_pct': overall_reduction
        }

    def reset_stats(self):
        """Reset statistics counters"""
        self.stats = {
            'total_compressions': 0,
            'total_skipped': 0,
            'total_tokens_saved': 0,
            'total_original_tokens': 0
        }


# Singleton instance
_compressor = CavemanCompressor()


def compress_for_memory(content, content_type='text', preserve_original=True):
    """
    Convenience function for memory compression

    Args:
        content: Text to compress
        content_type: Type of content
        preserve_original: Include original in result

    Returns:
        dict with compression result
    """
    return _compressor.compress(content, content_type, preserve_original)


def compress_observations(observations, content_type='observation'):
    """
    Convenience function for observation array compression

    Args:
        observations: List of observation strings
        content_type: Type of observations

    Returns:
        (compressed_observations, compression_stats)
    """
    return _compressor.compress_observations(observations, content_type)


def get_compression_stats():
    """Get global compression statistics"""
    return _compressor.get_stats()


def reset_compression_stats():
    """Reset global compression statistics"""
    _compressor.reset_stats()


def test_compression():
    """Test compression on sample content"""
    print("Testing Caveman Compression Utilities\n" + "="*60)

    test_cases = [
        {
            'name': 'Episodic Memory (Long)',
            'content': 'The distributed execution system was tested with seven different test cases to verify functionality across the cluster. All tests passed successfully, demonstrating that tasks can be routed to the appropriate nodes based on their requirements. The macpro51 builder node successfully executed Linux-specific commands, while the mac-studio orchestrator coordinated the overall workflow. We observed approximately 0.5 seconds of routing overhead and 1-2 seconds of SSH connection time, which is acceptable for tasks with execution times greater than 5 seconds. The parallel execution test showed linear scaling up to the number of available nodes. One interesting finding was that the task queue management handled concurrent submissions without any race conditions.',
            'type': 'observation'
        },
        {
            'name': 'Research Summary',
            'content': 'The paper introduces a novel approach to recursive self-improvement in AI systems. The authors propose a framework where agents can analyze their own performance metrics, identify weaknesses, and generate targeted improvements. The key innovation is the use of meta-learning to guide the self-improvement process, which allows the system to learn not just specific tasks but also how to improve its own learning mechanisms. The experimental results demonstrate significant performance gains over baseline approaches, with improvements ranging from 20% to 45% across different benchmarks.',
            'type': 'summary'
        },
        {
            'name': 'Agent Communication',
            'content': 'I have completed the analysis of the codebase structure and identified several opportunities for optimization. The memory management system could benefit from implementing compression for long-term storage, which would reduce database size by approximately 30-40%. Additionally, the distributed task router could be enhanced with predictive load balancing to better utilize cluster resources. I recommend prioritizing the memory compression implementation first, as it has the highest impact-to-effort ratio.',
            'type': 'message'
        }
    ]

    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"Type: {test['type']}")
        print(f"Original ({len(test['content'])} chars):")
        print(f"  {test['content'][:100]}...")

        result = compress_for_memory(test['content'], test['type'])

        if result['stats']['compressed']:
            print(f"Compressed ({len(result['compressed'])} chars):")
            print(f"  {result['compressed'][:100]}...")
            print(f"Stats: {result['stats']['token_reduction_pct']:.1f}% token reduction")
        else:
            print(f"Skipped: {result['stats']['reason']}")

    print("\n" + "="*60)
    print("Global Stats:")
    stats = get_compression_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == '__main__':
    test_compression()
