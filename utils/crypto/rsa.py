import base64

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature


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
            self.private_rsa = self.load_pem_private_key(
                private_key=private_key, private_key_password=private_key_password)
        else:
            self.private_rsa = None

        if public_key:
            self.public_rsa = self.load_pem_public_key(public_key=public_key)
        else:
            self.public_rsa = None

    def sign(self, data: bytes) -> str:
        return self._sign(private_rsa=self.private_rsa, data=data)

    @staticmethod
    def _sign(private_rsa, data: bytes) -> str:
        signature = private_rsa.sign(
            data=data,
            padding=padding.PKCS1v15(),
            algorithm=hashes.SHA256()
        )
        signature = base64.b64encode(signature)
        signature = signature.decode('utf-8')
        return signature

    def verify(self, signature: str, data: bytes):
        return self._verify(public_rsa=self.public_rsa, signature=signature, data=data)

    @staticmethod
    def _verify(public_rsa, signature: str, data: bytes):
        signature = base64.b64decode(signature.encode('utf-8'))
        try:
            public_rsa.verify(
                signature=signature,
                data=data,
                padding=padding.PKCS1v15(),
                algorithm=hashes.SHA256()
            )
            return True
        except InvalidSignature:
            return False

    @staticmethod
    def load_pem_private_key(private_key: str, private_key_password: str = None) -> rsa.RSAPrivateKey:
        return serialization.load_pem_private_key(
            private_key.encode('utf-8'),
            password=private_key_password if private_key_password is None else private_key_password.encode('utf-8')
        )

    @staticmethod
    def load_pem_public_key(public_key: str) -> rsa.RSAPublicKey:
        return serialization.load_pem_public_key(public_key.encode('utf-8'))

    @staticmethod
    def is_key_pair_match(private_key: str, public_key: str, private_key_password: str = None) -> bool:
        """
        是否是一对匹配的密钥对
        """
        try:
            pri_key = SHA256WithRSA.load_pem_private_key(
                private_key=private_key, private_key_password=private_key_password)
            pub_key = SHA256WithRSA.load_pem_public_key(public_key=public_key)
        except Exception as exc:
            return False

        signature = SHA256WithRSA._sign(private_rsa=pri_key, data=b'test')
        return SHA256WithRSA._verify(public_rsa=pub_key, signature=signature, data=b'test')
