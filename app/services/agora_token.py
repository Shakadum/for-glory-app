import base64
import binascii
import hashlib
import hmac
import os
import random
import struct
import time
from dataclasses import dataclass
from typing import Dict, Optional

# Agora RTC token builder (compatible with Agora's "006" token format).
# Implemented inline to avoid extra dependencies.
#
# References: Agora official token builder samples (AccessToken2 style).

VERSION = "006"


def _pack_uint16(x: int) -> bytes:
    return struct.pack("<H", int(x))


def _pack_uint32(x: int) -> bytes:
    return struct.pack("<I", int(x))


def _crc32(data: bytes) -> int:
    return binascii.crc32(data) & 0xFFFFFFFF


def _pack_string(s: str) -> bytes:
    b = s.encode("utf-8")
    return _pack_uint16(len(b)) + b


def _pack_map_uint32(m: Dict[int, int]) -> bytes:
    # map<uint16, uint32> in little-endian, with uint16 size prefix
    out = bytearray()
    out.extend(_pack_uint16(len(m)))
    for k, v in m.items():
        out.extend(_pack_uint16(int(k)))
        out.extend(_pack_uint32(int(v)))
    return bytes(out)


@dataclass
class RtcTokenOptions:
    app_id: str
    app_cert: str
    channel: str
    uid: str  # Agora accepts int uid (0..2^32-1) OR userAccount string; we'll use string userAccount
    expire_seconds: int = 3600
    # 1 = join, 2 = publish audio, 3 = publish video, 4 = publish data stream
    privileges: Optional[Dict[int, int]] = None
    salt: Optional[int] = None


def build_rtc_token(opts: RtcTokenOptions) -> str:
    if not opts.app_id or not opts.app_cert:
        raise ValueError("app_id and app_cert are required")
    if not opts.channel:
        raise ValueError("channel is required")
    uid = str(opts.uid)

    now = int(time.time())
    expire_ts = now + int(opts.expire_seconds)
    privileges = opts.privileges or {1: expire_ts, 2: expire_ts, 3: expire_ts, 4: expire_ts}
    salt = opts.salt if opts.salt is not None else random.randint(1, 99999999)

    # Message: salt + ts + privileges
    msg = bytearray()
    msg.extend(_pack_uint32(salt))
    msg.extend(_pack_uint32(expire_ts))
    msg.extend(_pack_map_uint32(privileges))

    # Sign: HMAC-SHA256(appCert, appId + channel + uid + msg)
    sign_input = bytearray()
    sign_input.extend(opts.app_id.encode("utf-8"))
    sign_input.extend(opts.channel.encode("utf-8"))
    sign_input.extend(uid.encode("utf-8"))
    sign_input.extend(msg)
    signature = hmac.new(opts.app_cert.encode("utf-8"), sign_input, hashlib.sha256).digest()

    # Content: signature + crc(channel) + crc(uid) + msg
    content = bytearray()
    content.extend(_pack_uint16(len(signature)))
    content.extend(signature)
    content.extend(_pack_uint32(_crc32(opts.channel.encode("utf-8"))))
    content.extend(_pack_uint32(_crc32(uid.encode("utf-8"))))
    content.extend(_pack_uint16(len(msg)))
    content.extend(msg)

    return f"{VERSION}{opts.app_id}{base64.b64encode(content).decode('utf-8')}"
