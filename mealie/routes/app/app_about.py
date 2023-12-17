from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm.session import Session

from mealie.core.config import get_app_settings
from mealie.core.settings.static import APP_VERSION
from mealie.db.db_setup import generate_session
from mealie.db.models.users.users import User
from mealie.schema.admin.about import AppInfo, AppStartupInfo, AppTheme, OIDCInfo

router = APIRouter(prefix="/about")


@router.get("", response_model=AppInfo)
def get_app_info():
    """Get general application information"""
    settings = get_app_settings()

    return AppInfo(
        version=APP_VERSION,
        demo_status=settings.IS_DEMO,
        production=settings.PRODUCTION,
        allow_signup=settings.ALLOW_SIGNUP,
        enable_oidc=settings.OIDC_READY,
    )


@router.get("/startup-info", response_model=AppStartupInfo)
def get_startup_info(session: Session = Depends(generate_session)):
    """returns helpful startup information"""
    settings = get_app_settings()

    is_first_login = False
    with session as db:
        if db.query(User).filter_by(email=settings._DEFAULT_EMAIL).count() > 0:
            is_first_login = True

    return AppStartupInfo(
        is_first_login=is_first_login,
    )


@router.get("/theme", response_model=AppTheme)
def get_app_theme(resp: Response):
    """Get's the current theme settings"""
    settings = get_app_settings()

    resp.headers["Cache-Control"] = "public, max-age=604800"
    return AppTheme(**settings.theme.dict())


@router.get("/oidc", response_model=OIDCInfo)
def get_oidc_info(resp: Response):
    """Get's the current OIDC configuration needed for the frontend"""
    settings = get_app_settings()

    resp.headers["Cache-Control"] = "public, max-age=604800"
    return OIDCInfo(configuration_url=settings.OIDC_CONFIGURATION_URL, client_id=settings.OIDC_CLIENT_ID)
