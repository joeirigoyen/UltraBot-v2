import unittest

from entities.utils import rare
from rapidfuzz import fuzz


class TestMListMostSimilarPartial(unittest.TestCase):

    def test_most_similar_basic(self):
        expected_output = ['lion', 'iron', 'lions']
        actual_output = rare.mListMostSimilarPartial('lion', ['lion', 'iron', 'lions', 'stick', 'fork'], 3)
        self.assertEqual(expected_output, actual_output)

    def test_most_similar_empty_str(self):
        expected_output = ['']
        actual_output = rare.mListMostSimilarPartial('', ['lion', 'iron', 'lions', 'stick', 'fork'], 1)
        self.assertEqual(expected_output, actual_output)

    def test_most_similar_non_alpha_char(self):
        expected_output = ['#12', '@12']
        actual_output = rare.mListMostSimilarPartial('#12', ['#12', 'iron', '@12', 'stick', 'fork'], 2)
        self.assertEqual(expected_output, actual_output)

    def test_most_similar_no_similar_words(self):
        expected_output = ['zebra']
        actual_output = rare.mListMostSimilarPartial('zebra', ['lion', 'iron', 'lions', 'stick', 'fork'], 3)
        self.assertEqual(expected_output, actual_output)

    def test_most_similar_max_limit(self):
        expected_output_len = 10
        actual_output_len = len(rare.mListMostSimilarPartial('monkey', ['monkey'] * 20, 10))
        self.assertEqual(expected_output_len, actual_output_len)

    def test_case_sensitivity(self):
        expected_output = ['LION', 'lion', 'Lions']
        actual_output = rare.mListMostSimilarPartial('LION', ['lion', 'LION', 'Lions', 'stick', 'fork'], 3)
        self.assertEqual(expected_output, actual_output)


if __name__ == '__main__':
    unittest.main()
