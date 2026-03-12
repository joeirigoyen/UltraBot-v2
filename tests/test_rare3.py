import unittest

from entities.utils import rare
from rapidfuzz import fuzz


class TestMListMostSimilarPartial(unittest.TestCase):

    def test_most_similar_basic(self):
        # Results sorted by similarity: exact match first, then partials
        actual_output = rare.mListMostSimilarPartial('lion', ['lion', 'iron', 'lions', 'stick', 'fork'], 3)
        self.assertIn('lion', actual_output)
        self.assertIn('lions', actual_output)
        self.assertEqual(len(actual_output), 3)

    def test_most_similar_empty_str(self):
        # Empty string should match nothing above the threshold
        actual_output = rare.mListMostSimilarPartial('', ['lion', 'iron', 'lions', 'stick', 'fork'], 1)
        self.assertEqual(actual_output, [])

    def test_most_similar_non_alpha_char(self):
        actual_output = rare.mListMostSimilarPartial('#12', ['#12', 'iron', '@12', 'stick', 'fork'], 2)
        self.assertIn('#12', actual_output)
        self.assertEqual(len(actual_output), 2)

    def test_most_similar_no_similar_words(self):
        # 'zebra' has no fuzzy match in the list
        actual_output = rare.mListMostSimilarPartial('zebra', ['lion', 'iron', 'lions', 'stick', 'fork'], 3)
        self.assertEqual(actual_output, [])

    def test_most_similar_max_limit(self):
        expected_output_len = 10
        actual_output_len = len(rare.mListMostSimilarPartial('monkey', ['monkey'] * 20, 10))
        self.assertEqual(expected_output_len, actual_output_len)

    def test_case_sensitivity(self):
        # All case variants of 'lion' should match regardless of case
        actual_output = rare.mListMostSimilarPartial('LION', ['lion', 'LION', 'Lions', 'stick', 'fork'], 3)
        self.assertEqual(len(actual_output), 3)
        for item in actual_output:
            self.assertIn(item.lower(), ['lion', 'lions'])

    def test_results_sorted_by_relevance(self):
        # Exact match should come first
        actual_output = rare.mListMostSimilarPartial('sprint', ['Adrenaline', 'Sprint Burst', 'Spine Chill'], 3)
        self.assertEqual(actual_output[0], 'Sprint Burst')


if __name__ == '__main__':
    unittest.main()
