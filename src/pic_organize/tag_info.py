"""Pydantic model for storing media tag information."""

from typing import Any, Dict, Literal
from pydantic import BaseModel


class MediaTagInfo(BaseModel):
    """
    Stores tag information for a media file (image or video).

    Attributes:
        filename (str): Path to the media file.
        media_type (Literal["image", "video"]): Type of media.
        tags (Dict[str, Any]): Dictionary of extracted tags.
    """

    filename: str
    media_type: Literal["image", "video"]
    tags: Dict[str, Any]
