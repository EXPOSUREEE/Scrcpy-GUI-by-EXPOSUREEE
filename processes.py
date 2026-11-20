"""Launch sessions and stream both pipes without blocking the Qt event loop."""
import subprocess
from threading import Thread

from adb import HIDDEN
from console import infer_fix_hint


class ProcessRunner:
    def __init__(self, env, log, finished):
        self.env = env
        self.log = log
        self.finished = finished

    def set_env(self, env):
        self.env = env

    def start(self, command, cwd, *, shell=False, debug=False):
        name = "Console" if shell else "scrcpy"
        self.log("INFO", command if shell else subprocess.list2cmdline(command))
        capture = {} if debug else {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
        process = subprocess.Popen(command, cwd=cwd, env=self.env, shell=shell, **capture,
                                   stdin=None if debug else subprocess.DEVNULL,
                                   creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0) if debug else HIDDEN)
        def read(stream, level):
            with stream:
                for chunk in iter(lambda: stream.readline(16384), b""):
                    line = chunk.decode("utf-8", "replace").rstrip()
                    self.log(level, line)
                    hint = infer_fix_hint(line)
                    if hint:
                        self.log("HINT", hint)

        def monitor():
            readers = []
            if not debug:
                for stream, level in ((process.stdout, "OUT"), (process.stderr, "ERR")):
                    worker = Thread(target=read, args=(stream, level), daemon=True)
                    worker.start()
                    readers.append(worker)
            code = process.wait()
            for worker in readers:
                worker.join()
            self.finished(name, code)

        Thread(target=monitor, daemon=True).start()
