"""Watching a run live: a small web server, started by main.py, that shows the
visualisation and passes along everything that happens in the settlement the
moment it happens.

The settlement tells the watcher each thing as it happens -- a new week, the
start and end of every day, every alarm, wake, answer, trade, rot and death --
and the watcher keeps a copy and streams it to every browser that is looking.
A browser that opens late is sent everything so far first, so it can catch up.
Nothing here changes the run: it only listens.
"""
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class Watcher:
    # - the ports tried in turn, in case one is already taken
    ports = range(8765, 8776)

    def __init__(self, folder):
        # - everything told so far, in order, and a signal for when there is more
        self.said = []
        self.changed = threading.Condition()

        # - the first free port; with none free the run goes on unwatched
        self.server = None
        for port in self.ports:
            try:
                self.server = ThreadingHTTPServer(("127.0.0.1", port), partial(Viewer, self, directory=str(folder)))
                break
            except OSError:
                continue

        if self.server is not None:
            self.server.daemon_threads = True
            threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def address(self):
        # - where to point the browser, or None if no port was free
        if self.server is None:
            return None
        return f"http://127.0.0.1:{self.server.server_address[1]}/visualisation/"

    def tell(self, kind, what):
        # - something has happened: keep it, and wake every browser that is waiting
        message = json.dumps({"kind": kind, "what": what}, default=str)
        with self.changed:
            self.said.append(message)
            self.changed.notify_all()


class Viewer(SimpleHTTPRequestHandler):
    # - serves the repo's files as they are, and /live as a stream of what happens

    def __init__(self, watcher, *args, **kwargs):
        self.watcher = watcher
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        # - the terminal is for the run's progress, not for every request
        pass

    def end_headers(self):
        # - always the page as it is now, never a copy the browser kept
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        if self.path.split("?")[0] != "/live":
            super().do_GET()
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()

        # - first everything so far, then word that the browser has caught up,
        #   then each new thing as it happens; a quiet line now and then keeps
        #   the connection open while the models think
        sent = 0
        caught_up = False
        try:
            while True:
                with self.watcher.changed:
                    if caught_up and sent >= len(self.watcher.said):
                        self.watcher.changed.wait(timeout=15)
                    fresh = self.watcher.said[sent:]

                for message in fresh:
                    self.wfile.write(b"data: " + message.encode() + b"\n\n")
                sent += len(fresh)

                if not caught_up:
                    self.wfile.write(b'data: {"kind": "caught up", "what": null}\n\n')
                    caught_up = True
                elif not fresh:
                    self.wfile.write(b": still here\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return
