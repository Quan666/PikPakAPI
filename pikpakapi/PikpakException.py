class PikpakException(Exception):
    def __init__(self, message):
        super().__init__(message)


class PikpakAccessTokenExpireException(Exception):
    def __init__(self, message):
        super().__init__(
            f"access_token expire, {message}, please refresh_access_token or login"
        )
