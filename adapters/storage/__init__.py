"""Módulo de Provedores de Armazenamento de Arquivos."""
from adapters.storage.base import StorageProvider, StoredFileInfo
from adapters.storage.local_storage import LocalDiskStorageProvider
from adapters.storage.factory import StorageFactory

__all__ = [
    "StorageProvider",
    "StoredFileInfo",
    "LocalDiskStorageProvider",
    "StorageFactory"
]
