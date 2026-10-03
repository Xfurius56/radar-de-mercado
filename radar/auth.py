from __future__ import annotations

from typing import Any

import streamlit as st


def _secret(name: str) -> str:
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return str(value).strip()


def supabase_settings() -> tuple[str, str]:
    from radar.config import env_value

    url = _secret("SUPABASE_URL") or env_value("SUPABASE_URL")
    key = _secret("SUPABASE_ANON_KEY") or env_value("SUPABASE_ANON_KEY")
    return url.rstrip("/"), key


def is_configured() -> bool:
    return all(supabase_settings())


def _new_client():
    url, key = supabase_settings()
    if not url or not key:
        raise RuntimeError("Falta configurar Supabase para habilitar el acceso privado.")
    from supabase import create_client

    return create_client(url, key)


def _store_session(client: Any, session: Any) -> None:
    st.session_state["_radar_supabase_client"] = client
    st.session_state["_radar_access_token"] = session.access_token
    st.session_state["_radar_refresh_token"] = session.refresh_token


def _clear_session() -> None:
    for key in ("_radar_supabase_client", "_radar_access_token", "_radar_refresh_token",
                "_radar_user_id", "_radar_user_email", "_radar_schema_checked_for"):
        st.session_state.pop(key, None)


def clear_user_workspace() -> None:
    transient = {
        "market_results", "chat_history", "investor_profile_complete", "backtest_rows",
        "backtest_source", "backtest_symbol", "backtest_result",
    }
    for key in list(st.session_state.keys()):
        if key in transient or key.startswith(("lesson_feedback_", "lesson_exercise_")):
            st.session_state.pop(key, None)


def get_supabase_client():
    client = st.session_state.get("_radar_supabase_client")
    access_token = st.session_state.get("_radar_access_token")
    refresh_token = st.session_state.get("_radar_refresh_token")
    if client is None or not access_token or not refresh_token:
        raise RuntimeError("La sesión ha caducado. Inicia sesión de nuevo.")
    try:
        session = client.auth.get_session()
        if session is None:
            client.auth.set_session(access_token, refresh_token)
            session = client.auth.get_session()
        if session is None:
            raise RuntimeError("No hay una sesión autenticada.")
        st.session_state["_radar_access_token"] = session.access_token
        st.session_state["_radar_refresh_token"] = session.refresh_token
        return client
    except Exception as exc:
        raise RuntimeError("No se pudo renovar la sesión. Vuelve a iniciar sesión.") from exc


def current_user_id() -> str:
    user_id = st.session_state.get("_radar_user_id")
    if not user_id:
        raise RuntimeError("La sesión no tiene un usuario autenticado.")
    return str(user_id)


def _database_ready(client: Any, user_id: str) -> bool:
    tables = (
        "settings", "source_status", "products", "watchlist", "asset_observations",
        "product_observations", "alerts", "portfolios", "sim_trades", "portfolio_marks",
        "lesson_progress", "image_analyses",
    )
    for table in tables:
        client.table(table).select("user_id").eq("user_id", user_id).limit(1).execute()
    return True


def _activate(client: Any, session: Any) -> None:
    clear_user_workspace()
    _store_session(client, session)
    user_response = client.auth.get_user(session.access_token)
    user = getattr(user_response, "user", None)
    if user is None or not getattr(user, "id", None):
        _clear_session()
        raise RuntimeError("No se pudo verificar la identidad de esta cuenta.")
    st.session_state["_radar_user_id"] = str(user.id)
    st.session_state["_radar_user_email"] = str(getattr(user, "email", ""))


