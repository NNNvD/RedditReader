#!/usr/bin/env python3
"""Minimal OAuth client for reading the authenticated Reddit user's saved items.

This scaffold is intended for use only after Reddit grants Data API access and
client credentials are configured locally in .env.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

AUTHORIZE_URL = "https://www.reddit.com/api/v1/authorize"
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_BASE = "https://oauth.reddit.com"
SCOPES = "identity history"


def load_config() -> dict[str, str]:
    load_dotenv()
    cfg = {
        "client_id": os.getenv("REDDIT_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("REDDIT_CLIENT_SECRET", "").strip(),
        "redirect_uri": os.getenv("REDDIT_REDIRECT_URI", "http://localhost:8080").strip(),
        "user_agent": os.getenv(
            "REDDIT_USER_AGENT", "RedditReader/0.1 by u/Mission_Formal_2028"
        ).strip(),
        "token_file": os.getenv("REDDIT_TOKEN_FILE", ".reddit_token.json").strip(),
    }
    if not cfg["client_id"]:
        raise SystemExit("REDDIT_CLIENT_ID is missing. Copy .env.example to .env and configure it after Reddit approval.")
    if not cfg["user_agent"]:
        raise SystemExit("REDDIT_USER_AGENT must not be blank.")
    return cfg


def basic_auth_header(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def token_headers(cfg: dict[str, str]) -> dict[str, str]:
    return {
        "Authorization": basic_auth_header(cfg["client_id"], cfg["client_secret"]),
        "User-Agent": cfg["user_agent"],
    }


def api_headers(access_token: str, cfg: dict[str, str]) -> dict[str, str]:
    return {
        "Authorization": f"bearer {access_token}",
        "User-Agent": cfg["user_agent"],
    }


def save_token(token: dict[str, Any], path: str) -> None:
    Path(path).write_text(json.dumps(token, indent=2), encoding="utf-8")


def load_token(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"No token file found at {path}. Run `python reddit_saved_reader.py authorize` first.")
    return json.loads(p.read_text(encoding="utf-8"))


def exchange_code(code: str, cfg: dict[str, str]) -> dict[str, Any]:
    response = requests.post(
        TOKEN_URL,
        headers=token_headers(cfg),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": cfg["redirect_uri"],
        },
        timeout=30,
    )
    response.raise_for_status()
    token = response.json()
    if "error" in token:
        raise RuntimeError(f"Reddit token exchange failed: {token}")
    return token


def refresh_access_token(token: dict[str, Any], cfg: dict[str, str]) -> dict[str, Any]:
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        return token
    response = requests.post(
        TOKEN_URL,
        headers=token_headers(cfg),
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        timeout=30,
    )
    response.raise_for_status()
    refreshed = response.json()
    if "error" in refreshed:
        raise RuntimeError(f"Reddit token refresh failed: {refreshed}")
    if "refresh_token" not in refreshed:
        refreshed["refresh_token"] = refresh_token
    save_token(refreshed, cfg["token_file"])
    return refreshed


def authorize(cfg: dict[str, str]) -> None:
    parsed = urllib.parse.urlparse(cfg["redirect_uri"])
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise SystemExit("This scaffold expects a local HTTP redirect URI such as http://localhost:8080.")

    state = secrets.token_urlsafe(32)
    result: dict[str, str] = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result["state"] = params.get("state", [""])[0]
            result["code"] = params.get("code", [""])[0]
            result["error"] = params.get("error", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Reddit authorization received. You can close this tab.")

        def log_message(self, format: str, *args: Any) -> None:
            return

    port = parsed.port or 80
    server = HTTPServer((parsed.hostname or "localhost", port), CallbackHandler)
    query = urllib.parse.urlencode(
        {
            "client_id": cfg["client_id"],
            "response_type": "code",
            "state": state,
            "redirect_uri": cfg["redirect_uri"],
            "duration": "permanent",
            "scope": SCOPES,
        }
    )
    url = f"{AUTHORIZE_URL}?{query}"
    print("Opening Reddit authorization page...")
    print(url)
    webbrowser.open(url)
    server.handle_request()

    if result.get("error"):
        raise SystemExit(f"Authorization failed: {result['error']}")
    if result.get("state") != state:
        raise SystemExit("OAuth state mismatch; authorization aborted.")
    if not result.get("code"):
        raise SystemExit("No authorization code was returned.")

    token = exchange_code(result["code"], cfg)
    save_token(token, cfg["token_file"])
    print(f"Authorization succeeded. Token stored locally in {cfg['token_file']}.")


def api_get(path: str, token: dict[str, Any], cfg: dict[str, str], params: dict[str, Any] | None = None) -> requests.Response:
    access_token = token.get("access_token", "")
    response = requests.get(
        API_BASE + path,
        headers=api_headers(access_token, cfg),
        params=params,
        timeout=30,
    )
    if response.status_code == 401 and token.get("refresh_token"):
        token = refresh_access_token(token, cfg)
        response = requests.get(
            API_BASE + path,
            headers=api_headers(token["access_token"], cfg),
            params=params,
            timeout=30,
        )
    response.raise_for_status()
    return response


def get_identity(token: dict[str, Any], cfg: dict[str, str]) -> dict[str, Any]:
    return api_get("/api/v1/me", token, cfg).json()


def simplify_child(child: dict[str, Any]) -> dict[str, Any]:
    kind = child.get("kind")
    data = child.get("data", {})
    item_type = "post" if kind == "t3" else "comment" if kind == "t1" else kind
    return {
        "id": data.get("name") or data.get("id"),
        "type": item_type,
        "subreddit": data.get("subreddit"),
        "author": data.get("author"),
        "title": data.get("title"),
        "link_title": data.get("link_title"),
        "permalink": ("https://www.reddit.com" + data["permalink"]) if data.get("permalink") else None,
        "created_utc": data.get("created_utc"),
    }


def list_saved(limit: int, output: str | None, cfg: dict[str, str]) -> None:
    if limit < 1 or limit > 100:
        raise SystemExit("--limit must be between 1 and 100 for this initial scaffold.")
    token = load_token(cfg["token_file"])
    identity = get_identity(token, cfg)
    username = identity.get("name")
    if not username:
        raise SystemExit("Could not determine the authenticated Reddit username.")

    response = api_get(
        f"/user/{urllib.parse.quote(username, safe='')}/saved",
        token,
        cfg,
        params={"limit": limit, "raw_json": 1},
    )
    listing = response.json().get("data", {})
    items = [simplify_child(child) for child in listing.get("children", [])]
    result = {
        "authenticated_user": username,
        "count": len(items),
        "after": listing.get("after"),
        "items": items,
    }

    text = json.dumps(result, indent=2, ensure_ascii=False)
    if output:
        Path(output).write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {len(items)} saved-item references to {output}.")
    else:
        print(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read saved items from the authenticated Reddit account.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("authorize", help="Authorize the Reddit account through OAuth.")
    list_parser = sub.add_parser("list", help="Retrieve saved-item reference metadata.")
    list_parser.add_argument("--limit", type=int, default=100)
    list_parser.add_argument("--output", type=str)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    cfg = load_config()
    try:
        if args.command == "authorize":
            authorize(cfg)
        elif args.command == "list":
            list_saved(args.limit, args.output, cfg)
    except requests.HTTPError as exc:
        body = exc.response.text[:1000] if exc.response is not None else ""
        raise SystemExit(f"Reddit API request failed: {exc}\n{body}") from exc


if __name__ == "__main__":
    main()
