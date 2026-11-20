from cryptography.fernet import Fernet

from .config import TOKEN_ENCRYPTION_KEY

_fernet = Fernet(TOKEN_ENCRYPTION_KEY.encode())


def encrypt(plain: str) -> str:
    return _fernet.encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet.decrypt(token.encode()).decode()