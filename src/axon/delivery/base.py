from __future__ import annotations

from abc import ABC, abstractmethod

from axon.models import Digest


class DeliveryBackend(ABC):
    """Abstract base class for delivery backends."""

    @abstractmethod
    def deliver(self, digest: Digest) -> str:
        """Deliver the digest. Returns a status/path description."""
        ...
