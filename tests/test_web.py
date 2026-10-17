import importlib.util
import io
import json
import ssl
import tempfile
import unittest
from pathlib import Path

HAS_WEB = all(importlib.util.find_spec(module) for module in ("flask", "trustme", "PIL", "bidi", "arabic_reshaper"))
if HAS_WEB:
    from parnia_web import create_app, decorate
    from PIL import Image
    from server import local_tls


@unittest.skipUnless(HAS_WEB, "Install requirements-web.txt for web tests")
class WebTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_home_health_and_static(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn(b"studio.js", home.data)
        self.assertEqual(self.client.get("/health").json["status"], "ok")
        with self.client.get("/static/studio.js") as response:
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/options").status_code, 200)
        self.assertIn("frame-ancestors 'none'", home.headers["Content-Security-Policy"])

    def test_text_preview_and_animation(self):
        response = self.client.post("/api/render", json={"text": "Parnia", "theme": "binary",
            "color": "sunset", "animation": "pixels", "border": "double"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["frames"]), 24)
        self.assertEqual(response.json["frames"][-1], response.json["art"])
        self.assertIn("╔", response.json["art"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_persian_and_hidden_message(self):
        response = self.client.post("/api/render", json={"text": "پرنیا", "theme": "dots"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(".", response.json["art"])
        response = self.client.post("/api/render", json={"text": "P", "message": "hello"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("hello", response.json["art"].replace("\n", "").replace(" ", ""))

    def test_validation_and_origin(self):
        for data in ({"scale": 1.5}, {"font": "bad"}, {"scale": True}, {"color": []},
                     {"text": "x"*201}, {"mode": "image"}, {"background": "url(x)"},
                     {"animation": "<script>"}, {"padding": 30}, {"text": ["P"]},
                     {"output": "../../secret"}):
            with self.subTest(data=data):
                response = self.client.post("/api/render", json=data)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json)
        response = self.client.post("/api/render", json={}, headers={"Origin": "https://evil.example"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.post("/api/render", json={}, headers={"Origin":"http://localhost"}).status_code, 200)

    def test_invalid_json_and_size(self):
        self.assertEqual(self.client.post("/api/render", data={"options": "{"}).status_code, 400)
        self.assertEqual(self.client.post("/api/render", json=[1]).status_code, 400)
        self.app.config["MAX_CONTENT_LENGTH"] = 100
        response = self.client.post("/api/render", data="x"*101, content_type="application/json")
        self.assertEqual(response.status_code, 413)

    def test_image_upload_adjustments(self):
        image = Image.new("RGB", (40, 20), "white")
        for x in range(20):
            for y in range(20):
                image.putpixel((x,y), (0,0,0))
        stream = io.BytesIO(); image.save(stream, format="PNG")
        def upload(options):
            return self.client.post("/api/render", data={"options":json.dumps({"mode":"image", "width":40, **options}),
                "image":(io.BytesIO(stream.getvalue()), "photo.png")})
        original = upload({}); inverted = upload({"invert": True})
        mirrored = upload({"mirror": True}); edges = upload({"edges": True})
        self.assertEqual(original.status_code, 200)
        self.assertNotEqual(original.json["art"], inverted.json["art"])
        self.assertNotEqual(original.json["art"], mirrored.json["art"])
        self.assertNotEqual(original.json["art"], edges.json["art"])
        self.assertEqual(upload({"brightness": 10}).status_code, 400)
        self.assertEqual(upload({"invert": "yes"}).status_code, 400)
        bad = self.client.post("/api/render", data={"options":json.dumps({"mode":"image"}),
            "image":(io.BytesIO(b"not an image"), "bad.png")})
        self.assertEqual(bad.status_code, 400)

    def test_photo_larger_than_multipart_buffer(self):
        import random
        image = Image.frombytes("RGB", (256,256), random.Random(42).randbytes(256*256*3))
        stream = io.BytesIO(); image.save(stream, format="PNG")
        self.assertGreater(len(stream.getvalue()), 64*1024)
        response = self.client.post("/api/render", data={"options":json.dumps({"mode":"image"}),
            "image":(io.BytesIO(stream.getvalue()), "photo.png")})
        self.assertEqual(response.status_code, 200)

    def test_download_formats_and_colors(self):
        for kind, mime in (("txt", "text/plain"), ("png", "image/png"), ("gif", "image/gif")):
            response = self.client.post("/api/render", json={"text":"P", "output":kind,
                "background":"#faf7f0", "foreground":"#342e3d"})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.content_type.startswith(mime))
            self.assertIn("attachment", response.headers["Content-Disposition"])
            if kind == "txt":
                self.assertIn(b"####", response.data)
            else:
                with Image.open(io.BytesIO(response.data)) as image:
                    self.assertEqual(image.convert("RGB").getpixel((0,0)), (250,247,240))
                    if kind == "gif":
                        self.assertGreater(image.n_frames, 1)

    def test_alignment_preserves_letter_shape(self):
        self.assertEqual(decorate("####\n#\n\n##\n#", alignment="center"), "####\n#\n\n ##\n #")

    def test_local_certificate_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            context = local_tls(folder)
            self.assertIsInstance(context, ssl.SSLContext)
            cert = (Path(folder)/"server.pem").read_bytes()
            local_tls(folder)
            self.assertEqual(cert, (Path(folder)/"server.pem").read_bytes())


if __name__ == "__main__":
    unittest.main()
