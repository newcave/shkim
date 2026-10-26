"""열람 게이트와 게시판 신원 확인.

- 열람 게이트: APP_GATE_MODE = "code"(접근코드) | "invite"(Community Cloud 비공개 앱 초대)
  code 모드에서는 `?k=<코드>`가 붙은 링크로 바로 들어올 수 있고, 코드 입력 후에는 링크에 자동으로 붙는다.
- 신원 확인: Streamlit 내장 OIDC(st.login)로 Google 계정을 확인한다. [auth] 설정이 없으면 비활성.
"""
from __future__ import annotations

import hmac

import streamlit as st

_GATE_FLAG = "gate_ok"
_LINK_PARAM = "k"


def secret(name: str, default=None):
    """secrets.toml이 없거나 키가 없어도 예외 없이 기본값을 돌려준다."""
    try:
        return st.secrets[name]
    except (KeyError, FileNotFoundError):
        return default
    except Exception:
        return default


# ── 열람 게이트 ────────────────────────────────────────────────

def gate() -> bool:
    """통과하면 True. 통과하지 못하면 게이트 화면을 그리고 False."""
    mode = str(secret("APP_GATE_MODE", "code")).lower()
    if mode != "code":
        return True

    code = secret("APP_ACCESS_CODE")
    if not code:
        st.error("접근코드가 설정되지 않았습니다. secrets에 APP_ACCESS_CODE를 추가하세요.")
        return False
    code = str(code)

    if st.session_state.get(_GATE_FLAG):
        _keep_code_in_link(code)
        return True

    given = st.query_params.get(_LINK_PARAM)
    if given and hmac.compare_digest(str(given), code):
        st.session_state[_GATE_FLAG] = True
        return True

    _render_gate(code)
    return False


def _keep_code_in_link(code: str) -> None:
    """페이지를 옮기거나 새로고침해도 링크에 코드가 남도록 유지한다."""
    if st.query_params.get(_LINK_PARAM) != code:
        st.query_params[_LINK_PARAM] = code


def _render_gate(code: str) -> None:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("### 김성훈 연구 페이지")
        st.caption("공유받은 접근코드를 입력하면 들어갈 수 있습니다.")
        with st.form("gate_form", border=True):
            given = st.text_input("접근코드", type="password", autocomplete="off")
            ok = st.form_submit_button("들어가기", type="primary", width="stretch")
        if ok:
            if given and hmac.compare_digest(given.strip(), code):
                st.session_state[_GATE_FLAG] = True
                st.query_params[_LINK_PARAM] = code
                st.rerun()
            st.error("접근코드가 맞지 않습니다. 코드를 공유한 사람에게 다시 확인해 주세요.")


# ── Google 인증 (게시판 신원) ───────────────────────────────────

def auth_configured() -> bool:
    return secret("auth") is not None


def current_user() -> dict | None:
    """로그인한 사용자 {email, name} 또는 None."""
    if not auth_configured():
        return None
    try:
        user = st.user
        if not getattr(user, "is_logged_in", False):
            return None
        email = user.get("email")
        return {"email": email, "name": user.get("name") or email}
    except Exception:
        return None


def is_admin() -> bool:
    user = current_user()
    if not user or not user.get("email"):
        return False
    admins = secret("ADMIN_EMAILS", []) or []
    return user["email"].lower() in {str(a).lower() for a in admins}


def render_sidebar_account() -> None:
    """사이드바 하단의 로그인 상태."""
    with st.sidebar:
        st.divider()
        if not auth_configured():
            st.caption("Google 인증 미설정 — 게시판은 이름만으로 작성됩니다.")
            return
        user = current_user()
        if user:
            st.caption(f"{user['name']}  \n{user['email']}")
            if st.button("로그아웃", width="stretch"):
                st.logout()
        else:
            st.caption("Google 계정으로 확인하면 글이 바로 게시됩니다.")
            if st.button("Google로 로그인", width="stretch"):
                st.login()
