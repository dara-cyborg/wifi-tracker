from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
import os

router = APIRouter()

static_path = os.path.join(os.path.dirname(__file__), "../../../frontend/static")
templates_path = os.path.join(os.path.dirname(__file__), "../../../frontend/templates")


@router.get("/")
def root(request: Request):
    from backend.business.auth_service import is_session_valid

    session_cookie = request.cookies.get("session")
    if is_session_valid(session_cookie):
        return RedirectResponse(url="/admin", status_code=302)
    return RedirectResponse(url="/admin/login", status_code=302)


@router.get("/.env")
def env_honeypot(request: Request):
    fake_env = "\n".join([
        "# got you lol",
        "ADMIN_USERNAME=admin_user",
        "ADMIN_PASSWORD=lmao_you_thought",
        "SECRET_KEY=nice_try_bestie",
        "DATABASE_URL=postgres://loser:loser@localhost:5432/loser_db",
        "ENVIRONMENT=production",
        "AWS_SECRET_ACCESS_KEY=imagine_falling_for_this",
        "STRIPE_SECRET_KEY=gg_ez_no_re",
    ]) + "\n"
    return Response(content=fake_env, media_type="text/plain")


@router.get("/admin")
def admin_panel(request: Request):
    from backend.business.auth_service import is_session_valid

    if not is_session_valid(request.cookies.get("session")):
        return RedirectResponse(url="/admin/login", status_code=302)

    return FileResponse(os.path.join(templates_path, "index.html"))


@router.get("/admin/login")
def login_page():
    return FileResponse(os.path.join(templates_path, "login.html"))
