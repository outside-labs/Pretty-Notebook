"""Compatibility alias; prefer pretty_notebook.helpers._datetime."""
from importlib import import_module
import sys

sys.modules[__name__] = import_module("pretty_notebook.helpers._datetime")
