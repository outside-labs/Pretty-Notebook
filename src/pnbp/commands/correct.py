"""Compatibility alias; prefer pretty_notebook.commands.correct."""
from importlib import import_module
import sys

sys.modules[__name__] = import_module("pretty_notebook.commands.correct")
