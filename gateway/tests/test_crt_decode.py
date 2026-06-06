import pytest

from crt_decode import MAX_VALUE, decode, encode


def test_crt_round_trip():
    for value in [0, 1, 42, 1234, 9000, MAX_VALUE - 1]:
        assert decode(encode(value)) == value


def test_crt_missing_residue_reconstruction():
    value = 1234
    residues = encode(value)
    residues.pop(103)
    assert decode(residues) == value


def test_crt_invalid_input():
    with pytest.raises(ValueError):
        encode(-1)
    with pytest.raises(ValueError):
        encode(MAX_VALUE)
    with pytest.raises(ValueError):
        decode({97: 1})
    with pytest.raises(ValueError):
        decode({97: 97, 101: 1})
