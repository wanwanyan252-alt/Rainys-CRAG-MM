import unittest

from tools.prepare_hf_signed_urls import is_official_download_host


class PrepareHfSignedUrlsTests(unittest.TestCase):
    def test_allows_official_download_hosts(self):
        self.assertTrue(is_official_download_host("us.aws.cdn.hf.co"))
        self.assertTrue(is_official_download_host("cas-bridge.xethub.hf.co"))

    def test_rejects_unrelated_hosts(self):
        self.assertFalse(is_official_download_host("huggingface.example.com"))
        self.assertFalse(is_official_download_host(None))


if __name__ == "__main__":
    unittest.main()
