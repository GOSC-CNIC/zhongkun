from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from .b64 import base64url_decode, base64url_encode


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
