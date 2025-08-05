import streamlit as st

from utils.api_client import api_request
from utils.auth import logout


st.markdown("### 🔐 Account Management")

st.subheader("Register")
with st.form("register_form"):
    reg_user = st.text_input("Username", key="register_username")
    reg_pass = st.text_input("Password", type="password", key="register_password")
    submitted = st.form_submit_button("Create Account")
if submitted and reg_user and reg_pass:
    res = api_request(
        "post",
        "/api/user/register",
        json={"username": reg_user, "password": reg_pass},
    )
    if res.status_code == 200:
        st.success(res.json().get("message", "Registered"))
    else:
        detail = res.json().get("detail", "Registration failed")
        st.error(detail)

st.subheader("Login")
with st.form("login_form"):
    login_user = st.text_input("Username", key="login_username")
    login_pass = st.text_input("Password", type="password", key="login_password")
    login_submitted = st.form_submit_button("Login")
if login_submitted and login_user and login_pass:
    res = api_request(
        "post",
        "/api/user/login",
        json={"username": login_user, "password": login_pass},
    )
    if res.status_code == 200:
        st.success(res.json().get("message", "Login successful"))
        st.session_state.username = login_user
        st.session_state.password = login_pass
        st.session_state.api_keys = res.json().get("api_keys", [])
    else:
        st.error(res.json().get("detail", "Login failed"))

try:
    if st.session_state.api_keys:
        st.markdown("#### Existing API Keys")
        selected_key = st.selectbox(
            "Choose an API key",
            st.session_state.api_keys,
            key="existing_api_keys",
        )
        if st.button("Use Selected Key") and selected_key:
            st.session_state.api_key = selected_key
            st.success("API key set for session")
except AttributeError:
    st.session_state.api_keys = []
    

if st.session_state.username and st.session_state.password:
    if st.button("Create New API Key"):
        res = api_request(
            "post",
            "/api/user/create-api-key",
            json={
                "username": st.session_state.username,
                "password": st.session_state.password,
            },
        )
        if res.status_code == 200:
            new_key = res.json().get("api_key")
            st.session_state.api_keys.append(new_key)
            st.session_state.api_key = new_key
            st.success(f"New API key generated: {new_key}")
        else:
            st.error(res.json().get("detail", "Failed to generate key"))

    if st.button("Logout"):
        logout()
        st.success("Logged out")
