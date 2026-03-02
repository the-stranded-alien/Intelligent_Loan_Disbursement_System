from config.settings import settings


class StorageService:
    """Abstraction over local filesystem and S3 storage."""

    async def upload(self, file_bytes: bytes, filename: str, content_type: str) -> str:
        # TODO: Save to local path or upload to S3, return URL/path
        pass

    async def download(self, path: str) -> bytes:
        # TODO: Read from local path or download from S3
        pass

    async def delete(self, path: str) -> bool:
        # TODO: Delete file from storage
        pass


storage_service = StorageService()
