from dataclasses import dataclass
from enum import Enum

from pandas import DataFrame
from PIL import Image as PILImage


class AttachmentTypes(Enum):
    """Enum representing the type of an attachment."""

    IMAGE = "image"
    TABLE = "table"
    CODE = "code"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class Content:
    checksum: str
    content_type: str
    data: bytes

    @classmethod
    def create(cls, data: bytes, content_type: str) -> "Content":
        """Factory method to create a Content instance with computed checksum."""
        import hashlib

        checksum = hashlib.sha256(data).hexdigest()
        return cls(checksum=checksum, content_type=content_type, data=data)

    def read(self) -> bytes:
        """Returns the raw bytes of the attachment."""
        return self.data

    @classmethod
    def from_image(cls, image: PILImage.Image, format: str = "PNG") -> "Content":
        """Returns a new Content with the given PIL image data."""
        from io import BytesIO

        buffer = BytesIO()
        image.save(buffer, format=format)
        return cls.create(
            data=buffer.getvalue(), content_type=f"image/{format.lower()}"
        )

    @classmethod
    def from_csv(cls, df: DataFrame) -> "Content":
        """Returns a new Content with the given CSV string data."""
        csv_string = df.to_csv(index=False)
        return cls.create(data=csv_string.encode("utf-8"), content_type="text/csv")

    @property
    def hash(self) -> str:
        """Returns the checksum of the content."""
        return self.checksum
