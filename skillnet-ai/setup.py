"""Require the prebuilt website when producing a distributable Python package."""

from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist


def require_website():
    assets = Path(__file__).parent / "src" / "skillnet_ai" / "web" / "static"
    if not (assets / "index.html").is_file():
        raise RuntimeError(
            "Web assets are missing. Run npm ci and npm run build in "
            "src/skillnet_ai/web/ui before building the Python package."
        )


class BuildWithWebsite(build_py):
    def run(self):
        if not self.editable_mode:
            require_website()
        super().run()


class SourceWithWebsite(sdist):
    def run(self):
        require_website()
        super().run()


setup(cmdclass={"build_py": BuildWithWebsite, "sdist": SourceWithWebsite})
