import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from core.config import settings


class StorageProvider(ABC):
    """
    Abstract interface for DPDP-compliant private object storage.
    Files are strictly private; no permanent public URLs are ever issued.
    """

    @abstractmethod
    def save_file(self, relative_path: str, data: bytes, content_type: str = "image/jpeg") -> str:
        """Saves file bytes at relative_path. Returns the relative storage path/identifier."""
        pass

    @abstractmethod
    def get_file(self, relative_path: str) -> Optional[bytes]:
        """Retrieves file bytes from storage. Returns None if not found."""
        pass

    @abstractmethod
    def delete_file(self, relative_path: str) -> bool:
        """Permanently deletes the file from storage. Returns True if deleted or did not exist."""
        pass

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        """Checks if a file exists at relative_path."""
        pass


class LocalStorageProvider(StorageProvider):
    """
    Zero-cost, offline-first private disk storage.
    Files are stored outside static web roots and served only via authenticated streaming endpoints.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.PRIVATE_STORAGE_PATH).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolves path and guards against directory traversal attacks."""
        clean_rel = relative_path.lstrip("/\\")
        target = (self.base_dir / clean_rel).resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise ValueError(f"Path traversal detected: {relative_path}")
        return target

    def save_file(self, relative_path: str, data: bytes, content_type: str = "image/jpeg") -> str:
        target = self._resolve_safe_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return relative_path

    def get_file(self, relative_path: str) -> Optional[bytes]:
        try:
            target = self._resolve_safe_path(relative_path)
            if target.exists() and target.is_file():
                return target.read_bytes()
            return None
        except ValueError:
            return None

    def delete_file(self, relative_path: str) -> bool:
        try:
            target = self._resolve_safe_path(relative_path)
            if target.exists() and target.is_file():
                target.unlink(missing_ok=True)
            return True
        except ValueError:
            return False

    def exists(self, relative_path: str) -> bool:
        try:
            target = self._resolve_safe_path(relative_path)
            return target.exists() and target.is_file()
        except ValueError:
            return False


class FirebaseStorageProvider(StorageProvider):
    """
    Cloud Storage implementation when Firebase Blaze plan and bucket are configured.
    """

    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or settings.FIREBASE_STORAGE_BUCKET
        self._bucket = None

    def _get_bucket(self):
        if not self._bucket:
            from firebase_admin import storage
            self._bucket = storage.bucket(self.bucket_name)
        return self._bucket

    def save_file(self, relative_path: str, data: bytes, content_type: str = "image/jpeg") -> str:
        bucket = self._get_bucket()
        clean_path = f"private_verifications/{relative_path.lstrip('/')}"
        blob = bucket.blob(clean_path)
        blob.upload_from_string(data, content_type=content_type)
        return relative_path

    def get_file(self, relative_path: str) -> Optional[bytes]:
        try:
            bucket = self._get_bucket()
            clean_path = f"private_verifications/{relative_path.lstrip('/')}"
            blob = bucket.blob(clean_path)
            if blob.exists():
                return blob.download_as_bytes()
            return None
        except Exception:
            return None

    def delete_file(self, relative_path: str) -> bool:
        try:
            bucket = self._get_bucket()
            clean_path = f"private_verifications/{relative_path.lstrip('/')}"
            blob = bucket.blob(clean_path)
            if blob.exists():
                blob.delete()
            return True
        except Exception:
            return False

    def exists(self, relative_path: str) -> bool:
        try:
            bucket = self._get_bucket()
            clean_path = f"private_verifications/{relative_path.lstrip('/')}"
            blob = bucket.blob(clean_path)
            return blob.exists()
        except Exception:
            return False


# Global default instance
_default_storage: Optional[StorageProvider] = None


def get_storage_provider() -> StorageProvider:
    global _default_storage
    if _default_storage is None:
        if settings.FIREBASE_STORAGE_BUCKET and not settings.USE_MOCK_FIREBASE:
            _default_storage = FirebaseStorageProvider()
        else:
            _default_storage = LocalStorageProvider()
    return _default_storage


def set_storage_provider(provider: StorageProvider) -> None:
    """Override storage provider (primarily for tests)."""
    global _default_storage
    _default_storage = provider

