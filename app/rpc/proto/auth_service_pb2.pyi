from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class ValidateAccessTokenRequest(_message.Message):
    __slots__ = ("transaction_id", "access_token", "timestamp")
    TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    ACCESS_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    transaction_id: str
    access_token: str
    timestamp: int
    def __init__(self, transaction_id: _Optional[str] = ..., access_token: _Optional[str] = ..., timestamp: _Optional[int] = ...) -> None: ...

class ValidateAccessTokenResponse(_message.Message):
    __slots__ = ("transaction_id", "is_valid", "user_id", "expires_at", "timestamp")
    TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    IS_VALID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    transaction_id: str
    is_valid: bool
    user_id: str
    expires_at: int
    timestamp: int
    def __init__(self, transaction_id: _Optional[str] = ..., is_valid: _Optional[bool] = ..., user_id: _Optional[str] = ..., expires_at: _Optional[int] = ..., timestamp: _Optional[int] = ...) -> None: ...

class CheckMfaRequiredRequest(_message.Message):
    __slots__ = ("transaction_id", "user_id", "timestamp")
    TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    transaction_id: str
    user_id: str
    timestamp: int
    def __init__(self, transaction_id: _Optional[str] = ..., user_id: _Optional[str] = ..., timestamp: _Optional[int] = ...) -> None: ...

class CheckMfaRequiredResponse(_message.Message):
    __slots__ = ("transaction_id", "is_mfa_required", "timestamp")
    TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    IS_MFA_REQUIRED_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    transaction_id: str
    is_mfa_required: bool
    timestamp: int
    def __init__(self, transaction_id: _Optional[str] = ..., is_mfa_required: _Optional[bool] = ..., timestamp: _Optional[int] = ...) -> None: ...

class ValidateAccountTokenRequest(_message.Message):
    __slots__ = ("transaction_id", "account_token", "timestamp")
    TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    transaction_id: str
    account_token: str
    timestamp: int
    def __init__(self, transaction_id: _Optional[str] = ..., account_token: _Optional[str] = ..., timestamp: _Optional[int] = ...) -> None: ...

class ValidateAccountTokenResponse(_message.Message):
    __slots__ = ("transaction_id", "is_valid", "user_id", "is_active", "timestamp")
    TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    IS_VALID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    transaction_id: str
    is_valid: bool
    user_id: str
    is_active: bool
    timestamp: int
    def __init__(self, transaction_id: _Optional[str] = ..., is_valid: _Optional[bool] = ..., user_id: _Optional[str] = ..., is_active: _Optional[bool] = ..., timestamp: _Optional[int] = ...) -> None: ...
