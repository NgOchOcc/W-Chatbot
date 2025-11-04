from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import and_
from user_agents import parse as parse_ua

from weschatbot.models.user import RefreshToken
from weschatbot.utils.db import provide_session


class TokenService:
    @staticmethod
    def extract_client_info(request) -> Dict[str, Any]:
        ua_raw = request.headers.get("user-agent", "") or ""
        ua = parse_ua(ua_raw)

        xff = request.headers.get("x-forwarded-for")
        if xff:
            ip = xff.split(",")[0].strip()
        else:
            ip = request.client.host if getattr(request, "client", None) else None

        return {
            "user_agent_raw": ua_raw,
            "browser": ua.browser.family,
            "browser_version": ua.browser.version_string,
            "os": ua.os.family,
            "os_version": ua.os.version_string,
            "device": ua.device.family,
            "is_mobile": ua.is_mobile,
            "is_tablet": ua.is_tablet,
            "is_pc": ua.is_pc,
            "is_bot": ua.is_bot,
            "ip_address": ip,
            "accept_language": request.headers.get("accept-language"),
        }

    @provide_session
    def create_refresh_token_record(
            self,
            request,
            user,
            refresh_token: str,
            expires_at: Optional[datetime] = None,
            session=None,
    ):
        client_info = self.extract_client_info(request)

        rt = RefreshToken(
            token=refresh_token,
            user_agent_raw=client_info.get("user_agent_raw"),
            ip_address=client_info.get("ip_address"),
            accept_language=client_info.get("accept_language"),
            expires_at=expires_at,
            revoked=False,
            user=user,
        )

        session.add(rt)

    @staticmethod
    @provide_session
    def get_refresh_token(refresh_token: str, session=None) -> Optional[RefreshToken]:
        return session.query(RefreshToken).filter(
            and_(
                RefreshToken.token == refresh_token,
                RefreshToken.revoked.is_(False)
            )
        ).one_or_none()
