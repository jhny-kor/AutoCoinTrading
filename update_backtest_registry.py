from tools.update_backtest_registry import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("tools.update_backtest_registry", run_name="__main__")
