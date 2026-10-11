import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

from app.core.config import Settings
from app.core.security import create_access_token, get_jwks
from app.main import app


class JwksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")
        cls.public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")
        cls.settings = Settings(
            ALGORITHM="RS256",
            JWT_KEY_ID="test-key-1",
            JWT_PRIVATE_KEY=cls.private_pem,
            JWT_PUBLIC_KEY=cls.public_pem,
            JWT_ISSUER="moaje-auth",
            JWT_AUDIENCE="moaje-gateway",
        )

    def test_access_token_has_kid_and_is_verifiable_with_public_key(self):
        token, _ = create_access_token("123", settings=self.settings)

        self.assertEqual(jwt.get_unverified_header(token)["kid"], "test-key-1")
        payload = jwt.decode(
            token,
            self.public_pem,
            algorithms=["RS256"],
            issuer="moaje-auth",
            audience="moaje-gateway",
        )
        self.assertEqual(payload["sub"], "123")

    def test_jwks_exposes_matching_rsa_public_key(self):
        jwks = get_jwks(settings=self.settings)

        self.assertEqual(len(jwks["keys"]), 1)
        self.assertEqual(
            {key: jwks["keys"][0][key] for key in ("kty", "use", "alg", "kid")},
            {"kty": "RSA", "use": "sig", "alg": "RS256", "kid": "test-key-1"},
        )
        self.assertTrue(jwks["keys"][0]["n"])
        self.assertEqual(jwks["keys"][0]["e"], "AQAB")

    def test_public_jwks_endpoint_is_registered(self):
        operation = app.openapi()["paths"]["/.well-known/jwks.json"]["get"]
        self.assertNotIn("security", operation)

    def test_keys_can_be_loaded_from_mounted_files(self):
        with TemporaryDirectory() as directory:
            private_path = Path(directory, "private.pem")
            public_path = Path(directory, "public.pem")
            private_path.write_text(self.private_pem, encoding="utf-8")
            public_path.write_text(self.public_pem, encoding="utf-8")
            settings = self.settings.model_copy(
                update={
                    "jwt_private_key": None,
                    "jwt_public_key": None,
                    "jwt_private_key_file": str(private_path),
                    "jwt_public_key_file": str(public_path),
                }
            )

            token, _ = create_access_token("123", settings=settings)

            self.assertEqual(jwt.get_unverified_header(token)["kid"], "test-key-1")
            self.assertEqual(get_jwks(settings=settings)["keys"][0]["kid"], "test-key-1")


if __name__ == "__main__":
    unittest.main()
