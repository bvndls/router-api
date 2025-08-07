from enum import Enum


class ErrorCode(Enum):
    """Error codes for better error categorization"""

    CREDENTIALS_NOT_FOUND = "CREDENTIALS_NOT_FOUND"
    GOOGLE_SHEET_ACCESS_ERROR = "GOOGLE_SHEET_ACCESS_ERROR"
    MAC_ADDRESS_NOT_FOUND = "MAC_ADDRESS_NOT_FOUND"
    USER_CREATION_FAILED = "USER_CREATION_FAILED"
    VLESS_LINK_RETRIEVAL_FAILED = "VLESS_LINK_RETRIEVAL_FAILED"
    INVALID_MAC_ADDRESS = "INVALID_MAC_ADDRESS"
    REMNA_API_ERROR = "REMNA_API_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


class VlessCreationException(Exception):
    """Base exception for VlessCreation"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        status_code: int = 500,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


class CredentialsError(VlessCreationException):
    """Raised when credentials file is not found or invalid"""

    def __init__(
        self,
        message: str,
    ):
        super().__init__(
            message,
            ErrorCode.CREDENTIALS_NOT_FOUND,
            500,
        )


class GoogleSheetError(VlessCreationException):
    """Raised when Google Sheet operations fail"""

    def __init__(
        self,
        message: str,
    ):
        super().__init__(
            message,
            ErrorCode.GOOGLE_SHEET_ACCESS_ERROR,
            500,
        )


class MacAddressError(VlessCreationException):
    """Raised when MAC address is invalid or not found"""

    def __init__(
        self,
        message: str,
        not_found: bool = False,
    ):
        error_code = (
            ErrorCode.MAC_ADDRESS_NOT_FOUND
            if not_found
            else ErrorCode.INVALID_MAC_ADDRESS
        )
        status_code = 404 if not_found else 400
        super().__init__(
            message,
            error_code,
            status_code,
        )


class RemnaApiError(VlessCreationException):
    """Raised when Remna API operations fail"""

    def __init__(
        self,
        message: str,
        operation: str,
    ):
        if operation == "create_user":
            error_code = ErrorCode.USER_CREATION_FAILED
        elif operation == "get_vless":
            error_code = ErrorCode.VLESS_LINK_RETRIEVAL_FAILED
        else:
            error_code = ErrorCode.REMNA_API_ERROR
        super().__init__(
            message,
            error_code,
            502,
        )


class ConfigurationError(VlessCreationException):
    """Raised when configuration is invalid"""

    def __init__(self, message: str):
        super().__init__(
            message,
            ErrorCode.CONFIGURATION_ERROR,
            500,
        )
