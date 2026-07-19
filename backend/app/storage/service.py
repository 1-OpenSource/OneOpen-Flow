from __future__ import annotations

import hashlib
import hmac
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.core.config import get_settings


class StorageService:
    """Local filesystem storage with an S3-compatible abstraction surface."""

    def __init__(self) -> None:
        settings = get_settings()
        self.backend = settings.storage_backend
        self.root = Path(settings.storage_local_path).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "artifacts").mkdir(exist_ok=True)
        (self.root / "workspaces").mkdir(exist_ok=True)
        (self.root / "evidence").mkdir(exist_ok=True)

    def save_bytes(
        self,
        *,
        relative_path: str,
        data: bytes,
        content_type: str | None = None,
    ) -> str:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def save_text(self, *, relative_path: str, text: str) -> str:
        return self.save_bytes(relative_path=relative_path, data=text.encode("utf-8"))

    def read_bytes(self, path: str) -> bytes:
        return Path(path).read_bytes()

    def create_workspace(self, run_id: UUID, node_id: str) -> Path:
        path = self.root / "workspaces" / str(run_id) / node_id / str(uuid4())
        path.mkdir(parents=True, exist_ok=True)
        return path

    def cleanup_workspace(self, path: Path) -> None:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

    def build_evidence_zip(self, run_id: UUID, manifest: dict[str, Any], files: list[Path]) -> Path:
        evidence_dir = self.root / "evidence" / str(run_id)
        evidence_dir.mkdir(parents=True, exist_ok=True)
        zip_path = evidence_dir / "evidence-package.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2, default=str))
            for file_path in files:
                if file_path.exists():
                    zf.write(file_path, arcname=f"artifacts/{file_path.name}")
        return zip_path


def sign_job_payload(payload: dict[str, Any], secret: str) -> str:
    body = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify_job_signature(payload: dict[str, Any], signature: str, secret: str) -> bool:
    expected = sign_job_payload(payload, secret)
    return hmac.compare_digest(expected, signature)
