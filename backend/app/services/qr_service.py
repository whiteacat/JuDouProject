"""活动二维码生成。

优先级：
1. 服务器配置了 WECHAT_APPID/WECHAT_SECRET 时，调用微信 getwxacode
   生成真实小程序码（path 携带活动 id + 邀请参数，扫码直达落地链路）
2. 凭证缺失或调用失败时，降级为普通 URL 二维码（内容为活动详情 H5 占位链接），
   保证海报功能不中断；配置凭证后自动升级为小程序码。
"""

from __future__ import annotations

import io

import httpx
import qrcode

from app.core.config import get_settings

# 降级二维码的落地页占位（H5 版未开发前仅作海报展示）
FALLBACK_BASE = "https://judou.example.com/share"


async def _get_access_token() -> str | None:
    """获取微信 access_token；凭证未配置返回 None。"""
    settings = get_settings()
    if not settings.wechat_appid or not settings.wechat_secret:
        return None
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://api.weixin.qq.com/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": settings.wechat_appid,
                "secret": settings.wechat_secret,
            },
        )
        data = resp.json()
        return data.get("access_token")


async def event_qrcode_png(event_id: int, invite_code: str = "", group_name: str = "") -> bytes:
    """生成活动二维码 PNG 字节流。"""
    path = f"pages/event/detail/index"
    params = [f"id={event_id}", "invite=1"]
    if invite_code:
        params.append(f"code={invite_code}")
    if group_name:
        params.append(f"gname={group_name}")
    page_path = f"{path}?{'&'.join(params)}"

    token = await _get_access_token()
    if token:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"https://api.weixin.qq.com/wxa/getwxacodeunlimit?access_token={token}",
                    json={
                        "scene": f"id={event_id}",
                        "page": "pages/event/detail/index",
                        "width": 280,
                        "check_path": False,
                    },
                )
                content_type = resp.headers.get("content-type", "")
                if "image" in content_type:
                    return resp.content
            # 非图片响应（凭证过期等）落到降级
        except httpx.HTTPError:
            pass

    # 降级：URL 二维码
    url = f"{FALLBACK_BASE}/{event_id}?{'&'.join(params[1:])}"
    img = qrcode.make(url, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
