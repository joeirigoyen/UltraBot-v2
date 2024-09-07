import re
import unittest

from entities.utils import rare


class TestRare(unittest.TestCase):
    def test_mPrepareString(self):
        self.assertEqual(rare.mPrepareString("I'm"), "I\\'m")
        self.assertEqual(rare.mPrepareString("He's taller"), "He\\'s taller")
        self.assertEqual(rare.mPrepareString("It's raining"), "It\\'s raining")
        self.assertEqual(rare.mPrepareString("She's beautiful"), "She\\'s beautiful")
        self.assertEqual(rare.mPrepareString("I'll be there for you"), "I\\'ll be there for you")


if __name__ == "__main__":
    unittest.main()
