from tools.migrate_logs_to_dated_dirs import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("tools.migrate_logs_to_dated_dirs", run_name="__main__")
