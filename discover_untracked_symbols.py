from tools.discover_untracked_symbols import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("tools.discover_untracked_symbols", run_name="__main__")

