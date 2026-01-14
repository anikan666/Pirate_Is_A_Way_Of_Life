"""
Storage abstraction layer for audio files.
Supports both local filesystem and AWS S3 storage.
"""

import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional, BinaryIO


class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    def save_file(self, filename: str, content: bytes) -> bool:
        """Save file content to storage"""
        pass
    
    @abstractmethod
    def get_file(self, filename: str) -> Optional[bytes]:
        """Get file content from storage"""
        pass
    
    @abstractmethod
    def delete_file(self, filename: str) -> bool:
        """Delete file from storage"""
        pass
    
    @abstractmethod
    def rename_file(self, old_name: str, new_name: str) -> bool:
        """Rename a file in storage"""
        pass
    
    @abstractmethod
    def list_files(self, exclude_prefix: str = None) -> List[Dict]:
        """List all files in storage"""
        pass
    
    @abstractmethod
    def file_exists(self, filename: str) -> bool:
        """Check if file exists"""
        pass
    
    @abstractmethod
    def get_file_url(self, filename: str) -> Optional[str]:
        """Get URL/path to access file"""
        pass


class LocalStorage(StorageBackend):
    """Local filesystem storage backend"""
    
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
    
    def _get_path(self, filename: str) -> str:
        return os.path.join(self.base_dir, filename)
    
    def save_file(self, filename: str, content: bytes) -> bool:
        try:
            filepath = self._get_path(filename)
            with open(filepath, 'wb') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"LocalStorage save error: {e}")
            return False
    
    def get_file(self, filename: str) -> Optional[bytes]:
        try:
            filepath = self._get_path(filename)
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    return f.read()
            return None
        except Exception as e:
            print(f"LocalStorage get error: {e}")
            return None
    
    def delete_file(self, filename: str) -> bool:
        try:
            filepath = self._get_path(filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception as e:
            print(f"LocalStorage delete error: {e}")
            return False
    
    def rename_file(self, old_name: str, new_name: str) -> bool:
        try:
            old_path = self._get_path(old_name)
            new_path = self._get_path(new_name)
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
                return True
            return False
        except Exception as e:
            print(f"LocalStorage rename error: {e}")
            return False
    
    def list_files(self, exclude_prefix: str = None) -> List[Dict]:
        files = []
        try:
            for filename in os.listdir(self.base_dir):
                if exclude_prefix and filename.startswith(exclude_prefix):
                    continue
                if filename.endswith(('.mp3', '.wav')):
                    filepath = self._get_path(filename)
                    files.append({
                        'filename': filename,
                        'size': os.path.getsize(filepath),
                        'created': os.path.getctime(filepath)
                    })
            files.sort(key=lambda x: x['created'], reverse=True)
        except Exception as e:
            print(f"LocalStorage list error: {e}")
        return files
    
    def file_exists(self, filename: str) -> bool:
        return os.path.exists(self._get_path(filename))
    
    def get_file_url(self, filename: str) -> Optional[str]:
        """For local storage, return the API path"""
        if self.file_exists(filename):
            return f"/api/play/{filename}"
        return None
    
    def get_file_path(self, filename: str) -> Optional[str]:
        """Get the actual file path (local storage only)"""
        filepath = self._get_path(filename)
        if os.path.exists(filepath):
            return filepath
        return None
    
    def cleanup_temp_files(self, max_age_seconds: int = 300):
        """Remove temporary files older than max_age_seconds"""
        try:
            current_time = time.time()
            for filename in os.listdir(self.base_dir):
                if filename.startswith('temp_'):
                    filepath = self._get_path(filename)
                    if current_time - os.path.getctime(filepath) > max_age_seconds:
                        os.remove(filepath)
        except Exception as e:
            print(f"LocalStorage cleanup error: {e}")


class S3Storage(StorageBackend):
    """AWS S3 storage backend"""
    
    def __init__(self, bucket_name: str, region: str = None, 
                 aws_access_key: str = None, aws_secret_key: str = None,
                 prefix: str = "audio/"):
        try:
            import boto3
            from botocore.config import Config
            
            self.bucket_name = bucket_name
            self.prefix = prefix
            
            # Configure boto3 client
            config = Config(
                signature_version='s3v4',
                retries={'max_attempts': 3}
            )
            
            if aws_access_key and aws_secret_key:
                self.s3_client = boto3.client(
                    's3',
                    region_name=region,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key,
                    config=config
                )
            else:
                # Use default credentials (IAM role, env vars, etc.)
                self.s3_client = boto3.client(
                    's3',
                    region_name=region,
                    config=config
                )
            
            self.region = region
            self._initialized = True
        except ImportError:
            print("boto3 not installed. S3 storage unavailable.")
            self._initialized = False
        except Exception as e:
            print(f"S3 initialization error: {e}")
            self._initialized = False
    
    def _get_key(self, filename: str) -> str:
        return f"{self.prefix}{filename}"
    
    def save_file(self, filename: str, content: bytes) -> bool:
        if not self._initialized:
            return False
        try:
            key = self._get_key(filename)
            content_type = 'audio/mpeg' if filename.endswith('.mp3') else 'audio/wav'
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                ContentType=content_type
            )
            return True
        except Exception as e:
            print(f"S3 save error: {e}")
            return False
    
    def get_file(self, filename: str) -> Optional[bytes]:
        if not self._initialized:
            return None
        try:
            key = self._get_key(filename)
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return response['Body'].read()
        except Exception as e:
            print(f"S3 get error: {e}")
            return None
    
    def delete_file(self, filename: str) -> bool:
        if not self._initialized:
            return False
        try:
            key = self._get_key(filename)
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except Exception as e:
            print(f"S3 delete error: {e}")
            return False
    
    def rename_file(self, old_name: str, new_name: str) -> bool:
        if not self._initialized:
            return False
        try:
            old_key = self._get_key(old_name)
            new_key = self._get_key(new_name)
            
            # Copy to new key
            self.s3_client.copy_object(
                Bucket=self.bucket_name,
                CopySource={'Bucket': self.bucket_name, 'Key': old_key},
                Key=new_key
            )
            
            # Delete old key
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=old_key
            )
            return True
        except Exception as e:
            print(f"S3 rename error: {e}")
            return False
    
    def list_files(self, exclude_prefix: str = None) -> List[Dict]:
        if not self._initialized:
            return []
        files = []
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=self.prefix):
                for obj in page.get('Contents', []):
                    filename = obj['Key'].replace(self.prefix, '')
                    
                    if exclude_prefix and filename.startswith(exclude_prefix):
                        continue
                    
                    if filename.endswith(('.mp3', '.wav')):
                        files.append({
                            'filename': filename,
                            'size': obj['Size'],
                            'created': obj['LastModified'].timestamp()
                        })
            files.sort(key=lambda x: x['created'], reverse=True)
        except Exception as e:
            print(f"S3 list error: {e}")
        return files
    
    def file_exists(self, filename: str) -> bool:
        if not self._initialized:
            return False
        try:
            key = self._get_key(filename)
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except:
            return False
    
    def get_file_url(self, filename: str) -> Optional[str]:
        """Generate a presigned URL for temporary access"""
        if not self._initialized:
            return None
        try:
            key = self._get_key(filename)
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=3600  # URL valid for 1 hour
            )
            return url
        except Exception as e:
            print(f"S3 URL generation error: {e}")
            return None
    
    def cleanup_temp_files(self, max_age_seconds: int = 300):
        """Remove temporary files older than max_age_seconds"""
        if not self._initialized:
            return
        try:
            current_time = time.time()
            files = self.list_files()
            for file in files:
                if file['filename'].startswith('temp_'):
                    if current_time - file['created'] > max_age_seconds:
                        self.delete_file(file['filename'])
        except Exception as e:
            print(f"S3 cleanup error: {e}")


def get_storage_backend() -> StorageBackend:
    """
    Factory function to get the appropriate storage backend.
    Checks environment variables to determine which backend to use.
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    storage_type = os.environ.get('STORAGE_TYPE', 'local').lower()
    
    if storage_type == 's3':
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        if not bucket_name:
            print("Warning: S3_BUCKET_NAME not set, falling back to local storage")
            storage_type = 'local'
        else:
            return S3Storage(
                bucket_name=bucket_name,
                region=os.environ.get('S3_REGION', 'us-east-1'),
                aws_access_key=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                prefix=os.environ.get('S3_PREFIX', 'audio/')
            )
    
    # Default to local storage
    base_dir = os.environ.get(
        'LOCAL_STORAGE_DIR',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio_output')
    )
    return LocalStorage(base_dir)
