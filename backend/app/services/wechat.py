"""微信开放接口客户端。"""

import httpx

from app.core.config import get_settings

WECHAT_CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


class WechatClient:
    """封装微信 code2session 登录接口。

    未配置 WECHAT_APPID / WECHAT_SECRET 时进入 mock 模式：
    openid 由登录 code 派生，便于本地多账号联调与 CI。
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    async def code2session(self, code: str) -> dict:
        if not self.settings.wechat_enabled:
            return self._mock_session(code)

        params = {
            "appid": self.settings.wechat_appid,
            "secret": self.settings.wechat_secret,
            "js_code": code,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(WECHAT_CODE2SESSION_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        if "errcode" in data and data["errcode"] != 0:
            raise ValueError(f"wechat code2session failed: {data}")
        return data

    def _mock_session(self, code: str) -> dict:
        return {
            "openid": f"mock_openid_{code}",
            "session_key": "mock-session-key",
            "unionid": None,
        }
