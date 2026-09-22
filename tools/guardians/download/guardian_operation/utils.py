from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization


# asymmetric encryption/decryption
class AsymmetricEncryption:
    def __init__(self):
        self.padding = padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        )

    def encrypt(self, public_key_pem: bytes, data_bytes: bytes) -> bytes:
        try:
            public_key_obj = serialization.load_pem_public_key(public_key_pem)
            encrypted_data = public_key_obj.encrypt(data_bytes, padding=self.padding)
            return encrypted_data
        except Exception as e:
            raise RuntimeError(f"Data encryption failed: {str(e)}")

    def decrypt(self, private_key_bytes: bytes, encrypted_data_bytes: bytes) -> bytes:
        try:
            private_key = serialization.load_pem_private_key(
                data=private_key_bytes, password=None
            )
            data_bytes = private_key.decrypt(encrypted_data_bytes, padding=self.padding)
            return data_bytes
        except Exception as e:
            raise RuntimeError(f"Data decryption failed: {str(e)}")
