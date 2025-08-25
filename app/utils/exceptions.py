class RateLimitException(Exception):
    """Raised when rate limit is exceeded"""
    pass

class UserNotFoundException(Exception):
    """Raised when user is not found"""
    pass

class FileProcessingException(Exception):
    """Raised when file processing fails"""
    pass
