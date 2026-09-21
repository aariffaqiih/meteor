"""Asset exposure and CSP regressions for Meteor's visual theme."""
import unittest
from html.parser import HTMLParser

import app as meteor


class Elements(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.tags = []
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class ThemeTests(unittest.TestCase):
    def setUp(self):
        self.client = meteor.app.test_client()

    def test_brand_images_are_served_as_png_without_exposing_other_files(self):
        for name in ("banner.png", "profile_picture.png"):
            with self.client.get("/images/" + name) as response:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, "image/png")
                self.assertTrue(response.data.startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        for path in ("/images/.env", "/images/app.py", "/images/unknown.png", "/images/../.env", "/.env"):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_theme_requires_fresh_nonce_and_uses_only_local_images(self):
        response = self.client.get("/")
        policy = response.headers["Content-Security-Policy"]
        elements = Elements(response.get_data(as_text=True)).tags
        nonce = policy.split("script-src 'nonce-")[1].split("'")[0]
        self.assertIn(f"style-src 'nonce-{nonce}'", policy)
        self.assertIn("img-src 'self'", policy)
        self.assertNotIn("unsafe-inline", policy)
        self.assertEqual([attrs["nonce"] for tag, attrs in elements if tag == "style"], [nonce])
        self.assertEqual({attrs["src"] for tag, attrs in elements if tag == "img"},
                         {"/images/banner.png", "/images/profile_picture.png"})
        self.assertNotEqual(policy, self.client.get("/").headers["Content-Security-Policy"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")


if __name__ == "__main__":
    unittest.main()
