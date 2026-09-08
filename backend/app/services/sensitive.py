"""敏感词过滤：禁止广告、联系方式、违规昵称。

策略：
- 内置基础敏感词库（联系方式、广告关键词）
- 支持从文件或环境变量扩展词库
- 统一用 check_nickname() 返回违规原因或 None
"""

import re
from typing import Optional

# ── 联系方式正则 ──────────────────────────────────────────────
_PHONE_RE = re.compile(
    r"(?<!\d)"
    r"(?:\+?86[-\s]?)?"
    r"1[3-9]\d{9}"
    r"(?!\d)"
)
_QQ_RE = re.compile(
    r"(?:QQ|qq|扣扣|企鹅)[\s:：]?\d{5,12}"
    r"|(?<!\d)[1-9]\d{4,11}(?!\d)",
)
_WECHAT_RE = re.compile(
    r"(?:微信|wechat|wx|vx)[\s:：号IDid]{0,6}[a-zA-Z0-9_\-]{5,30}",
    re.IGNORECASE,
)
_URL_RE = re.compile(
    r"https?://|www\.|\.com|\.cn|\.net|\.org",
    re.IGNORECASE,
)

# ── 广告/引流关键词 ───────────────────────────────────────────
_AD_KEYWORDS: list[str] = [
    "代购", "微商", "加我", "加群", "私聊", "下单", "优惠券",
    "免费领", "扫码", "兼职", "日赚", "月入", "暴富", "代理",
    "招代理", "推广", "引流", "变现", "薅羊毛", "返利",
    "低价", "特价清仓", "厂家直销", "一手货源",
    "赌博", "博彩", "彩票", "网赚", "刷单",
    "色情", "约炮", "裸聊",
]

# ── 违规符号/特殊字符 ─────────────────────────────────────────
_SYMBOL_RE = re.compile(r"[\x00-\x1f\u200b-\u200f\u202a-\u202e\ufeff]")


def check_nickname(nickname: str) -> Optional[str]:
    """校验昵称是否合规。

    Returns:
        None 表示通过；否则返回违规原因字符串。
    """
    if not nickname or not nickname.strip():
        return "昵称不能为空"
    if len(nickname) > 20:
        return "昵称不能超过 20 个字符"

    # 联系方式
    if _PHONE_RE.search(nickname):
        return "昵称中不能包含手机号"
    if _QQ_RE.search(nickname):
        return "昵称中不能包含 QQ 号"
    if _WECHAT_RE.search(nickname):
        return "昵称中不能包含微信号"
    if _URL_RE.search(nickname):
        return "昵称中不能包含网址"

    # 广告关键词
    lower = nickname.lower()
    for kw in _AD_KEYWORDS:
        if kw in lower:
            return "昵称包含违规内容"

    # 控制字符
    if _SYMBOL_RE.search(nickname):
        return "昵称包含非法字符"

    return None
