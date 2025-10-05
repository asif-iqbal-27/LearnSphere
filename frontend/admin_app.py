import streamlit as st
import os
import json
import hashlib
import requests

# ------------------ CONFIG ------------------ #
API_BASE_URL = "http://localhost:8000/api/v1"
PRIMARY_COLOR = "#66CDD3"
ADMIN_FILE = "frontend/admin.json"


# ------------------ HELPERS ------------------ #
def load_admins():
    """Load admins from JSON"""
    if not os.path.exists(ADMIN_FILE):
        return {"admins": []}
    with open(ADMIN_FILE, "r") as f:
        return json.load(f)


def save_admins(admins):
    """Save admins to JSON"""
    with open(ADMIN_FILE, "w") as f:
        json.dump(admins, f, indent=4)


def hash_password(password: str) -> str:
    """Hash password with SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


# ------------------ CSS ------------------ #
def load_css():
    st.markdown(f"""
        <style>
        .main-title {{
            color: {PRIMARY_COLOR};
            text-align: center;
            font-size: 2.2em;
            font-weight: bold;
            margin-bottom: 20px;
        }}
        .section-title {{
            color: {PRIMARY_COLOR};
            font-size: 1.4em;
            font-weight: 600;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        .upload-box {{
            background-color: #ffffff;
            border: 2px dashed {PRIMARY_COLOR};
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            margin-bottom: 20px;
        }}
        </style>
    """, unsafe_allow_html=True)


# ------------------ ADMIN LOGIN ------------------ #
def admin_login():
    st.markdown("<div class='main-title'>🔐 Admin Login</div>", unsafe_allow_html=True)
    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login"):
        creds = load_admins()
        for admin in creds["admins"]:
            if admin["username"] == username and admin["password"] == hash_password(password):
                st.session_state["is_admin"] = True
                st.session_state["admin_username"] = username
                st.success(f"✅ Login successful! Welcome, {username}")
                st.session_state["refresh_trigger"] = not st.session_state.get("refresh_trigger", False)
                st.stop()
        st.error("❌ Invalid username or password")


# ------------------ ADMIN REGISTRATION ------------------ #
def admin_register():
    st.markdown("<div class='main-title'>🆕 Register Admin</div>", unsafe_allow_html=True)
    username = st.text_input("New Username", key="reg_user")
    password = st.text_input("New Password", type="password", key="reg_pass")
    confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
    if st.button("Register"):
        if password != confirm_password:
            st.error("❌ Passwords do not match")
            return
        creds = load_admins()
        if any(admin["username"] == username for admin in creds["admins"]):
            st.error("❌ Username already exists")
            return
        creds["admins"].append({
            "username": username,
            "password": hash_password(password)
        })
        save_admins(creds)
        st.success(f"✅ Admin '{username}' registered successfully! You can now login.")


# ------------------ DOCUMENT MANAGEMENT ------------------ #
def upload_page():
    st.markdown("<div class='section-title'>📂 Upload Document</div>", unsafe_allow_html=True)

    with st.form("upload_form"):
        st.markdown("<div class='upload-box'>Drag & drop your PDF or click below</div>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Choose a PDF", type="pdf", label_visibility="collapsed")
        col1, col2, col3 = st.columns(3)
        with col1:
            class_name = st.text_input("Class Name", placeholder="e.g., class_six")
        with col2:
            subject = st.text_input("Subject", placeholder="e.g., BGS")
        with col3:
            version = st.text_input("Version", placeholder="e.g., English")
        submitted = st.form_submit_button("🚀 Upload Document")
        if submitted and uploaded_file:
            filename = f"{class_name}_{subject}_{version}.pdf"
            files = {"file": (filename, uploaded_file.getvalue(), "application/pdf")}
            try:
                resp = requests.post(f"{API_BASE_URL}/documents/add_document", files=files)
                if resp.status_code == 200:
                    st.success("✅ Document uploaded successfully!")
                    st.session_state["refresh_trigger"] = not st.session_state.get("refresh_trigger", False)
                    st.stop()
                else:
                    st.error(f"❌ Upload failed: {resp.json().get('detail', 'Unknown error')}")
            except Exception as e:
                st.error(f"⚠️ Error: {str(e)}")


def delete_page():
    st.markdown("<div class='section-title'>📄 Manage Documents</div>", unsafe_allow_html=True)
    try:
        resp = requests.get(f"{API_BASE_URL}/documents/documents")
        if resp.status_code != 200:
            st.error("Failed to fetch documents")
            return

        docs = resp.json().get("documents", [])
        if not docs:
            st.info("No documents available")
            return

        # Remove duplicates
        seen = set()
        unique_docs = []
        for doc in docs:
            if doc["collection_name"] not in seen:
                unique_docs.append(doc)
                seen.add(doc["collection_name"])
        docs = unique_docs

        for doc in docs:
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"📄 {doc['collection_name']}")
            with col2:
                delete_key = f"delete_{doc['collection_name']}"
                if st.button("Delete", key=delete_key):
                    try:
                        d_resp = requests.delete(f"{API_BASE_URL}/documents/{doc['collection_name']}")
                        if d_resp.status_code == 200:
                            st.success(f"✅ Deleted {doc['collection_name']}")
                            st.session_state["refresh_trigger"] = not st.session_state.get("refresh_trigger", False)
                            st.stop()

                        else:
                            st.error(f"❌ Failed to delete {doc['collection_name']}")
                    except Exception as e:
                        st.error(f"⚠️ Error: {str(e)}")
    except Exception as e:
        st.error(f"⚠️ Error: {str(e)}")


# ------------------ MAIN ------------------ #
def main():
    load_css()

    if "is_admin" not in st.session_state:
        st.session_state["is_admin"] = False

    st.sidebar.markdown(f"<h3 style='color:{PRIMARY_COLOR}'>Menu</h3>", unsafe_allow_html=True)
    choice = st.sidebar.radio("Select", ["Login", "Register"])

    if not st.session_state["is_admin"]:
        if choice == "Login":
            admin_login()
        else:
            admin_register()
    else:
        if st.sidebar.button("Logout"):
            st.session_state["is_admin"] = False

            st.session_state["refresh_trigger"] = not st.session_state.get("refresh_trigger", False)
            st.stop()
        upload_page()
        st.markdown("---")
        delete_page()


if __name__ == "__main__":
    main()
