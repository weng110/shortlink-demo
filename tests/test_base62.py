from app.utils.base62 import decode, encode


def test_encode_specific_values():
    assert encode(0) == "0"
    assert encode(1) == "1"
    assert encode(61) == "Z"
    assert encode(62) == "10"
    assert encode(63) == "11"


def test_encode_decode_roundtrip():
    for n in [0, 1, 61, 62, 63, 3844, 123456789, 2**40]:
        assert decode(encode(n)) == n
