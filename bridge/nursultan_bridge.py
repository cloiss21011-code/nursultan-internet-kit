#!/usr/bin/env python3
"""Nursultan Internet Bridge — протокол v1.

Читает слот net.req скриптов через MCP-сервер клиента, выполняет HTTPS-запрос,
кладёт ответ в scripts/assets/_net/resp/<scriptId>/net-<id>-<nonce>.env.

Только стандартная библиотека Python 3.10+.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import logging
import logging.handlers
import os
import re
import socket
import sys
import time
from pathlib import Path
from urllib import parse as urlparse
from urllib import request as urlrequest

PROTO = 1
UA = "NursultanInternetKit/1"
REQUEST_BANNER = "NETREQ "
RESPONSE_BANNER = "NETRESP "
DEFAULTS = {
    "proto": PROTO,
    "mcpLink": "",
    "pollMs": 150,
    "allowlist": [],
    "allowPrivate": False,
    "maxTimeoutSec": 60,
    "maxBodyBytes": 8 * 1024 * 1024,
    "secrets": {},
    "requestLog": "requests.log",
    "stateFile": "bridge-state.json",
    "cleanAfterHours": 24,
}
DIRECTIVES = ("timeout:", "jsonpath:", "keyref:", "nonce:", "header:")
METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}
LOG = logging.getLogger("bridge")


class BridgeError(Exception):
    pass


class SafetyError(BridgeError):
    pass


# --------------------------------------------------------------------------
# конфиг и лог
# --------------------------------------------------------------------------

def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def load_config(path: Path) -> dict:
    cfg = dict(DEFAULTS)
    if path.exists():
        try:
            cfg.update(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as e:
            raise BridgeError(f"bridge.json не читается: {e}")
    else:
        path.write_text(json.dumps(DEFAULTS, indent=2, ensure_ascii=False), encoding="utf-8")
    if int(cfg["proto"]) != PROTO:
        LOG.warning("proto в конфиге %s, мост поддерживает %s", cfg["proto"], PROTO)
    return cfg


def setup_logging(cfg_dir: Path, cfg: dict) -> None:
    LOG.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S")
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    LOG.addHandler(console)
    log_path = Path(cfg["requestLog"])
    if not log_path.is_absolute():
        log_path = cfg_dir / log_path
    try:
        file_h = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        LOG.addHandler(file_h)
    except OSError as e:
        LOG.warning("лог-файл недоступен: %s", e)


# --------------------------------------------------------------------------
# MCP
# --------------------------------------------------------------------------

class Mcp:
    def __init__(self, link: str, timeout: float = 8.0):
        self.link = link.rstrip("/")
        self.timeout = timeout
        self.seq = 0

    def call(self, tool: str, args: dict | None = None):
        self.seq += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self.seq,
            "method": "tools/call",
            "params": {"name": tool, "arguments": args or {}},
        }
        req = urlrequest.Request(
            self.link,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
        except OSError as e:
            raise BridgeError(f"MCP недоступен: {e}") from e
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as e:
            raise BridgeError(f"MCP: не JSON: {e}") from e
        if "error" in obj:
            raise BridgeError(f"MCP: {obj['error']}")
        text = None
        for item in obj.get("result", {}).get("content", []):
            if item.get("type") == "text":
                text = item.get("text")
                break
        if text is None:
            raise BridgeError("MCP: пустой ответ")
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise BridgeError(f"MCP: payload не JSON: {e}") from e

    def scripts(self):
        payload = self.call("scripts_list")
        scripts = None
        assets_dir = None
        if isinstance(payload, dict):
            scripts = payload.get("scripts")
            assets_dir = payload.get("assetsDir")
            if scripts is None:
                scripts = next(
                    (v for v in payload.values()
                     if isinstance(v, list) and (not v or isinstance(v[0], dict))),
                    [],
                )
        return scripts or [], assets_dir

    def settings(self, script_id: str):
        payload = self.call("script_settings", {"id": script_id})
        if isinstance(payload, dict):
            return payload.get("settings") or []
        return []


# --------------------------------------------------------------------------
# конверт запроса
# --------------------------------------------------------------------------

def parse_request(raw: str) -> dict:
    if not raw.startswith(REQUEST_BANNER):
        raise BridgeError("конверт: нет баннера NETREQ")
    sep = raw.find("\n\n")
    head = raw if sep == -1 else raw[:sep]
    body = "" if sep == -1 else raw[sep + 2:]
    lines = head.split("\n")
    banner = lines[0].strip()
    rid = banner[len(REQUEST_BANNER):].strip()
    if not rid.isdigit() or int(rid) <= 0:
        raise BridgeError("конверт: bad id")
    if len(lines) < 2:
        raise BridgeError("конверт: нет строки метода")
    request_line = lines[1].strip()
    sp = request_line.find(" ")
    if sp <= 0:
        raise BridgeError("конверт: нет строки запроса")
    method = request_line[:sp].upper()
    url = request_line[sp + 1:].strip()
    if method not in METHODS:
        raise BridgeError(f"конверт: метод {method} не поддерживается")
    req = {
        "id": int(rid),
        "method": method,
        "url": url,
        "headers": [],
        "timeout": 60,
        "jsonpath": None,
        "keyref": None,
        "nonce": "0",
        "body": body,
    }
    for line in lines[2:]:
        text = line.strip()
        if not text:
            continue
        for directive in DIRECTIVES:
            if text.lower().startswith(directive):
                value = text[len(directive):].strip()
                if directive == "timeout:":
                    try:
                        req["timeout"] = int(value)
                    except ValueError:
                        raise BridgeError(f"конверт: timeout {value!r}")
                elif directive == "jsonpath:":
                    req["jsonpath"] = value
                elif directive == "keyref:":
                    req["keyref"] = value
                elif directive == "nonce:":
                    req["nonce"] = value
                elif directive == "header:":
                    if "\n" in value or value.count(":") < 1:
                        raise BridgeError(f"конверт: header {value!r}")
                    req["headers"].append(value)
                break
        else:
            raise BridgeError(f"конверт: неизвестная директива {text!r}")
    return req


def substitute_key(req: dict, secrets: dict) -> None:
    needle = "{{KEY}}"
    has_placeholder = needle in req["url"] or needle in req["body"] or any(
        needle in v for _, v in split_headers(req["headers"])
    )
    if not has_placeholder:
        return
    if not req["keyref"]:
        raise SafetyError("{{KEY}} в запросе, но директива keyref отсутствует")
    key = secrets.get(req["keyref"])
    if not key:
        raise SafetyError(f"keyref {req['keyref']!r} не найден в bridge.json")
    req["url"] = req["url"].replace(needle, key)
    req["body"] = req["body"].replace(needle, key)
    req["headers"] = [
        f"{name}: {value.replace(needle, key)}" for name, value in split_headers(req["headers"])
    ]


def split_headers(headers: list[str]):
    for line in headers:
        idx = line.find(":")
        if idx <= 0:
            raise BridgeError(f"конверт: header {line!r}")
        yield line[:idx].strip(), line[idx + 1:].strip()


# --------------------------------------------------------------------------
# jsonpath
# --------------------------------------------------------------------------

def jsonpath_get(data, path: str):
    current = data
    for part in path.split("."):
        if part == "":
            continue
        if isinstance(current, list):
            index = int(part)
            current = current[index]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(part)
    return current


# --------------------------------------------------------------------------
# безопасность
# --------------------------------------------------------------------------

def host_allowed(host: str, allowlist: list[str]) -> bool:
    if not allowlist:
        return True
    host = host.lower().rstrip(".")
    for entry in allowlist:
        entry = entry.strip().lower().rstrip(".")
        if not entry:
            continue
        if entry.startswith("*."):
            if host.endswith(entry[1:]) and host != entry[1:]:
                return True
        elif host == entry or host.endswith("." + entry):
            return True
    return False


def host_resolves_private(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        raw = info[4][0]
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return True
    return False


def check_url(url: str, cfg: dict) -> None:
    parts = urlparse.urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise SafetyError(f"схема {parts.scheme!r} запрещена")
    host = parts.hostname
    if not host:
        raise SafetyError("в URL нет хоста")
    if not host_allowed(host, cfg["allowlist"]):
        raise SafetyError(f"хост {host} не входит в allowlist")
    if not cfg["allowPrivate"] and host_resolves_private(host):
        raise SafetyError(f"хост {host} ведёт на приватную сеть")


def make_opener(cfg: dict):
    class GuardedRedirect(urlrequest.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            check_url(newurl, cfg)
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    return urlrequest.build_opener(GuardedRedirect)


# --------------------------------------------------------------------------
# выполнение запроса
# --------------------------------------------------------------------------

def fetch(cfg: dict, req: dict) -> tuple[int, str]:
    substitute_key(req, cfg["secrets"])
    check_url(req["url"], cfg)
    timeout = max(1, min(int(req["timeout"]), int(cfg["maxTimeoutSec"])))
    headers = {"User-Agent": UA, "Accept": "*/*"}
    for name, value in split_headers(req["headers"]):
        headers[name] = value
    data = req["body"].encode("utf-8") if req["body"] else None
    http_request = urlrequest.Request(
        req["url"], data=data, headers=headers, method=req["method"]
    )
    opener = make_opener(cfg)
    started = time.monotonic()
    try:
        with opener.open(http_request, timeout=timeout) as response:
            raw = response.read(int(cfg["maxBodyBytes"]) + 1)
            if len(raw) > int(cfg["maxBodyBytes"]):
                raise BridgeError(
                    f"тело больше {int(cfg['maxBodyBytes'])} байт"
                )
            status = int(getattr(response, "status", response.getcode()))
            content_type = response.headers.get("Content-Type", "")
    except SafetyError:
        raise
    except BridgeError:
        raise
    except OSError as e:
        raise BridgeError(f"сетевая ошибка: {e}") from e
    elapsed = int((time.monotonic() - started) * 1000)
    charset = "utf-8"
    match = re.search(r"charset=([\w-]+)", content_type, re.I)
    if match:
        charset = match.group(1)
    try:
        text = raw.decode(charset, errors="replace")
    except LookupError:
        text = raw.decode("utf-8", errors="replace")
    if req["jsonpath"]:
        try:
            extracted = jsonpath_get(json.loads(text), req["jsonpath"])
        except (json.JSONDecodeError, KeyError, IndexError, ValueError, TypeError) as e:
            raise BridgeError(f"jsonpath {req['jsonpath']!r}: {e}") from e
        text = extracted if isinstance(extracted, str) else json.dumps(extracted, ensure_ascii=False)
    LOG.info(
        "req id=%s script=%s %s %s -> %s %sms %sB",
        req["id"], req.get("script", "-"), req["method"],
        urlparse.urlsplit(req["url"]).hostname, status, elapsed, len(raw),
    )
    return status, text


# --------------------------------------------------------------------------
# запись ответа
# --------------------------------------------------------------------------

def sanitize(value: str, pattern: str, fallback: str) -> str:
    cleaned = re.sub(pattern, "", value)
    return cleaned[:64] if cleaned else fallback


def write_response(assets_dir: Path, script_id: str, req: dict, code: int, text: str) -> None:
    if ".." in script_id or not script_id:
        raise SafetyError(f"недопустимый id скрипта: {script_id!r}")
    folder = assets_dir / "_net" / "resp" / sanitize(script_id, r"[^A-Za-z0-9._-]", "_")
    folder.mkdir(parents=True, exist_ok=True)
    rid = sanitize(str(req["id"]), r"[^0-9]", "0")
    nonce = sanitize(req["nonce"], r"[^A-Za-z0-9_-]", "0")
    header = f"{RESPONSE_BANNER}{rid}\n{code}\nbody: {len(text)}\n"
    payload = (header + text).encode("utf-8")
    tmp = folder / f".net-{rid}-{nonce}-{os.getpid()}.tmp"
    tmp.write_bytes(payload)
    os.replace(tmp, folder / f"net-{rid}-{nonce}.env")


def error_response(assets_dir: Path, script_id: str, req: dict, message: str) -> None:
    LOG.warning("req id=%s script=%s отклонён: %s", req.get("id", "?"), script_id, message)
    write_response(assets_dir, script_id, req, 0, f"bridge error: {message}")


# --------------------------------------------------------------------------
# состояние
# --------------------------------------------------------------------------

def load_state(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(path: Path, state: dict) -> None:
    try:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state), encoding="utf-8")
        os.replace(tmp, path)
    except OSError as e:
        LOG.warning("state не записан: %s", e)


def cleanup(assets_dir: Path, hours: int) -> None:
    if hours <= 0:
        return
    limit = time.time() - hours * 3600
    resp_root = assets_dir / "_net" / "resp"
    if not resp_root.is_dir():
        return
    for folder in resp_root.iterdir():
        if not folder.is_dir():
            continue
        for file in folder.iterdir():
            try:
                if file.is_file() and file.stat().st_mtime < limit:
                    file.unlink()
            except OSError:
                pass


# --------------------------------------------------------------------------
# цикл
# --------------------------------------------------------------------------

def looks_like_request(setting: dict) -> bool:
    if setting.get("key") == "net.req":
        return bool(setting.get("value"))
    value = setting.get("value")
    return (
        setting.get("kind") == "input"
        and isinstance(value, str)
        and value.startswith(REQUEST_BANNER)
    )


def run(cfg: dict, cfg_dir: Path, assets_hint: str | None = None) -> int:
    mcp = Mcp(cfg["mcpLink"])
    state_path = Path(cfg["stateFile"])
    if not state_path.is_absolute():
        state_path = cfg_dir / state_path
    state = load_state(state_path)
    assets_dir = Path(assets_hint) if assets_hint else default_assets_dir()
    cleanup(assets_dir, int(cfg["cleanAfterHours"]))
    last_error_log = 0.0
    last_cleanup = time.monotonic()
    LOG.info("мост запущен, poll=%sms allowlist=%s", cfg["pollMs"],
             cfg["allowlist"] or "все домены")
    while True:
        try:
            scripts, reported_assets = mcp.scripts()
            if reported_assets:
                assets_dir = Path(reported_assets)
            for script in scripts:
                script_id = script.get("id")
                if not script_id:
                    continue
                try:
                    settings = mcp.settings(script_id)
                except BridgeError as e:
                    LOG.debug("settings %s: %s", script_id, e)
                    continue
                request_value = next(
                    (s.get("value") for s in settings if looks_like_request(s)), None
                )
                if not request_value:
                    continue
                digest = hashlib.sha1(
                    f"{script_id}\n{request_value}".encode("utf-8")
                ).hexdigest()
                seen = state.setdefault(script_id, [])
                if digest in seen:
                    continue
                seen.append(digest)
                if len(seen) > 2000:
                    del seen[:-2000]
                process_one(cfg, assets_dir, script_id, request_value, state, state_path)
        except BridgeError as e:
            now = time.monotonic()
            if now - last_error_log > 30:
                LOG.warning("%s", e)
                last_error_log = now
        time.sleep(max(25, int(cfg["pollMs"])) / 1000)
        if time.monotonic() - last_cleanup > 3600:
            cleanup(assets_dir, int(cfg["cleanAfterHours"]))
            last_cleanup = time.monotonic()


def process_one(cfg, assets_dir, script_id, raw_request, state, state_path):
    try:
        req = parse_request(raw_request)
        req["script"] = script_id
        code, text = fetch(cfg, req)
        write_response(assets_dir, script_id, req, code, text)
    except (BridgeError, OSError) as e:
        try:
            parsed = parse_request(raw_request)
        except BridgeError:
            return
        parsed["script"] = script_id
        error_response(assets_dir, script_id, parsed, str(e))
    finally:
        save_state(state_path, state)


def default_assets_dir() -> Path:
    appdata = os.environ.get("APPDATA") or str(Path.home())
    return Path(appdata) / "Nursultan" / "scripts" / "assets"


# --------------------------------------------------------------------------
# режимы
# --------------------------------------------------------------------------

def check_mode(cfg: dict) -> int:
    problems = []
    if not cfg["mcpLink"]:
        problems.append("mcpLink пуст — включи MCP в Scripts-табе и вставь ссылку")
    else:
        try:
            mcp = Mcp(cfg["mcpLink"])
            scripts, assets = mcp.scripts()
            print(f"MCP: ок, скриптов {len(scripts)}, assets: {assets}")
        except BridgeError as e:
            problems.append(str(e))
    for problem in problems:
        print(f"FAIL {problem}")
    return 1 if problems else 0


def selftest() -> int:
    failures = []

    def expect(condition, message):
        if not condition:
            failures.append(message)

    req = parse_request(
        "NETREQ 7\nPOST https://api.example.com/v1\nnonce: n-1\n"
        "timeout: 30\njsonpath: a.0.b\nkeyref: k\nheader: Content-Type: application/json\n"
        "\n{\"x\":1}\n\nещё"
    )
    expect(req["id"] == 7, "id")
    expect(req["method"] == "POST", "method")
    expect(req["timeout"] == 30, "timeout")
    expect(req["jsonpath"] == "a.0.b", "jsonpath")
    expect(req["nonce"] == "n-1", "nonce")
    expect(req["body"] == "{\"x\":1}\n\nещё", f"body={req['body']!r}")

    minimal = parse_request("NETREQ 1\nGET https://a.example/x\n\n")
    expect(minimal["body"] == "", "пустое тело")
    expect(minimal["timeout"] == 60, "timeout по умолчанию")

    data = {"candidates": [{"content": {"parts": [{"text": "привет"}]}}]}
    expect(jsonpath_get(data, "candidates.0.content.parts.0.text") == "привет", "jsonpath list")
    expect(jsonpath_get({"a": {"b": 3}}, "a.b") == 3, "jsonpath dict")
    try:
        jsonpath_get(data, "candidates.9.text")
        failures.append("jsonpath: ожидалась ошибка")
    except (IndexError, KeyError, TypeError, ValueError):
        pass

    expect(host_allowed("api.deepseek.com", []), "allowlist пуст = всё разрешено")
    expect(host_allowed("api.deepseek.com", ["deepseek.com"]), "allowlist суффикс")
    expect(host_allowed("x.deepseek.com", ["*.deepseek.com"]), "allowlist wildcard")
    expect(not host_allowed("evil.com", ["deepseek.com"]), "allowlist чужой хост")

    expect(ipaddress.ip_address("127.0.0.1").is_loopback, "loopback")
    expect(ipaddress.ip_address("192.168.1.5").is_private, "private")

    sample = {"id": 1, "nonce": "n-1", "method": "GET", "url": "https://x.example/",
              "headers": [], "timeout": 60, "jsonpath": None, "keyref": None, "body": ""}
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        assets = Path(tmp)
        write_response(assets, "demo", sample, 200, "тело ответа")
        file = assets / "_net" / "resp" / "demo" / "net-1-n-1.env"
        raw = file.read_text(encoding="utf-8")
        head = raw.split("\n", 3)
        expect(head[0] == "NETRESP 1", "response banner")
        expect(head[1] == "200", "response code")
        expect(head[2] == "body: 11", f"response length {head[2]!r}")
        expect(head[3] == "тело ответа", "response body")

    if failures:
        for item in failures:
            print(f"FAIL {item}")
        return 1
    print("selftest OK")
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Nursultan Internet Bridge")
    parser.add_argument("--config", default=None, help="путь к bridge.json")
    parser.add_argument("--check", action="store_true", help="проверить конфиг и MCP")
    parser.add_argument("--selftest", action="store_true", help="автотест протокола")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    config_path = Path(args.config) if args.config else app_dir() / "bridge.json"
    cfg_dir = config_path.resolve().parent
    try:
        cfg = load_config(config_path)
    except BridgeError as e:
        print(f"FAIL {e}")
        return 1
    setup_logging(cfg_dir, cfg)

    if args.check:
        return check_mode(cfg)

    if not cfg["mcpLink"]:
        LOG.error(
            "mcpLink пуст. Клиент → Scripts → MCP → Enabled → Copy link → вставь в %s",
            config_path,
        )
        return 1
    try:
        run(cfg, cfg_dir)
    except KeyboardInterrupt:
        LOG.info("остановлен")
    return 0


if __name__ == "__main__":
    sys.exit(main())
