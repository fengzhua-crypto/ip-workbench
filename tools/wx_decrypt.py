"""视频号加密视频解密：ISAAC-64 生成密钥流，XOR 前 128KB。

背景：视频号 CDN 上的 mp4 只有**前 131072 字节**被加密，其余是明文。
密钥流 = ISAAC-64(seed=decode_key) 生成 131072 字节后**整体倒序**，
再与文件头逐字节 XOR。每次请求拿到的 decode_key 不同，必须与当次下载的文件配对。

算法按公开逆向分析实现（微信公众号/视频号下载器社区），
用测试向量与 ftyp 魔数双重自校验。

用法：
    from wx_decrypt import decrypt_file, is_decrypted
    decrypt_file(Path("enc.mp4"), "123456789")   # 原地解密
"""
from __future__ import annotations

from pathlib import Path

MASK64 = (1 << 64) - 1
WX_KEY_BYTES = 131072

# 微信版 ISAAC-64 的 8 个初始常量（与公开分析一致，不是标准 ISAAC 的黄金比）
_WX_INIT = (
    0x647C4677A2884B7C,
    0xB9F8B322C73AC862,
    0x8C0EA5053D4712A0,
    0xB29B2E824A595524,
    0x82F053DB8355E0CE,
    0x48FE4A0FA5A09315,
    0xAE985BF2CBFC89ED,
    0x98F5704F6C44C0AB,
)


def _u64(v: int) -> int:
    return v & MASK64


def _mix(values: list[int]) -> list[int]:
    a, b, c, d, e, f, g, h = values
    a = _u64(a - e); f = _u64(f ^ (h >> 9));  h = _u64(h + a)
    b = _u64(b - f); g = _u64(g ^ _u64(a << 9)); a = _u64(a + b)
    c = _u64(c - g); h = _u64(h ^ (b >> 23)); b = _u64(b + c)
    d = _u64(d - h); a = _u64(a ^ _u64(c << 15)); c = _u64(c + d)
    e = _u64(e - a); b = _u64(b ^ (d >> 14)); d = _u64(d + e)
    f = _u64(f - b); c = _u64(c ^ _u64(e << 20)); e = _u64(e + f)
    g = _u64(g - c); d = _u64(d ^ (f >> 17)); f = _u64(f + g)
    h = _u64(h - d); e = _u64(e ^ _u64(g << 14)); g = _u64(g + h)
    return [a, b, c, d, e, f, g, h]


class WxIsaac64:
    """微信 WebAssembly 模块里的 ISAAC-64 等价实现。"""

    def __init__(self, seed: int) -> None:
        self.mem = [0] * 256
        self.mem[0] = seed & MASK64
        self.a = 0
        self.b = 0
        self.c = 0
        self._init_memory()

    def _init_memory(self) -> None:
        values = list(_WX_INIT)
        for _ in range(2):
            for index in range(0, 256, 8):
                values = [_u64(values[o] + self.mem[index + o]) for o in range(8)]
                values = _mix(values)
                self.mem[index:index + 8] = values

    def _ind(self, value: int) -> int:
        return self.mem[(value & ((256 - 1) << 3)) >> 3]

    def block(self) -> list[int]:
        self.c = _u64(self.c + 1)
        a = self.a
        b = _u64(self.b + self.c)
        result = [0] * 256
        for index in range(256):
            mode = index & 3
            if mode == 0:
                mixed = _u64(~(a ^ _u64(a << 21)))
            elif mode == 1:
                mixed = _u64(a ^ (a >> 5))
            elif mode == 2:
                mixed = _u64(a ^ _u64(a << 12))
            else:
                mixed = _u64(a ^ (a >> 33))
            x = self.mem[index]
            a = _u64(mixed + self.mem[(index + 128) & 255])
            y = _u64(self._ind(x) + a + b)
            self.mem[index] = y
            b = _u64(self._ind(y >> 8) + x)
            result[index] = b
        self.a = a
        self.b = b
        return result

    def keystream(self, size: int) -> bytes:
        out = bytearray()
        while len(out) < size:
            for word in self.block():
                out.extend(word.to_bytes(8, "little"))
                if len(out) >= size:
                    break
        return bytes(out[:size])


def seed_of(decode_key: str | int) -> int:
    value = str(decode_key or "").strip()
    if not value or not value.isdigit():
        raise ValueError("decode_key 必须是十进制整数字符串")
    seed = int(value, 10)
    if seed < 0 or seed > MASK64:
        raise ValueError("decode_key 超出 uint64 范围")
    return seed


def decryption_array(decode_key: str | int, size: int = WX_KEY_BYTES) -> bytes:
    """生成解密流：ISAAC-64 输出后整体倒序（Emscripten 桥接的行为）。"""
    return WxIsaac64(seed_of(decode_key)).keystream(size)[::-1]


def decrypt_file(path: Path | str, decode_key: str | int, size: int = WX_KEY_BYTES) -> int:
    """原地解密文件前 size 字节，返回处理字节数。"""
    path = Path(path)
    key = decryption_array(decode_key, size)
    with path.open("r+b") as fh:
        chunk = fh.read(len(key))
        if not chunk:
            return 0
        fh.seek(0)
        fh.write(bytes(a ^ b for a, b in zip(chunk, key)))
        return len(chunk)


def is_decrypted(path: Path | str) -> bool:
    """文件头是不是合法 MP4（第 4-8 字节为 ftyp 盒子）。"""
    head = Path(path).read_bytes()[:12]
    return len(head) >= 12 and head[4:8] == b"ftyp"


def self_test() -> bool:
    """用公开测试向量自校验实现是否正确。"""
    g = WxIsaac64(0)
    first = g.block()
    return first[0] == 0x673F4A26E311355A and first[1] == 0x80B58CE58CF970FD


if __name__ == "__main__":
    ok = self_test()
    print("ISAAC-64 自校验：", "通过" if ok else "失败")
    if ok:
        stream = decryption_array("0", 131072)
        print(f"密钥流长度 {len(stream)}，前 8 字节 {stream[:8].hex()}")
