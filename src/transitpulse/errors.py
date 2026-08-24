"""Domain errors surfaced by TransitPulse."""


class TransitPulseError(Exception):
    """Base class for expected operational failures."""


class InputLoadError(TransitPulseError):
    """Raised when a local or remote feed cannot be loaded."""


class FeedParseError(TransitPulseError):
    """Raised when input is not a valid GTFS-Realtime feed."""


class StorageError(TransitPulseError):
    """Raised when the analytical store cannot complete an operation."""
