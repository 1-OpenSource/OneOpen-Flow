"""Seed demo user, secret, environment, and example workflow."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.security import encrypt_secret, hash_password
from app.db.database import SessionLocal
from app.models import Environment, Secret, User
from app.services.workflows import WorkflowService


def seed() -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "owner@oneopen.local").first()
        if not user:
            user = User(
                name="Flow Owner",
                email="owner@oneopen.local",
                password_hash=hash_password("ChangeMe123!"),
                role="owner",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        if not db.query(Secret).filter(Secret.name == "LOGIN_PASSWORD").first():
            db.add(
                Secret(
                    name="LOGIN_PASSWORD",
                    description="Demo login password",
                    encrypted_value=encrypt_secret("demo-password"),
                    created_by=user.id,
                )
            )

        if not db.query(Environment).filter(Environment.name == "local").first():
            db.add(
                Environment(
                    name="local",
                    description="Local development",
                    variables={
                        "baseUrl": "http://localhost:3000",
                        "healthEndpoint": "/health",
                        "applicationType": "react",
                    },
                    created_by=user.id,
                )
            )
        db.commit()

        example_path = Path(__file__).resolve().parents[3] / "examples" / "build-start-validate.json"
        if not example_path.exists():
            example_path = Path("/examples/build-start-validate.json")
        if example_path.exists():
            definition = json.loads(example_path.read_text(encoding="utf-8"))
            existing = [
                w
                for w in WorkflowService(db).list_workflows()
                if w.name == definition["name"]
            ]
            if not existing:
                WorkflowService(db).create(
                    owner_id=user.id,
                    payload={
                        "name": definition["name"],
                        "description": definition.get("description"),
                        "definition": definition,
                        "tags": definition.get("tags") or [],
                        "trigger_type": definition.get("trigger_type") or "manual",
                    },
                )
        print("Seed completed: owner@oneopen.local / ChangeMe123!")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
