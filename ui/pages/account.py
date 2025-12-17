import streamlit as st

from utils.api_client import api_request, API_URL
from utils.auth import logout
from utils.error_handling import handle_api_error


st.markdown("### 🔐 Account Management")
st.caption(f"API: {API_URL}")

st.subheader("Register")
with st.form("register_form"):
    reg_user = st.text_input("Username", key="register_username")
    reg_pass = st.text_input("Password", type="password", key="register_password")
    submitted = st.form_submit_button("Create Account")
if submitted and reg_user and reg_pass:
    res = api_request(
        "post",
        "/api/v1/user/register",
        json={"username": reg_user, "password": reg_pass},
    )
    if res.status_code == 200:
        api_key = res.json().get("api_key")
        if api_key:
            from utils.auth import set_api_key
            set_api_key(api_key)
            st.success("Registration successful! You are now logged in.")
            st.info("Your API key has been saved to session.")
        else:
            st.success("Registration successful! Please login to continue.")
    else:
        handle_api_error(res, "Registration")

st.subheader("Login")
with st.form("login_form"):
    login_user = st.text_input("Username", key="login_username")
    login_pass = st.text_input("Password", type="password", key="login_password")
    login_submitted = st.form_submit_button("Login")
if login_submitted and login_user and login_pass:
    res = api_request(
        "post",
        "/api/v1/user/login",
        json={"username": login_user, "password": login_pass},
    )
    if res.status_code == 200:
        # Get the API key from login response
        api_key = res.json().get("api_key")
        if api_key:
            # Store only the API key, never store passwords
            from utils.auth import set_api_key
            set_api_key(api_key)
            st.session_state.username = login_user
            # Show only last 4 characters of API key for security
            masked_key = f"***{api_key[-4:]}" if len(api_key) > 4 else "****"
            st.success(f"Login successful! API key set: {masked_key}")
            st.rerun()
        else:
            st.error("Login succeeded but no API key returned")
    else:
        handle_api_error(res, "Login")

st.divider()

# Generate New API Key section (requires re-entering password for security)
st.subheader("Generate New API Key")
st.markdown("*Create additional API keys for different applications or rotate compromised keys.*")

with st.form("create_api_key_form"):
    key_username = st.text_input("Username", key="key_gen_username")
    key_password = st.text_input("Password", type="password", key="key_gen_password")
    create_submitted = st.form_submit_button("Generate New API Key")

if create_submitted and key_username and key_password:
    res = api_request(
        "post",
        "/api/v1/user/create-api-key",
        json={"username": key_username, "password": key_password},
    )
    if res.status_code == 200:
        new_key = res.json().get("api_key")
        if new_key:
            # Show only last 4 characters for security
            masked_key = f"***{new_key[-4:]}" if len(new_key) > 4 else "****"
            st.success(f"New API key generated: {masked_key}")
            st.warning("⚠️ Copy this key now! It won't be shown again.")
            # Show full key in a code block for copying (one-time only)
            st.code(new_key, language=None)
        else:
            st.error("API key generation succeeded but no key returned")
    else:
        handle_api_error(res, "API Key Generation")

st.divider()

# Logout section
if st.button("🚪 Logout"):
    logout()
    st.success("Logged out successfully")
    st.rerun()
