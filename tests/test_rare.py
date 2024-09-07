import unittest

from entities.utils import rare


class TestMSuperCleanString(unittest.TestCase):
    def test_mSuperCleanString(self):
        self.assertEqual(rare.mSuperCleanString('Boon: Circle Of Healing'), 'booncircleofhealing')
        self.assertEqual(rare.mSuperCleanString('Wake Up!'), 'wakeup')
        self.assertEqual(rare.mSuperCleanString('Dèjá Vu'), 'dejavu')
        self.assertEqual(rare.mSuperCleanString('We\'re Gonna Live Forever'), 'weregonnaliveforever')
        self.assertEqual(rare.mSuperCleanString('12345'), '')


if __name__ == "__main__":
    unittest.main()
