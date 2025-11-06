"""
Storage Service - Abstraction layer for file storage

This module provides a storage abstraction that supports:
- Local filesystem storage (current implementation)
- AWS S3 (future)
- Sonatype Nexus (future)

To switch storage backends, implement the StorageBackend interface
and update the get_storage() function.
"""

import os
import uuid
from werkzeug.utils import secure_filename
from abc import ABC, abstractmethod
from typing import Optional, BinaryIO


class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    def save_file(self, file: BinaryIO, filename: str, folder: str = "items") -> tuple[str, str]:
        """
        Save a file to storage
        
        Args:
            file: File object to save
            filename: Original filename
            folder: Storage folder/prefix
            
        Returns:
            Tuple of (storage_path, original_filename)
        """
        pass
    
    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_file_path(self, storage_path: str) -> str:
        """
        Get the full path to a stored file
        
        Args:
            storage_path: Storage path from database
            
        Returns:
            Full path to file
        """
        pass
    
    @abstractmethod
    def file_exists(self, storage_path: str) -> bool:
        """
        Check if a file exists in storage
        
        Args:
            storage_path: Storage path from database
            
        Returns:
            True if file exists, False otherwise
        """
        pass


class LocalFileStorage(StorageBackend):
    """Local filesystem storage backend"""
    
    def __init__(self, base_upload_folder: str = "uploads"):
        self.base_upload_folder = base_upload_folder
        os.makedirs(base_upload_folder, exist_ok=True)
    
    def save_file(self, file: BinaryIO, filename: str, folder: str = "items") -> tuple[str, str]:
        """Save file to local filesystem"""
        original_filename = secure_filename(filename)
        
        extension = ""
        if "." in original_filename:
            extension = original_filename.rsplit(".", 1)[1].lower()
        
        unique_filename = f"{uuid.uuid4().hex}.{extension}" if extension else uuid.uuid4().hex
        
        folder_path = os.path.join(self.base_upload_folder, folder)
        os.makedirs(folder_path, exist_ok=True)
        
        file_path = os.path.join(folder_path, unique_filename)
        
        file.save(file_path)
        
        storage_path = os.path.join(folder, unique_filename)
        
        return storage_path, original_filename
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from local filesystem"""
        try:
            full_path = os.path.join(self.base_upload_folder, file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
            return False
    
    def get_file_path(self, storage_path: str) -> str:
        """Get full filesystem path"""
        return os.path.join(self.base_upload_folder, storage_path)
    
    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists"""
        return os.path.exists(self.get_file_path(storage_path))


class S3Storage(StorageBackend):
    """
    AWS S3 storage backend (not yet implemented)
    
    To implement:
    1. Install boto3: pip install boto3
    2. Set environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME
    3. Implement the methods below using boto3
    """
    
    def __init__(self):
        raise NotImplementedError("S3 storage backend not yet implemented")
    
    def save_file(self, file: BinaryIO, filename: str, folder: str = "items") -> tuple[str, str]:
        raise NotImplementedError()
    
    def delete_file(self, file_path: str) -> bool:
        raise NotImplementedError()
    
    def get_file_path(self, storage_path: str) -> str:
        raise NotImplementedError()
    
    def file_exists(self, storage_path: str) -> bool:
        raise NotImplementedError()


class NexusStorage(StorageBackend):
    """
    Sonatype Nexus storage backend (not yet implemented)
    
    To implement:
    1. Set environment variables: NEXUS_URL, NEXUS_USERNAME, NEXUS_PASSWORD, NEXUS_REPOSITORY
    2. Implement the methods below using Nexus REST API
    """
    
    def __init__(self):
        raise NotImplementedError("Nexus storage backend not yet implemented")
    
    def save_file(self, file: BinaryIO, filename: str, folder: str = "items") -> tuple[str, str]:
        raise NotImplementedError()
    
    def delete_file(self, file_path: str) -> bool:
        raise NotImplementedError()
    
    def get_file_path(self, storage_path: str) -> str:
        raise NotImplementedError()
    
    def file_exists(self, storage_path: str) -> bool:
        raise NotImplementedError()


def get_storage() -> StorageBackend:
    """
    Get the configured storage backend
    
    To switch storage backends:
    1. Set STORAGE_BACKEND environment variable to: 'local', 's3', or 'nexus'
    2. Configure appropriate environment variables for the backend
    
    Returns:
        StorageBackend instance
    """
    backend_type = os.environ.get("STORAGE_BACKEND", "local").lower()
    
    if backend_type == "local":
        return LocalFileStorage()
    elif backend_type == "s3":
        return S3Storage()
    elif backend_type == "nexus":
        return NexusStorage()
    else:
        raise ValueError(f"Unknown storage backend: {backend_type}")


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "doc", "docx", "txt", "csv", "xlsx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_file_size(file: BinaryIO) -> bool:
    """Check if file size is within limits"""
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    return size <= MAX_FILE_SIZE
