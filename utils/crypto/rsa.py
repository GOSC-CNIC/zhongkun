from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from .b64 import base64url_decode, base64url_encode


def generate_rsa_key(key_size: int = 2048):
    pri_rsa = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    bytes_private_key = pri_rsa.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    private_key = bytes_private_key.decode('utf-8')

    public_rsa = pri_rsa.public_key()
    bytes_public_key = public_rsa.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    public_key = bytes_public_key.decode('utf-8')

    return private_key, public_key


class SHA256WithRSA:
    def __init__(self, private_key: str = None, public_key: str = None, private_key_password: str = None):
        """
        :param private_key: encoding PEM, format PKCS8
        :param public_key: encoding PEM, format SubjectPublicKeyInfo
        :param private_key_password:
        """
        self.private_key = private_key
        self.public_key = public_key
        if private_key:
            self.private_rsa = serialization.load_pem_private_key(
                private_key.encode('utf-8'),
                password=private_key_password if private_key_password is None else private_key_password.encode('utf-8')
            )
        else:
            self.private_rsa = None

        if public_key:
            self.public_rsa = serialization.load_pem_public_key(public_key.encode('utf-8'))
        else:
            self.public_rsa = None

    def sign(self, data: bytes) -> str:
        signature = self.private_rsa.sign(
            data=data,
            padding=padding.PKCS1v15(),
            algorithm=hashes.SHA256()
        )
        signature = base64url_encode(signature)
        signature = signature.decode('utf-8')
        return signature

    def verify(self, signature: str, data: bytes):
        signature = base64url_decode(signature.encode('utf-8'))
        try:
            self.public_rsa.verify(
                signature=signature,
                data=data,
                padding=padding.PKCS1v15(),
                algorithm=hashes.SHA256()
            )
            return True
        except InvalidSignature:
            return False
