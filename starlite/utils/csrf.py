import hashlib
import hmac
import secrets

CSRF_SECRET_BYTES = 32


def generate_csrf_hash(token: str, secret: str) -> str:
    """Generate an HMAC that signs the CSRF token.

    Args:
        token: A hashed token.
        secret: A secret value.

    Returns:
        A CSRF hash.
    """
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def generate_csrf_token(secret: str) -> str:
    """Generate a CSRF token that includes a randomly generated string signed by an HMAC.

    Args:
        secret: A secret string.

    Returns:
        A unique CSRF token.
    """
    token = secrets.token_hex(CSRF_SECRET_BYTES)
    token_hash = generate_csrf_hash(token=token, secret=secret)
    return token + token_hash
