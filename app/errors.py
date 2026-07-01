class NorthStarError(Exception):
    """Base class for all our app-specific errors."""


class ExtractionError(NorthStarError):
    """Raised when we can't get text out of the PDF."""


class AnalysisError(NorthStarError):
    """Raised when the AI analysis fails or returns bad data."""