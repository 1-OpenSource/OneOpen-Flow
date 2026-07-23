# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# Allow autodoc of the backend package when building from repo root / docs.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

project = "OneOpen Flow"
author = "OneOpenSource"
copyright = f"{date.today().year}, OneOpenSource"
release = "0.2.0"
version = "0.2"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinxcontrib.mermaid",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "requirements-docs.txt"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

master_doc = "index"
language = "en"

# Classic Read the Docs appearance
html_theme = "sphinx_rtd_theme"
html_title = "OneOpen Flow Documentation"
html_short_title = "OneOpen Flow"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_logo = "logo.svg"
html_favicon = "logo.svg"
html_show_sourcelink = True
html_show_sphinx = False
html_copy_source = False

html_theme_options = {
    "logo_only": False,
    "prev_next_buttons_location": "bottom",
    "style_external_links": True,
    "style_nav_header_background": "#2980B9",
    "collapse_navigation": False,
    "sticky_navigation": True,
    "navigation_depth": 3,
    "includehidden": True,
    "titles_only": False,
}

html_context = {
    "display_github": True,
    "github_user": "1-OpenSource",
    "github_repo": "OneOpen-Flow",
    "github_version": "main",
    "conf_py_path": "/docs/",
}

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "replacements",
    "smartquotes",
    "tasklist",
]

myst_heading_anchors = 3
todo_include_todos = True

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}
autodoc_typehints = "description"
napoleon_google_docstring = True
napoleon_numpy_docstring = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "fastapi": ("https://fastapi.tiangolo.com/", None),
}

copybutton_prompt_text = r">>> |\.\.\. |\$ |PS> "
copybutton_prompt_is_regexp = True
