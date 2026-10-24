"""Gera o site estático autônomo: python -m tigrifes.build_site."""

import argparse
import io
import json
import shutil
import zipfile
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from .experiments import export_files, run_experiments
from .machine import PAYOUTS

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
SYMBOL_DISPLAY = {
    "A": {"emoji": "🍒", "name": "cereja"},
    "B": {"emoji": "🍋", "name": "limão"},
    "C": {"emoji": "🍇", "name": "uva"},
    "D": {"emoji": "🍉", "name": "melancia"},
    "E": {"emoji": "🐯", "name": "tigre"},
}


def static_url(endpoint, **values):
    """Links relativos funcionam no domínio próprio e em /TigrIFES/."""
    if endpoint == "index":
        return "index.html"
    if endpoint == "experiments":
        return "experimentos.html"
    if endpoint == "static":
        return f"assets/{values['filename']}"
    if endpoint == "chart":
        return f"resultados/graficos/{values['name']}.png"
    if endpoint == "download":
        return "resultados/tigrifes-experimentos.zip"
    if endpoint == "license":
        return "licenses/MT19937.txt"
    raise ValueError(f"Não existe destino estático para {endpoint!r}.")


def normalize_base_path(value):
    """Normaliza o caminho público recebido do GitHub Pages, sem aceitar URLs."""
    if value in ("", "/"):
        return "/"
    parsed = urlsplit(value)
    if not value.startswith("/") or parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or "\\" in value:
        raise ValueError("O caminho base deve ser '/' ou um caminho como '/TigrIFES/'.")
    segments = [unquote(segment) for segment in value.strip("/").split("/")]
    if any(segment in ("", ".", "..") or "/" in segment or "\\" in segment for segment in segments):
        raise ValueError("O caminho base não pode conter segmentos vazios ou navegação entre diretórios.")
    return "/" + "/".join(quote(segment, safe="-._~") for segment in segments) + "/"


def number(value, digits=2):
    if value is None:
        return "Não estimável"
    return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def build_site(output: Path, base_path="/"):
    base_path = normalize_base_path(base_path)
    output = output.resolve()
    # Não remove diretórios: escreve apenas os arquivos próprios da compilação.
    output.mkdir(parents=True, exist_ok=True)
    env = Environment(loader=FileSystemLoader(ROOT / "templates"),
                      autoescape=select_autoescape(["html"]), undefined=StrictUndefined)
    env.filters["number"] = number
    env.globals.update(site_url=static_url, symbol_display=SYMBOL_DISPLAY)
    game = {"rounds": 0, "balance": 100, "seed": 2026, "wins": 0, "last": None}
    pages = {
        "index.html": ("index.html", {"game": game, "payouts": PAYOUTS, "active": "simulator"}),
        "experimentos.html": ("experiments.html", {"data": run_experiments(), "active": "experiments"}),
        "404.html": ("error.html", {"message": "Esta página não foi encontrada.", "active": "",
                                   "site_url": lambda endpoint, **values: base_path + static_url(endpoint, **values)}),
    }
    for destination, (template, context) in pages.items():
        (output / destination).write_text(env.get_template(template).render(**context), encoding="utf-8")
    assets = output / "assets"
    assets.mkdir(exist_ok=True)
    for name in ("style.css", "favicon.svg", "machine.js", "session-store.js", "app-static.js"):
        shutil.copyfile(ROOT / "static" / name, assets / name)
    license_dir = output / "licenses"
    license_dir.mkdir(exist_ok=True)
    shutil.copyfile(PROJECT / "LICENSES" / "MT19937.txt", license_dir / "MT19937.txt")
    files = export_files()
    for name, contents in files.items():
        destination = output / "resultados" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(contents)
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, contents in files.items():
            archive.writestr(name, contents)
    (output / "resultados" / "tigrifes-experimentos.zip").write_bytes(archive_bytes.getvalue())
    (output / ".nojekyll").write_text("", encoding="utf-8")
    manifest = {"format": "static", "pages": list(pages), "base_path": base_path,
                "browser_generator": "MT19937, integer seed uint32, CPython 3.13 randrange(5) compatible",
                "experiments": run_experiments()["metadata"],
                "runtime": "HTML, CSS e JavaScript; nenhum servidor de aplicação"}
    (output / "build-info.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def main():
    parser = argparse.ArgumentParser(description="Gera o TigrIFES estático para GitHub Pages.")
    parser.add_argument("--output", type=Path, default=Path("site"))
    parser.add_argument("--base-path", default="/", help="Caminho público do site: '/' ou '/TigrIFES/' (usado na página 404).")
    args = parser.parse_args()
    try:
        result = build_site(args.output, base_path=args.base_path)
    except ValueError as error:
        parser.error(str(error))
    print(f"Site estático gerado em {result}")
    print("Abra index.html ou execute: python -m http.server 8000 --directory site --bind 127.0.0.1")


if __name__ == "__main__":
    main()
