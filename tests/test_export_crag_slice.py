import unittest

from tools.export_crag_slice import download_official_image


class ExportCragSliceTests(unittest.TestCase):
    def test_rejects_non_official_image_host(self):
        with self.assertRaises(SystemExit):
            download_official_image("https://example.com/image.jpg")

    def test_rejects_non_https_official_url(self):
        with self.assertRaises(SystemExit):
            download_official_image("http://upload.wikimedia.org/image.jpg")


if __name__ == "__main__":
    unittest.main()
