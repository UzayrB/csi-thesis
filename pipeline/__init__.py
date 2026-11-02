# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Wi-Fi CSI tracking and identification; the module names the saved models use still import.

import importlib
import importlib.abc
import importlib.util
import json
import os
import sys

_OLD_NAMES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "old_module_names.json")


# Gives the module already imported under its new name; the module keeps its own spec.
class _OldName(importlib.abc.Loader):

    # Sets up the object.
    def __init__(self, new: str):
        self.new = new

    # Function create module.
    def create_module(self, spec):
        self.module = importlib.import_module(self.new)
        self.spec = self.module.__spec__
        return self.module

    # Function exec module.
    def exec_module(self, module):
        module.__spec__ = self.spec


# Class Old Names.
class _OldNames(importlib.abc.MetaPathFinder):
    # Sets up the object.
    def __init__(self):
        with open(_OLD_NAMES, encoding="utf-8") as f:
            self.names = json.load(f)

    # Function find spec.
    def find_spec(self, name, path=None, target=None):
        new = self.names.get(name)
        return importlib.util.spec_from_loader(name, _OldName(new)) if new else None


if not any(isinstance(f, _OldNames) for f in sys.meta_path):
    sys.meta_path.insert(0, _OldNames())
