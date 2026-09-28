"""Módulo de Provedores de Armazenamento de Arquivos."""
from adapters.storage.base import StorageProvider, StoredFileInfo
from adapters.storage.drive_adapter import GoogleDriveStorageAdapter
from adapters.storage.saas_cloud_adapter import SaaSCloudBucketStorageProvider, LocalDiskStorageProvider
from adapters.storage.factory import StorageFactory

__all__ = [
    "StorageProvider",
    "StoredFileInfo",
    "GoogleDriveStorageAdapter",
    "SaaSCloudBucketStorageProvider",
    "LocalDiskStorageProvider",
    "StorageFactory"
]
