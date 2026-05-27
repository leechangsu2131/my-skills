import importlib.resources as resources
import platform

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

from . import bond, stock

os = platform.system()

if os == "Darwin":
    plt.rc("font", family="AppleGothic")
else:
    with resources.path("pykrx", "NanumBarunGothic.ttf") as font_path:
        fe = fm.FontEntry(fname=str(font_path), name="NanumBarunGothic")
        fm.fontManager.ttflist.insert(0, fe)
        plt.rc("font", family=fe.name)

plt.rcParams["axes.unicode_minus"] = False

__all__ = ["bond", "stock"]

# Version is automatically managed by setuptools_scm from git tags
try:
    from importlib.metadata import version

    __version__ = version("pykrx")
except Exception:
    # Fallback for development/editable installs without metadata
    __version__ = "0.0.0+unknown"
