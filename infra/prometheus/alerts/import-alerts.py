#!/usr/bin/env python3
"""Import Grafana Unified Alerting rules from alerts.json.

Usage:
    export GRAFANA_URL=http://localhost:8080
    export GRAFANA_USER=admin
    export GRAFANA_PASSWORD=<password>
    python import-alerts.py
"""

import json
import os
import ssl
import sys
import urllib.request
from pathlib import Path
from urllib.error import HTTPError

GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://localhost:8080")
GRAFANA_USER = os.environ.get("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.environ.get("GRAFANA_PASSWORD", "")
ALERTS_FILE = Path(__file__).with_name("alerts.json")


def _request(method, path, json_data=None):
    url = f"{GRAFANA_URL}{path}"
    data = json.dumps(json_data).encode("utf-8") if json_data is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    credentials = f"{GRAFANA_USER}:{GRAFANA_PASSWORD}".encode("utf-8")
    import base64

    req.add_header("Authorization", "Basic " + base64.b64encode(credentials).decode("ascii"))
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def ensure_folder(title):
    status, body = _request("GET", "/api/folders")
    if status != 200:
        print(f"Failed to list folders: {status} {body}")
        sys.exit(1)
    folders = json.loads(body)
    for folder in folders:
        if folder["title"] == title:
            return folder["uid"]
    status, body = _request("POST", "/api/folders", {"title": title})
    if status not in (200, 201):
        print(f"Failed to create folder: {status} {body}")
        sys.exit(1)
    return json.loads(body)["uid"]


def main():
    if not GRAFANA_PASSWORD:
        print("Set GRAFANA_PASSWORD environment variable")
        sys.exit(1)

    with ALERTS_FILE.open(encoding="utf-8") as fp:
        payload = json.load(fp)

    folder_uid = ensure_folder("alerts")

    for group in payload.get("groups", []):
        group_name = group["name"]
        for rule in group.get("rules", []):
            rule["folderUID"] = folder_uid
            rule["ruleGroup"] = group_name
            rule["orgID"] = rule.pop("orgId", 1)
            rule.pop("id", None)
            rule.pop("updated", None)

            status, body = _request("POST", "/api/v1/provisioning/alert-rules", rule)
            if status in (200, 201):
                print(f"Imported: {rule['title']}")
            elif status == 409:
                print(f"Already exists: {rule['title']}")
            else:
                print(f"Failed to import {rule['title']}: {status} {body}")


if __name__ == "__main__":
    main()
