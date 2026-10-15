#!/usr/bin/env python3
"""Интеграционный тест: фейковый MCP + фейковый API → мост → файл ответа.

Запуск: python tools/integration_test.py
Требуется Python 3.10+, сеть не нужна.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRIDGE = ROOT / "bridge" / "nursultan_bridge.py"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    tmp = Path(tempfile.mkdtemp(prefix="kit-test-"))
    assets = tmp / "assets"
    assets.mkdir(parents=True)
    state = {"port": 0, "envelope": "", "settings_reads": 0}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _reply(self, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            request = json.loads(self.rfile.read(length) or b"{}")
            tool = request.get("params", {}).get("name")
            if tool == "scripts_list":
                payload = {
                    "scriptsDir": str(tmp),
                    "assetsDir": str(assets),
                    "scripts": [{"id": "demo", "status": "READY", "name": "demo"}],
                }
            elif tool == "script_settings":
                state["settings_reads"] += 1
                payload = {
                    "id": "demo",
                    "settings": [
                        {"key": "net.req", "kind": "input", "value": state["envelope"]}
                    ],
                }
            else:
                payload = {"error": f"unknown tool {tool}"}
            self._reply(
                {
                    "jsonrpc": "2.0",
                    "id": request.get("id", 1),
                    "result": {"content": [{"type": "text", "text": json.dumps(payload)}]},
                }
            )

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/hello":
                self.send_response(404)
                self.end_headers()
                return
            key = urllib.parse.parse_qs(parsed.query).get("key", [""])[0]
            value = "ok42" if key == "XYZ" else "BADKEY"
            body = json.dumps({"value": value}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    state["port"] = port
    state["envelope"] = (
        "NETREQ 1\n"
        f"GET http://127.0.0.1:{port}/hello?key={{{{KEY}}}}\n"
        "nonce: it-1\n"
        "timeout: 5\n"
        "jsonpath: value\n"
        "keyref: demo\n"
        "\n"
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()

    config = {
        "proto": 1,
        "mcpLink": f"http://127.0.0.1:{port}/mcp/test",
        "pollMs": 50,
        "allowlist": [],
        "allowPrivate": True,
        "maxTimeoutSec": 10,
        "maxBodyBytes": 1048576,
        "secrets": {"demo": "XYZ"},
        "requestLog": str(tmp / "requests.log"),
        "stateFile": str(tmp / "state.json"),
        "cleanAfterHours": 24,
    }
    config_path = tmp / "bridge.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    proc = subprocess.Popen(
        [sys.executable, str(BRIDGE), "--config", str(config_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
    )
    response_file = assets / "_net" / "resp" / "demo" / "net-1-it-1.env"
    deadline = __import__("time").time() + 10
    try:
        while __import__("time").time() < deadline:
            if response_file.exists():
                break
            if proc.poll() is not None:
                break
            __import__("time").sleep(0.1)

        failures = []
        if not response_file.exists():
            failures.append("файл ответа не появился")
        else:
            raw = response_file.read_text(encoding="utf-8")
            expected = "NETRESP 1\n200\nbody: 4\nok42"
            if raw != expected:
                failures.append(f"тело ответа: {raw!r} != {expected!r}")
        if state["settings_reads"] < 1:
            failures.append("мост не прочитал script_settings")
    finally:
        proc.terminate()
        try:
            output, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            output, _ = proc.communicate()
        server.shutdown()

    if failures:
        for item in failures:
            print(f"FAIL {item}")
        if output:
            print("--- вывод моста ---")
            print(output)
        return 1
    print("integration OK: MCP → слот net.req → HTTP+{{KEY}}+jsonpath → файл ответа")
    return 0


if __name__ == "__main__":
    sys.exit(main())