def _render_login() -> bool:
    st.title("🧭 Radar de Mercado")
    st.caption("Acceso privado para tu espacio de investigación.")
    if not is_configured():
        st.warning("El acceso de usuarios aún no está habilitado. Primero configura Supabase y aplica el esquema de base de datos del proyecto.")
        st.info("Cuando esté listo, cada cuenta tendrá su propia información. No se permite continuar en el modo compartido de demostración.")
        st.code("SUPABASE_URL = \"https://tu-proyecto.supabase.co\"\nSUPABASE_ANON_KEY = \"tu-clave-publicable\"\nOPENAI_API_KEY = \"tu-clave-de-openai\"", language="toml")
        st.caption("Añade estos valores en Streamlit Cloud → Manage app → Settings → Secrets. Nunca uses ni publiques la clave service_role de Supabase.")
        return False

    login_tab, signup_tab = st.tabs(["Iniciar sesión", "Crear cuenta"])
    with login_tab:
        with st.form("radar_login"):
            email = st.text_input("Correo electrónico", autocomplete="email")
            password = st.text_input("Contraseña", type="password", autocomplete="current-password")
            submitted = st.form_submit_button("Entrar", type="primary", use_container_width=True)
        if submitted:
            if not email.strip() or not password:
                st.error("Escribe tu correo y contraseña.")
            else:
                try:
                    client = _new_client()
                    result = client.auth.sign_in_with_password({"email": email.strip(), "password": password})
                    if result.session is None:
                        st.error("No se inició sesión. Comprueba tus datos y la verificación del correo.")
                    else:
                        _activate(client, result.session)
                        st.rerun()
                except Exception:
                    st.error("No se pudo iniciar sesión. Comprueba el correo, la contraseña y la configuración del servicio.")

    with signup_tab:
        st.caption("Usa una contraseña larga y única. El servicio puede pedirte confirmar el correo antes de entrar.")
        with st.form("radar_signup"):
            new_email = st.text_input("Correo electrónico", key="signup_email", autocomplete="email")
            new_password = st.text_input("Contraseña (12 caracteres o más)", type="password", key="signup_password", autocomplete="new-password")
            confirm_password = st.text_input("Repite la contraseña", type="password", autocomplete="new-password")
            create = st.form_submit_button("Crear cuenta", use_container_width=True)
        if create:
            if not new_email.strip() or len(new_password) < 12:
                st.error("Escribe tu correo y una contraseña de al menos 12 caracteres.")
            elif new_password != confirm_password:
                st.error("Las contraseñas no coinciden.")
            else:
                try:
                    client = _new_client()
                    result = client.auth.sign_up({"email": new_email.strip(), "password": new_password})
                    if result.session is not None:
                        _activate(client, result.session)
                        st.rerun()
                    else:
                        st.success("Cuenta creada. Confirma el correo y después inicia sesión.")
                except Exception:
                    st.error("No se pudo crear la cuenta. Comprueba el correo y vuelve a intentarlo.")
    return False


def require_authenticated_user() -> bool:
    if not is_configured():
        return _render_login()
    client = st.session_state.get("_radar_supabase_client")
    access_token = st.session_state.get("_radar_access_token")
    refresh_token = st.session_state.get("_radar_refresh_token")
    if client is None or not access_token or not refresh_token:
        return _render_login()
    try:
        session = client.auth.get_session()
        if session is None:
            session = client.auth.set_session(access_token, refresh_token)
            session = getattr(session, "session", None) or client.auth.get_session()
        if session is None:
            _clear_session()
            return _render_login()
        verified = client.auth.get_user(session.access_token).user
        if verified is None:
            _clear_session()
            return _render_login()
        st.session_state["_radar_access_token"] = session.access_token
        st.session_state["_radar_refresh_token"] = session.refresh_token
        st.session_state["_radar_user_id"] = str(verified.id)
        st.session_state["_radar_user_email"] = str(getattr(verified, "email", ""))
    except Exception:
        _clear_session()
        return _render_login()
    if st.session_state.get("_radar_schema_checked_for") != str(verified.id):
        try:
            _database_ready(client, str(verified.id))
            st.session_state["_radar_schema_checked_for"] = str(verified.id)
        except Exception:
            st.title("Configuración pendiente")
            st.error("La base de datos privada aún no está completa. El administrador debe ejecutar `database/schema.sql` en Supabase SQL Editor antes de abrir el espacio.")
            return False
    return True


def logout() -> None:
    client = st.session_state.get("_radar_supabase_client")
    if client is not None:
        try:
            client.auth.sign_out({"scope": "local"})
        except Exception:
            pass
    st.session_state.clear()
