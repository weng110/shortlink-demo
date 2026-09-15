"""Base62 编码：把十进制 ID 转为短码。

原理：62 个字符（0-9a-zA-Z）表示 62 进制。
ID=1  -> "1"
ID=62 -> "10"
ID=63 -> "11"
"""

CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(CHARS)  # 62


def encode(num: int) -> str:
    """十进制 -> Base62 短码。"""
    if num == 0:
        return CHARS[0]
    sb = []
    while num > 0:
        num, rem = divmod(num, BASE)
        sb.append(CHARS[rem])
    return "".join(reversed(sb))


def decode(code: str) -> int:
    """Base62 短码 -> 十进制。"""
    num = 0
    for ch in code:
        num = num * BASE + CHARS.index(ch)
    return num
