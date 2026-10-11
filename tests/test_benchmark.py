"""Regression checks for coverage flags and overlap-induced word loss."""
import pathlib
import sys
import types
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from report import digest, subtract
from trial import parakeet_segments


class SyntheticStream:
    def accept_waveform(self, sample_rate, audio):
        self.start = float(audio[0])
        self.end = self.start + len(audio) / sample_rate


class SyntheticRecognizer:
    def create_stream(self):
        return SyntheticStream()

    def decode_stream(self, stream):
        points = [
            t for t in np.arange(np.ceil(stream.start * 2) / 2, stream.end, .5)
            if t != 25
        ]
        pairs = [(float(t - stream.start), '▁w' + str(int(t * 2))) for t in points]
        if stream.start <= 24.9 < stream.end:
            pairs += [(24.9 - stream.start, '▁cross'), (25.1 - stream.start, 'boundary')]
        pairs.sort()
        timestamps, tokens = map(list, zip(*pairs))
        stream.result = types.SimpleNamespace(
            text='speech', tokens=tokens, timestamps=timestamps,
            durations=[.1] * len(tokens),
        )


class BenchmarkRegressionTests(unittest.TestCase):
    def test_whole_word_crossing_core_boundary_survives_once(self):
        audio = np.arange(53 * 16000, dtype=np.float32) / 16000
        segments = parakeet_segments(SyntheticRecognizer(), audio)
        words = ' '.join(s['text'] for s in segments).split()
        self.assertEqual(words.count('crossboundary'), 1)
        self.assertNotIn('cross', words)
        self.assertNotIn('boundary', words)
        self.assertEqual(
            [word for word in words if word != 'crossboundary'],
            ['w' + str(i) for i in range(106) if i != 50],
        )
        self.assertTrue(all(0 <= s['start'] < s['end'] <= 53 for s in segments))

    def test_empty_audio_has_no_synthetic_speech(self):
        self.assertEqual(parakeet_segments(SyntheticRecognizer(), np.array([], dtype=np.float32)), [])

    def test_transcript_identity_ignores_elapsed_time(self):
        segments = [{'start': 0, 'end': 10, 'text': 'Sponsor passage'}]
        first = [{'id': 'clip', 'seconds': 2, 'segments': segments}]
        second = [{'id': 'clip', 'seconds': 3, 'segments': segments}]
        self.assertEqual(digest(first), digest(second))
        second[0]['segments'] = [{'start': 1, 'end': 10, 'text': 'Sponsor passage'}]
        self.assertNotEqual(digest(first), digest(second))

    def test_adjacent_coverage_is_not_a_missing_passage(self):
        self.assertEqual(subtract([(0, 20)], [(0, 5), (5, 20)]), [])
        self.assertEqual(subtract([(0, 20)], [(5, 15)]), [(0, 5), (15, 20)])
        self.assertEqual(subtract([(0, 20)], [(30, 40)]), [(0, 20)])


if __name__ == '__main__':
    unittest.main()
