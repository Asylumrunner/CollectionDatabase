import os
import traceback

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def exception_stack(e):
    # Where an exception travelled, from the frame that caught it to the line that raised it, as
    # "File.py:function:line" hops joined by " > ". Library frames are dropped, except the one that
    # raised. Only code locations are included, never the message or any values, so the result is
    # safe to log even when the message could contain user identifiers
    frames = traceback.extract_tb(e.__traceback__)
    if not frames:
        return "unknown"
    hops = [f for f in frames if f.filename.startswith(_PROJECT_ROOT + os.sep) and "site-packages" not in f.filename]
    if not hops or hops[-1] is not frames[-1]:
        hops.append(frames[-1])
    return " > ".join(f"{os.path.basename(f.filename)}:{f.name}:{f.lineno}" for f in hops)
