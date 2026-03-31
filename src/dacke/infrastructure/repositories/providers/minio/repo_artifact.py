"""MinIO artifact repository implementation."""

import asyncio
from datetime import timedelta
from functools import partial
from io import BytesIO

from minio import Minio
from minio.error import S3Error
from pydantic import AnyUrl

from dacke.application.ports.repository import AclLayer, Repository
from dacke.domain.values.artifact import Blob, ObjectAddress, StoragePath
from dacke.infrastructure.exceptions import (
    DatabaseConnectionError,
    DatabaseOperationError,
)


class ArtifactBlobAcl(AclLayer[Blob, Blob]):
    """Translation layer between Blob domain object and dict ORM representation."""

    @staticmethod
    def to_domain(orm: Blob) -> Blob:
        """Convert dict ORM representation to Blob domain object."""
        return orm

    @staticmethod
    def from_domain(domain: Blob) -> Blob:
        """Convert Blob domain object to dict ORM representation."""
        return domain


class ArtifactBlobRepository(Repository):
    """Repository for persisting and retrieving Artifact entities in MinIO."""

    def __init__(self, endpoint: str, access_key: str, secret_key: str) -> None:
        """Initialize MinIO client.

        Args:
            endpoint: MinIO server endpoint (e.g., 'localhost:9000')
            access_key: MinIO access key
            secret_key: MinIO secret key
        """
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self._client: Minio | None = None

    async def _connect(self) -> None:
        if self._client:
            return

        try:
            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=False,
            )
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to connect to MinIO: {e}") from e

    async def _disconnect(self) -> None:
        self._client = None

    async def ensure_bucket_exists(self, bucket_name: str) -> None:
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            exists = await asyncio.to_thread(self._client.bucket_exists, bucket_name)
            if not exists:
                await asyncio.to_thread(self._client.make_bucket, bucket_name)
        except Exception as e:
            raise DatabaseOperationError(f"Failed to ensure bucket exists: {e}") from e

    async def save_blob(self, blob: Blob) -> str:
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            await self.ensure_bucket_exists(blob.address.bucket)

            content_stream = BytesIO(blob.content)
            await asyncio.to_thread(
                self._client.put_object,
                blob.address.bucket,
                blob.address.key,
                content_stream,
                len(blob.content),
                content_type=blob.media_type,
            )

            return await self.get_presigned_url(blob.address)
        except Exception as e:
            raise DatabaseOperationError(f"Failed to save blob: {e}") from e

    async def get_blob(
        self, address: ObjectAddress, media_type: str | None = None
    ) -> Blob | None:
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            response = await asyncio.to_thread(
                self._client.get_object, address.bucket, address.key
            )
            try:
                content = await asyncio.to_thread(response.read)
            finally:
                response.close()
                response.release_conn()

            return Blob(
                address=address,
                content=content,
                media_type=media_type or "application/octet-stream",
            )
        except S3Error as e:
            if e.code == "NoSuchKey":
                return None
            raise DatabaseOperationError(f"Failed to retrieve blob: {e}") from e
        except Exception as e:
            raise DatabaseOperationError(f"Failed to retrieve blob: {e}") from e

    async def delete_blob(self, address: ObjectAddress) -> None:
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            await asyncio.to_thread(
                self._client.remove_object, address.bucket, address.key
            )
        except Exception as e:
            raise DatabaseOperationError(f"Failed to delete blob: {e}") from e

    async def get_presigned_url(
        self, address: ObjectAddress, duration_seconds: int = 3600
    ) -> AnyUrl:
        if self._client is None:
            await self._connect()
        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"
            return await asyncio.to_thread(
                self._client.presigned_get_object,
                address.bucket,
                address.key,
                expires=timedelta(seconds=duration_seconds),
            )
        except Exception as e:
            raise DatabaseOperationError(f"Failed to get presigned url: {e}") from e

    async def list_blobs_by_prefix(self, path: StoragePath) -> list[Blob]:
        if self._client is None:
            await self._connect()

        blobs = []

        try:
            assert (
                self._client is not None
            ), "Client should be initialized after connect"

            list_func = partial(
                self._client.list_objects,
                path.bucket,
                prefix=path.prefix,
                recursive=True,
            )

            objects = await asyncio.to_thread(list_func)

            for obj in objects:
                if obj is None:
                    continue

                assert isinstance(
                    obj.object_name, str
                ), "Object name should be a string"
                parts = obj.object_name.split("/")
                object_prefix = "/".join(parts[:-1])
                object_filename = parts[-1]

                address = ObjectAddress.create(
                    bucket=path.bucket,
                    prefix=object_prefix,
                    filename=object_filename,
                )

                blob = await self.get_blob(address)
                if blob is not None:
                    blobs.append(blob)

            return blobs

        except Exception as e:
            raise DatabaseOperationError(f"Failed to list blobs: {e}") from e
