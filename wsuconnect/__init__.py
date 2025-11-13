# Optional but helps Sphinx resolve submodules
from importlib import import_module

__all__ = ["support_tools", "classes", "data"]

for _mod in __all__:
    try:
        import_module(f"wsuconnect.{_mod}")
    except ModuleNotFoundError:
        pass