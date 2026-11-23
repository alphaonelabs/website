"""W3C Bitstring Status List helpers (revocation purpose)."""

import base64
import gzip

STATUS_LIST_SIZE = 131072  # bits; the spec's minimum list size for herd privacy
STATUS_LIST_PATH = "/status-lists/revocation/1"


def build_status_entry(list_url: str, index: int) -> dict:
    return {
        "id": f"{list_url}#{index}",
        "type": "BitstringStatusListEntry",
        "statusPurpose": "revocation",
        "statusListIndex": str(index),
        "statusListCredential": list_url,
    }


def encode_list(revoked_indexes, size: int = STATUS_LIST_SIZE) -> str:
    """Bit 0 is the leftmost bit of the first byte. GZIP, then multibase base64url."""
    bits = bytearray(size // 8)
    for i in revoked_indexes:
        if 0 <= i < size:
            bits[i >> 3] |= 0x80 >> (i & 7)
    packed = gzip.compress(bytes(bits), mtime=0)
    return "u" + base64.urlsafe_b64encode(packed).rstrip(b"=").decode("ascii")


def decode_list(encoded: str) -> bytes:
    if not encoded.startswith("u"):
        raise ValueError("encodedList must be multibase base64url ('u' prefix)")
    body = encoded[1:]
    return gzip.decompress(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))


def is_set(bits: bytes, index: int) -> bool:
    return bool(bits[index >> 3] & (0x80 >> (index & 7)))


def build_status_list_credential(issuer_url: str, list_url: str, encoded_list: str, issued_at: str) -> dict:
    return {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "id": list_url,
        "type": ["VerifiableCredential", "BitstringStatusListCredential"],
        "issuer": issuer_url,
        "validFrom": issued_at,
        "credentialSubject": {
            "id": f"{list_url}#list",
            "type": "BitstringStatusList",
            "statusPurpose": "revocation",
            "encodedList": encoded_list,
        },
    }

def is_set(bits: bytes, index: int) -> bool:
    if index < 0 or index >= len(bits) * 8:
        raise ValueError("status-list index out of range")

    return bool(bits[index >> 3] & (0x80 >> (index & 7)))