"""
Base class for all radar modes.
Each mode implements process() which takes raw returns and produces detections.
"""

from abc import ABC, abstractmethod
from radar_sim.models import RawReturn, Detection, RadarParams


class BaseMode(ABC):
    """
    Abstract interface for a radar processing mode.
    All modes receive the same raw returns and radar params,
    but apply different processing to produce detections.
    """

    def __init__(self, radar: RadarParams):
        self.radar = radar

    @abstractmethod
    def process(self, raw_returns: list[RawReturn]) -> list[Detection]:
        """
        Process raw returns through this mode's signal processing chain.
        Returns a list of detections.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable mode name."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of what this mode does."""
        ...
