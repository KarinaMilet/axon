from __future__ import annotations

from axon.delivery.base import DeliveryBackend
from axon.models import Digest


def create_backends(config: dict) -> list[DeliveryBackend]:
    """Create delivery backends based on config."""
    formats = config.get("delivery", {}).get("formats", ["markdown"])
    backends: list[DeliveryBackend] = []

    for fmt in formats:
        if fmt == "markdown":
            from axon.delivery.markdown import MarkdownBackend

            backends.append(MarkdownBackend(config))
        else:
            raise ValueError(f"Unknown delivery format: {fmt}")

    return backends


def deliver_all(digest: Digest, config: dict) -> list[str]:
    """Deliver digest via all configured backends. Returns list of status strings."""
    backends = create_backends(config)
    return [b.deliver(digest) for b in backends]


__all__ = ["DeliveryBackend", "create_backends", "deliver_all"]
