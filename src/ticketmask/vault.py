"""Encrypted store for the surrogate -> original mapping.

This file is the sensitive half of the system. The masked corpus is safe to
hand to a model; the vault is not. They should not live on the same disk in
production, and the key should come from a KMS rather than an env var.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path

from cryptography.fernet import Fernet


@dataclass
class VaultEntry:
    surrogate: str          # "<PERSON_1>"
    original: str           # "Maria Gonzalez"
    entity_type: str        # "PERSON"
    score: float            # detector confidence at mask time
    occurrences: int = 1    # how many times it appeared in the document


class DocumentVault:
    """The reverse map for a single ticket.

    Scoped per document deliberately. A global surrogate space would let
    someone correlate <PERSON_7> across thousands of tickets, which rebuilds
    exactly the linkage we are trying to break.
    """

    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        self._by_surrogate: dict[str, VaultEntry] = {}
        self._by_original: dict[tuple[str, str], str] = {}  # (type, original) -> surrogate
        self._counters: dict[str, int] = {}

    def surrogate_for(self, original: str, entity_type: str, score: float) -> str:
        """Return a stable surrogate, minting a new one only for unseen values."""
        key = (entity_type, original)
        if key in self._by_original:
            surrogate = self._by_original[key]
            self._by_surrogate[surrogate].occurrences += 1
            return surrogate

        self._counters[entity_type] = self._counters.get(entity_type, 0) + 1
        # Typed, obviously-synthetic placeholders rather than realistic fake
        # names. If one ever survives into a published KB article it reads as a
        # visible bug; a plausible fake name would read as a real customer.
        surrogate = f"<{entity_type}_{self._counters[entity_type]}>"

        self._by_surrogate[surrogate] = VaultEntry(surrogate, original, entity_type, score)
        self._by_original[key] = surrogate
        return surrogate

    def alias(self, original: str, entity_type: str, surrogate: str) -> None:
        """Point a variant spelling at an existing surrogate (see linker.py)."""
        self._by_original[(entity_type, original)] = surrogate

    def original_for(self, surrogate: str) -> str | None:
        entry = self._by_surrogate.get(surrogate)
        return entry.original if entry else None

    @property
    def entries(self) -> list[VaultEntry]:
        return list(self._by_surrogate.values())

    # --- persistence ------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "entries": [asdict(e) for e in self._by_surrogate.values()],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> DocumentVault:
        vault = cls(payload["doc_id"])
        for raw in payload["entries"]:
            entry = VaultEntry(**raw)
            vault._by_surrogate[entry.surrogate] = entry
            vault._by_original[(entry.entity_type, entry.original)] = entry.surrogate
        return vault


class VaultStore:
    """Fernet-encrypted vault files on disk. One file per document."""

    def __init__(self, directory: str | Path | None = None, key: str | None = None):
        self.directory = Path(directory or os.environ.get("TICKETMASK_VAULT_DIR", "./vault"))
        raw_key = key or os.environ.get("TICKETMASK_VAULT_KEY")
        if not raw_key:
            raise RuntimeError(
                "TICKETMASK_VAULT_KEY is not set. Generate one with:\n"
                '  python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            )
        self._fernet = Fernet(raw_key.encode() if isinstance(raw_key, str) else raw_key)

    def _path(self, doc_id: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in doc_id)
        return self.directory / f"{safe}.vault"

    def save(self, vault: DocumentVault) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        blob = self._fernet.encrypt(json.dumps(vault.to_dict()).encode("utf-8"))
        path = self._path(vault.doc_id)
        path.write_bytes(blob)
        return path

    def load(self, doc_id: str) -> DocumentVault:
        blob = self._path(doc_id).read_bytes()
        return DocumentVault.from_dict(json.loads(self._fernet.decrypt(blob)))
