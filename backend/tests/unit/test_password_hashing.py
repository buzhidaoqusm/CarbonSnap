"""Tests hash passwords cheaply; the application keeps scrypt.

scrypt is slow on purpose, ~0.3 s per hash on a laptop and over 1 s under
load, and user fixtures hash a password each: it was 86% of the forum
tests' run time.
"""

from __future__ import annotations

import time

from werkzeug.security import check_password_hash, generate_password_hash


def test_password_hashing_is_cheap_in_tests():
    started = time.perf_counter()
    hashed = generate_password_hash("password123")
    elapsed = time.perf_counter() - started

    assert hashed.startswith("pbkdf2:sha256:1$")
    assert elapsed < 0.01
    assert check_password_hash(hashed, "password123")


def test_scrypt_hashes_still_verify():
    # Rows hashed before this change, or by a real deployment, still log in.
    hashed = generate_password_hash("password123", method="scrypt")

    assert hashed.startswith("scrypt:")
    assert check_password_hash(hashed, "password123")
