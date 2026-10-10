"""Compatibility entry point for the provider-neutral vision service."""
from app.services.vision import analyze_images


def analyze_image(data: bytes, mime_type: str):
    return analyze_images([(data, mime_type)], "drone", None, None)
