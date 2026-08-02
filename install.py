#!/usr/bin/env python3
"""
Universal install/build/deploy script for otus-msa services.

Auto-discovers all app-* services under services/ and charts/ directories.
Adding a new service is zero-config: just create services/app-<name> and
charts/chart-app-<name>, and it will be picked up automatically.

Usage:
  ./install.py              # deploy (re-use current image tags from helm)
  ./install.py build        # build + load images + deploy
  ./install.py build <svc>  # build + load + deploy only one service
  ./install.py -n           # dry-run: show what would be done
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent
SERVICES_DIR = ROOT / "services"
CHARTS_DIR = ROOT / "charts"
DOCKERFILE = SERVICES_DIR / "Dockerfile"
REGISTRY = "cianoid/otus-msa"
NAMESPACE = "default"
HELMFILE = ROOT / "helmfile.yaml.gotmpl"


def discover_services() -> List[str]:
    """Return sorted list of service short-names (e.g. 'auth', 'user', 'order')."""
    names = []
    for entry in sorted(SERVICES_DIR.iterdir()):
        if entry.is_dir() and entry.name.startswith("app-"):
            names.append(entry.name.removeprefix("app-"))
    return names


def svc_dir(name: str) -> Path:
    return SERVICES_DIR / f"app-{name}"


def chart_dir(name: str) -> Path:
    return CHARTS_DIR / f"chart-app-{name}"


def helm_release(name: str) -> str:
    return f"app-{name}"


def helmfile_key(name: str) -> str:
    """Convert 'my-service' → 'app_my_service' for helmfile StateValues."""
    return f"app_{name.replace('-', '_')}"


def tag(name: str, date_str: str) -> str:
    return f"{name}-{date_str}"


def image(tag_val: str) -> str:
    return f"{REGISTRY}:{tag_val}"


def run(cmd: list[str], dry: bool, **kwargs) -> None:
    msg = " ".join(cmd)
    if dry:
        print(f"  [dry] {msg}")
        return
    subprocess.run(cmd, check=True, **kwargs)


def get_current_tag(name: str, dry: bool) -> Optional[str]:
    """Ask helm for the current image tag of a release."""
    release = helm_release(name)
    if dry:
        print(f"  [dry] helm get values {release} -n {NAMESPACE}")
        return "dry-tag"
    try:
        result = subprocess.run(
            ["helm", "get", "values", release, "-n", NAMESPACE, "-o", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        return data.get("image", {}).get("tag")
    except subprocess.CalledProcessError:
        return None


def build_images(services: List[str], date_str: str, dry: bool) -> Dict[str, str]:
    """Build docker images. Returns {name: tag}."""
    tags: Dict[str, str] = {}
    for name in services:
        t = tag(name, date_str)
        tags[name] = t
        img = image(t)
        ctx = str(svc_dir(name))
        print(f"Сборка {img} ...")
        run(
            [
                "docker",
                "build",
                "-q",
                "-t",
                img,
                "-f",
                str(DOCKERFILE),
                ctx,
            ],
            dry=dry,
        )
    return tags


def load_images(tags: Dict[str, str], dry: bool) -> None:
    """Load images into minikube."""
    for name, t in tags.items():
        img = image(t)
        print(f"Загрузка {img} в кубер ...")
        run(["minikube", "image", "load", img], dry=dry)


def deploy(services: List[str], tags: Dict[str, str], dry: bool) -> None:
    """Run helmfile sync with the given tags."""
    cmd = ["helmfile", "--state-values-set"]
    parts = []
    for name in services:
        t = tags[name]
        key = helmfile_key(name)
        parts.append(f"{key}.image.tag={t}")
    cmd.append(",".join(parts))
    cmd.append("sync")
    print(f"Деплой приложений: {', '.join(f'{n}={tags[n]}' for n in services)}")
    run(cmd, dry=dry)


def fail_missing_tags(missing: List[str]) -> None:
    print("Ошибка: не удалось определить текущие теги для:", ", ".join(missing))
    print("Возможно, приложения ещё не были установлены.")
    print("Запустите 'install.py build' для первой установки.")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="otus-msa install script")
    parser.add_argument(
        "mode",
        nargs="?",
        default="deploy",
        choices=["build", "deploy"],
        help="Режим: build (сборка + загрузка + деплой) или deploy (только деплой)",
    )
    parser.add_argument(
        "service",
        nargs="?",
        default=None,
        help="Ограничиться одним сервисом (только для build)",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Показать, что будет сделано, но не выполнять",
    )
    args = parser.parse_args()

    all_services = discover_services()
    if not all_services:
        print("Не найдено ни одного сервиса в services/app-* — нечего делать.")
        sys.exit(1)

    if args.service:
        if args.service not in all_services:
            print(f"Сервис '{args.service}' не найден. Доступны: {', '.join(all_services)}")
            sys.exit(1)
        services = [args.service]
    else:
        services = all_services

    print(f"Обнаружено сервисов: {', '.join(services)}")

    if args.mode == "build":
        date_str = datetime.now().strftime("%Y-%m-%d-%H%M")
        tags = build_images(services, date_str, args.dry_run)
        load_images(tags, args.dry_run)
        deploy(services, tags, args.dry_run)
    else:
        # deploy mode: read current tags from helm
        tags: Dict[str, str] = {}
        missing: List[str] = []
        for name in services:
            t = get_current_tag(name, args.dry_run)
            if t:
                tags[name] = t
            else:
                missing.append(name)
        if missing:
            fail_missing_tags(missing)
        deploy(services, tags, args.dry_run)


if __name__ == "__main__":
    main()
