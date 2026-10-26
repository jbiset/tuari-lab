from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from simulate import CampusClient, CampusHTML, InternalRedirect


def response(html, url="http://proxy/my/"):
    obj = Mock()
    obj.__enter__ = Mock(return_value=obj)
    obj.__exit__ = Mock(return_value=False)
    obj.read.return_value = html.encode()
    obj.url = url
    return obj


class SimulatorTests(unittest.TestCase):
    def test_html_token_and_links(self):
        parser = CampusHTML()
        parser.feed('<input value="abc&amp;def" name="logintoken"><a href="/course/view.php?id=2&amp;x=1">Curso</a>')
        self.assertEqual(parser.token, "abc&def")
        self.assertIn("/course/view.php?id=2&x=1", parser.links)

    def test_login_requires_session_and_posts_token(self):
        client = CampusClient("http://proxy", "http://localhost:8080")
        client.opener = Mock()
        client.opener.open.side_effect = [
            response('<input name="logintoken" value="csrf-token">', "http://proxy/login/index.php"),
            response("ok"), response('<a href="http://localhost:8080/login/logout.php?sesskey=x">Salir</a>'),
        ]
        client.login("estudiante001", "fictional")
        post = client.opener.open.call_args_list[1].args[1]
        self.assertIn(b"logintoken=csrf-token", post)

    def test_http_200_login_form_is_not_success(self):
        client = CampusClient("http://proxy", "http://localhost:8080")
        client.opener = Mock()
        client.opener.open.side_effect = [
            response('<input name="logintoken" value="token">'), response("Login failed"),
            response('<input name="password">', "http://proxy/login/index.php"),
        ]
        with self.assertRaisesRegex(RuntimeError, "autenticada"):
            client.login("estudiante001", "wrong")

    def test_redirect_stays_internal_and_external_requests_are_rejected(self):
        handler = InternalRedirect("http://proxy", "http://localhost:8080")
        req = urllib.request.Request("http://proxy/login/index.php")
        redirect = handler.redirect_request(req, None, 303, "", {}, "http://localhost:8080/my/")
        self.assertEqual(redirect.full_url, "http://proxy/my/")
        with self.assertRaises(ValueError):
            handler.redirect_request(req, None, 302, "", {}, "https://example.org/")
        client = CampusClient("http://proxy", "http://localhost:8080")
        with self.assertRaises(ValueError):
            client.request("http://example.org/")
