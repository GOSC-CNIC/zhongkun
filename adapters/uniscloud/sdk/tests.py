from unittest import TestCase

from .model import build_url


class BuildUrlTest(TestCase):
    def test_build_url(self):
        url = build_url('a', 'b', 'c')
        self.assertEqual('a/b/c', url)

        url = build_url('/a', '/b', 'c/')
        self.assertEqual('a/b/c', url)

        url = build_url('/a/', 'b', '/c')
        self.assertEqual('a/b/c', url)

        url = build_url('/a/', '/b/', '/c/')
        self.assertEqual('a/b/c', url)

        url = build_url('/a/', 'b/')
        self.assertEqual('a/b', url)

        url = build_url('/a/')
        self.assertEqual('a', url)

        url = build_url()
        self.assertEqual('', url)
