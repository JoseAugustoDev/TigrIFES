import json
import importlib.util
import shutil
import subprocess
import sys
import threading
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import urlopen

import pytest

from tigrifes.build_site import build_site, normalize_base_path, static_url
from tigrifes.machine import simulate

PROJECT = Path(__file__).resolve().parents[1]
SEEDS = (0, 1, 10, 42, 2026, 123456, 2**31, 2**32 - 1)


@pytest.fixture(scope="module")
def javascript_rounds():
    node = shutil.which("node")
    assert node, "Instale Node.js 22+ para conferir a compatibilidade do site estático."
    script = """
      const fs = require('node:fs');
      const machine = require('./tigrifes/static/machine.js');
      const seeds = JSON.parse(fs.readFileSync(0, 'utf8'));
      console.log(JSON.stringify(seeds.map(seed => {
        const rng = new machine.PythonRandom(seed);
        return Array.from({length: 10000}, () => machine.spin(rng).stops);
      })));
    """
    result = subprocess.run([node, "-e", script], input=json.dumps(SEEDS), cwd=PROJECT,
                            capture_output=True, text=True, check=True)
    return dict(zip(SEEDS, json.loads(result.stdout)))


@pytest.mark.parametrize("seed", SEEDS)
def test_javascript_reproduces_ten_thousand_python_rounds(seed, javascript_rounds):
    assert javascript_rounds[seed] == [list(r.stops) for r in simulate(10_000, seed)]


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        for key in ("href", "src"):
            if key in values:
                self.links.append(values[key])
        if tag == "script":
            self.scripts.append(values.get("src"))


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    return build_site(tmp_path_factory.mktemp("static-site"))


def test_all_pages_links_assets_and_anchors_resolve_on_static_host(site):
    for path in site.glob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert "{{" not in text and "{%" not in text
        assert "/api/" not in text
        page = PageParser()
        page.feed(text)
        assert len(page.ids) == len(set(page.ids)), f"IDs duplicados em {path.name}"
        for link in page.links:
            parsed = urlsplit(link)
            assert not parsed.scheme, f"O site deve ser autônomo: {link}"
            if path.name != "404.html":
                assert not parsed.path.startswith("/"), f"Link incompatível com /TigrIFES/: {link}"
            if parsed.path.startswith("/"):
                destination = site / unquote(parsed.path).lstrip("/")
            elif parsed.path:
                destination = path.parent / unquote(parsed.path)
            else:
                destination = path
            assert destination.is_file(), (path.name, link)
            if parsed.fragment:
                target = PageParser()
                target.feed(destination.read_text(encoding="utf-8"))
                assert parsed.fragment in target.ids, (path.name, link)
        assert all(src for src in page.scripts), "O site não usa scripts inline."
    assert (site / "resultados" / "tigrifes-experimentos.zip").read_bytes().startswith(b"PK")
    assert (site / ".nojekyll").exists()
    assert not list(site.rglob("*.py"))
    assert not list(site.rglob("*.sqlite3"))


def test_static_page_has_only_browser_scripts_and_no_network_api_calls(site):
    page = PageParser()
    page.feed((site / "index.html").read_text(encoding="utf-8"))
    assert page.scripts == ["assets/machine.js", "assets/session-store.js", "assets/app-static.js"]
    source = (site / "assets" / "app-static.js").read_text(encoding="utf-8")
    assert "fetch(" not in source
    assert "XMLHttpRequest" not in source
    info = json.loads((site / "build-info.json").read_text(encoding="utf-8"))
    assert info["format"] == "static"
    assert info["experiments"]["e4_e5_reuse_e1"] is True


def test_unknown_static_endpoint_fails_instead_of_generating_broken_links():
    with pytest.raises(ValueError):
        static_url("unmapped")


@pytest.mark.parametrize("value,expected", [("", "/"), ("/", "/"), ("/TigrIFES", "/TigrIFES/"), ("/TigrIFES/", "/TigrIFES/")])
def test_base_path_accepts_root_and_repository(value, expected):
    assert normalize_base_path(value) == expected


@pytest.mark.parametrize("value", ["TigrIFES", "https://example.tech/", "//example.tech/", "/../", "/%2e%2e/", "/x//y", "/x?query", "/x#hash", "/x\\y", "/x%2fy"])
def test_base_path_rejects_urls_and_directory_traversal(value):
    with pytest.raises(ValueError):
        normalize_base_path(value)


def test_model_can_be_imported_with_only_the_standard_library():
    script = "from tigrifes.machine import simulate; assert len(simulate(10, 2026)) == 10"
    result = subprocess.run([sys.executable, "-S", "-c", script], cwd=PROJECT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_removed_server_dependencies_are_absent():
    # O teste só verifica o projeto: ferramentas do usuário podem ter outros pacotes.
    requirements = (PROJECT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    assert {line.split("==")[0] for line in requirements if line} == {"Jinja2", "matplotlib"}
    assert importlib.util.find_spec("tigrifes.storage") is None


@pytest.mark.parametrize("project_path", [False, True])
def test_static_server_delivers_pages_assets_and_downloads_at_both_base_paths(site, project_path):
    directory = site.parent if project_path else site
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    prefix = f"/{site.name}/" if project_path else "/"
    base = f"http://127.0.0.1:{server.server_port}{prefix}"
    try:
        for filename in ("index.html", "experimentos.html"):
            with urlopen(base + filename) as response:
                assert response.status == 200
                assert response.headers.get_content_type() == "text/html"
                page = PageParser()
                page.feed(response.read().decode("utf-8"))
            for link in set(page.links):
                if link.startswith("#"):
                    continue
                with urlopen(urljoin(base + filename, link)) as response:
                    assert response.status == 200
                    if link.endswith(".zip"):
                        assert response.read(2) == b"PK"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


@pytest.mark.parametrize("base_path", ["/", "/TigrIFES/"])
def test_nested_not_found_page_resolves_every_link_at_public_base(tmp_path, base_path):
    public_root = tmp_path / "public"
    site_root = public_root / base_path.strip("/") if base_path != "/" else public_root
    build_site(site_root, base_path=base_path)

    class PagesHandler(SimpleHTTPRequestHandler):
        def send_error(self, code, message=None, explain=None):
            if code != 404:
                return super().send_error(code, message, explain)
            body = (site_root / "404.html").read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(PagesHandler, directory=str(public_root)))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    try:
        from urllib.error import HTTPError
        for suffix in ("rota/inexistente", "rota/inexistente/"):
            requested = origin + base_path + suffix
            with pytest.raises(HTTPError) as error:
                urlopen(requested)
            assert error.value.code == 404
            with error.value as response:
                page = PageParser()
                page.feed(response.read().decode("utf-8"))
            for link in page.links:
                if link.startswith("#"):
                    continue
                assert urlsplit(link).path.startswith(base_path)
                with urlopen(urljoin(requested, link)) as response:
                    assert response.status == 200, link
        info = json.loads((site_root / "build-info.json").read_text(encoding="utf-8"))
        assert info["base_path"] == base_path
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
