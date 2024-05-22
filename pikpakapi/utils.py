import hashlib
import re
import urllib.parse
from uuid import uuid4
import time

def get_timestamp() -> int:
    """
    Get current timestamp.
    """
    return int(time.time() * 1000)

def device_id_generator() -> str:
    """
    Generate a random device id.
    """
    return str(uuid4()).replace("-", "")


def l(e):
    if re.search(r"[\u0080-\uFFFF]", e):
        e = urllib.parse.unquote(urllib.parse.quote(e, encoding="utf-8"))
    return e


def b(s: str) -> str:
    s = l(s)
    return hashlib.md5(s.encode()).hexdigest()


SALTS = [
    {"alg": "md5", "salt": "C9qPpZLN8ucRTaTiUMWYS9cQvWOE"},
    {"alg": "md5", "salt": "+r6CQVxjzJV6LCV"},
    {"alg": "md5", "salt": "F"},
    {"alg": "md5", "salt": "pFJRC"},
    {"alg": "md5", "salt": "9WXYIDGrwTCz2OiVlgZa90qpECPD6olt"},
    {"alg": "md5", "salt": "/750aCr4lm/Sly/c"},
    {"alg": "md5", "salt": "RB+DT/gZCrbV"},
    {"alg": "md5", "salt": ""},
    {"alg": "md5", "salt": "CyLsf7hdkIRxRm215hl"},
    {"alg": "md5", "salt": "7xHvLi2tOYP0Y92b"},
    {"alg": "md5", "salt": "ZGTXXxu8E/MIWaEDB+Sm/"},
    {"alg": "md5", "salt": "1UI3"},
    {"alg": "md5", "salt": "E7fP5Pfijd+7K+t6Tg/NhuLq0eEUVChpJSkrKxpO"},
    {"alg": "md5", "salt": "ihtqpG6FMt65+Xk+tWUH2"},
    {"alg": "md5", "salt": "NhXXU9rg4XXdzo7u5o"},
]


def calculate_captcha_sign(e: dict, n: str) -> str:
    try:
        result = {"salt": n}
        for item in e:
            result["salt"] = b(result["salt"] + item["salt"])
            # print(result)
        return result["salt"]
    except Exception as e:
        print("[calculateCaptchaSign:]", e)
        return str(e)


def captcha_sign(device_id: str) -> str:
    """
    Generate a captcha sign.

    在网页端的js中, 搜索 captcha_sign, 可以找到对应的js代码

    """
    f = "1715937459548"
    g = "YUMx5nI8ZU8Ap8pm" + "2.0.0" + "mypikpak.com" + device_id + f
    return f"1.{calculate_captcha_sign(SALTS, g)}"
