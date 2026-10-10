"""Compatibility alias; prefer pretty_notebook._internal.publication_plan."""
from importlib import import_module
import sys

sys.modules[__name__] = import_module("pretty_notebook._internal.publication_plan")
