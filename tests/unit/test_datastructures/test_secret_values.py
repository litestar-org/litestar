from litestar.datastructures.secret_values import SecretBytes, SecretString


def test_secret_string_get_value() -> None:
    secret_string = SecretString("some_secret_value")
    assert secret_string.get_value() == "some_secret_value"


def test_secret_string_get_hidden_value() -> None:
    secret_string = SecretString("some_secret_value")
    assert secret_string._get_hidden_value() == SecretString._hide_value("some_secret_value")


def test_secret_string_len() -> None:
    secret_string = SecretString("some_secret_value")
    assert len(secret_string) == len("some_secret_value")


def test_secret_string_str() -> None:
    secret_string = SecretString("some_secret_value")
    assert str(secret_string) == SecretString._hide_value("some_secret_value")


def test_secret_string_repr() -> None:
    secret_string = SecretString("some_secret_value")
    assert repr(secret_string) == "SecretString('******')"


def test_secret_string_eq() -> None:
    secret_string1 = SecretString("some_secret_value")
    secret_string2 = SecretString("some_secret_value")
    secret_string3 = SecretString("other_secret")

    assert secret_string1 == secret_string2
    assert not (secret_string1 == secret_string3)


def test_secret_string_hash() -> None:
    assert isinstance(hash(SecretString("some_secret_value")), int)
    assert hash(SecretString("some_secret_value")) == hash("some_secret_value")


def test_secret_bytes_get_value() -> None:
    secret_bytes = SecretBytes(b"some_secret_value")
    assert secret_bytes.get_value() == b"some_secret_value"


def test_secret_bytes_get_hidden_value() -> None:
    secret_bytes = SecretBytes(b"some_secret_value")
    assert secret_bytes._get_hidden_value() == SecretBytes._hide_value(b"some_secret_value").encode()


def test_secret_bytes_len() -> None:
    secret_bytes = SecretBytes(b"some_secret_value")
    assert len(secret_bytes) == len(b"some_secret_value")


def test_secret_bytes_str() -> None:
    secret_bytes = SecretBytes(b"some_secret_value")
    assert str(secret_bytes) == str(b"******")


def test_secret_bytes_repr() -> None:
    secret_bytes = SecretBytes("some_secret_value")
    assert repr(secret_bytes) == "SecretBytes(b'******')"


def test_secret_bytes_eq() -> None:
    secret_bytes1 = SecretBytes("some_secret_value")
    secret_bytes2 = SecretBytes("some_secret_value")
    secret_bytes3 = SecretBytes("other_secret")

    assert secret_bytes1 == secret_bytes2
    assert not (secret_bytes1 == secret_bytes3)


def test_secret_bytes_hash() -> None:
    assert isinstance(hash(SecretBytes(b"some_secret_value")), int)
    assert hash(SecretBytes(b"some_secret_value")) == hash(b"some_secret_value")
