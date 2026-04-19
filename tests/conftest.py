"""Test bootstrap.

Each microservice ships its own ``schemas.py`` / ``calculator.py`` /
``ahp.py`` at the *top level* of its directory (so ``main.py`` can do
``from schemas import ...`` without any package). To exercise those
modules from this top-level ``tests/`` package we load each service's
files via ``importlib.util.spec_from_file_location`` under a unique
alias (``mc_ahp``, ``fin_calculator``, ...) and temporarily aim
``sys.modules['schemas']`` at the right schemas module so the calculator's
own ``from schemas import X`` can resolve. After the import returns,
the calculator already has its symbols bound, so the global
``sys.modules['schemas']`` can safely be overwritten by the next service.

Also mints an ephemeral RSA keypair + env vars so that ``eco_common.auth``
(which reads JWT_PUBLIC_KEY_PATH at module import time) can load under test
without a real secrets directory being mounted.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))


def _bootstrap_jwt_env() -> None:
    if os.getenv("JWT_PUBLIC_KEY_PATH") and os.getenv("JWT_ISSUER") and os.getenv("JWT_AUDIENCE"):
        return
    # Local imports keep `cryptography` off the import path when the caller
    # already provisioned real keys via environment variables.
    from cryptography.hazmat.primitives import serialization  # noqa: PLC0415
    from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: PLC0415

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    priv_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    tmp = Path(tempfile.mkdtemp(prefix="eco-test-keys-"))
    (tmp / "jwt_public.pem").write_bytes(pub_pem)
    (tmp / "jwt_private.pem").write_bytes(priv_pem)

    os.environ.setdefault("JWT_PUBLIC_KEY_PATH", str(tmp / "jwt_public.pem"))
    os.environ.setdefault("JWT_PRIVATE_KEY_PATH", str(tmp / "jwt_private.pem"))
    os.environ.setdefault("JWT_ISSUER", "eco-analysis-test")
    os.environ.setdefault("JWT_AUDIENCE", "eco-analysis-test")


_bootstrap_jwt_env()


def load_service(prefix: str, service_dir: str, modules: Iterable[str]) -> dict[str, ModuleType]:
    """Load ``modules`` from ``services/<service_dir>/`` under unique aliases.

    The first module loaded must always be ``schemas`` so the rest can
    resolve their ``from schemas import ...`` references.
    """
    base = ROOT / "services" / service_dir
    out: dict[str, ModuleType] = {}
    for name in modules:
        path = base / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"{prefix}_{name}", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"{prefix}_{name}"] = module
        if name == "schemas":
            sys.modules["schemas"] = module
        spec.loader.exec_module(module)
        out[name] = module
    return out
