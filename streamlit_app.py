import streamlit as st
import requests
import os
from pathlib import Path
from PIL import Image

# Configure Streamlit
st.set_page_config(
    page_title="EduGPT",
    page_icon="📚",
    layout="wide"
)

# API base URL
API_BASE_URL = "http://localhost:8000/api/v1"


def main():
    st.title("📚 EduGPT")
    st.markdown("Upload educational documents and chat with them!")

    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", ["Upload Document", "Chat with Document"])

    if page == "Upload Document":
        upload_page()
    elif page == "Chat with Document":
        chat_page()


def upload_page():
    st.header("📄 Upload Document")

    with st.form("upload_form"):
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

        col1, col2, col3 = st.columns(3)
        with col1:
            class_name = st.text_input("Class Name", placeholder="e.g., class_six")
        with col2:
            subject = st.text_input("Subject", placeholder="e.g., English")
        with col3:
            version = st.text_input("Version", placeholder="e.g., bangla or english")

        submitted = st.form_submit_button("Upload Document")

        if submitted and uploaded_file is not None:
            # If inputs are empty, parse from filename
            if not all([class_name, subject, version]):
                try:
                    name_without_ext = uploaded_file.name.replace(".pdf", "")
                    parts = name_without_ext.split("_")
                    if len(parts) >= 3:
                        class_name = class_name or parts[0]
                        subject = subject or parts[1]
                        version = version or "_".join(parts[2:])
                    else:
                        st.error("Please fill in all fields or use a correctly formatted filename")
                        return
                except Exception as e:
                    st.error(f"Error parsing filename: {str(e)}")
                    return

            filename = f"{class_name}_{subject}_{version}.pdf"

            with st.spinner("Processing document..."):
                try:
                    files = {"file": (filename, uploaded_file.getvalue(), "application/pdf")}
                    response = requests.post(f"{API_BASE_URL}/documents/add_document", files=files)

                    if response.status_code == 200:
                        result = response.json()
                        st.success("Document uploaded successfully!")
                        st.info(f"Collection Name: {result['collection_name']}")
                        st.info(f"Class: {result['class_name']}")
                        st.info(f"Subject: {result['subject']}")
                        st.info(f"Version: {result['version']}")
                    else:
                        error_detail = response.json().get('detail', 'Unknown error')
                        st.error(f"Upload failed: {error_detail}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")


def display_images(image_paths: list):
    """Display multiple images side by side in small size"""
    if not image_paths:
        return

    cols = st.columns(len(image_paths))
    for idx, img_path in enumerate(image_paths):
        try:
            if img_path.startswith("http://") or img_path.startswith("https://"):
                response = requests.get(img_path, stream=True)
                if response.status_code == 200:
                    image = Image.open(response.raw)
                    cols[idx].image(image, use_container_width=False, width=160)
                else:
                    cols[idx].warning("Image not accessible")
            else:
                if os.path.exists(img_path):
                    image = Image.open(img_path)
                    cols[idx].image(image, use_container_width=False, width=160)
                else:
                    cols[idx].warning("Image not found locally")
        except Exception as e:
            cols[idx].error(f"Error: {str(e)}")


def chat_page():
    st.header("💬 Chat with Document")

    try:
        response = requests.get(f"{API_BASE_URL}/documents/documents")
        if response.status_code == 200:
            documents_raw = response.json()["documents"]

            # Remove duplicate collections based on collection_name
            seen = set()
            documents = []
            for doc in documents_raw:
                if doc["collection_name"] not in seen:
                    documents.append(doc)
                    seen.add(doc["collection_name"])

            if not documents:
                st.info("No documents available. Please upload a document first.")
                return

            # Document selector
            doc_options = [
                f"{doc['class_name']} - {doc['subject']} - {doc['version']}"
                for doc in documents
            ]
            selected_doc = st.selectbox("Select a document", doc_options)

            if selected_doc:
                selected_index = doc_options.index(selected_doc)
                collection_name = documents[selected_index]["collection_name"]

                st.info(f"Chatting with: **{selected_doc}**")

                # Initialize chat history
                if "chat_history" not in st.session_state:
                    st.session_state.chat_history = {}
                if collection_name not in st.session_state.chat_history:
                    st.session_state.chat_history[collection_name] = []

                current_chat = st.session_state.chat_history[collection_name]

                # Display chat history
                for message in current_chat:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
                        if message.get("images"):
                            display_images(message["images"])

                # Chat input
                if prompt := st.chat_input("Ask a question about the document"):
                    current_chat.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)

                    with st.chat_message("assistant"):
                        with st.spinner("Thinking..."):
                            try:
                                chat_request = {"query": prompt, "collection_name": collection_name}
                                response = requests.post(f"{API_BASE_URL}/chat/chat", json=chat_request)
                                if response.status_code == 200:
                                    result = response.json()
                                    response_text = result["response"]
                                    images = result.get("images", [])

                                    st.markdown(response_text)

                                    if images:
                                        display_images(images)

                                    current_chat.append({
                                        "role": "assistant",
                                        "content": response_text,
                                        "images": images
                                    })
                                    st.session_state.chat_history[collection_name] = current_chat
                                else:
                                    error_detail = response.json().get('detail', 'Unknown error')
                                    st.error(f"Error: {error_detail}")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")

                # Clear chat or delete document buttons
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("Clear Chat"):
                        st.session_state.chat_history[collection_name] = []
                        st.rerun()
                with col2:
                    if st.button("Delete Document"):
                        try:
                            response = requests.delete(f"{API_BASE_URL}/documents/{collection_name}")
                            if response.status_code == 200:
                                st.success("Document deleted successfully!")
                                if collection_name in st.session_state.chat_history:
                                    del st.session_state.chat_history[collection_name]
                                st.rerun()
                            else:
                                st.error("Failed to delete document")
                        except Exception as e:
                            st.error(f"Error deleting document: {str(e)}")
        else:
            st.error("Failed to fetch documents")
    except Exception as e:
        st.error(f"Error loading documents: {str(e)}")


if __name__ == "__main__":
    main()

    # streamlit run streamlit_app.py
    # python run_api.py
    # docker-compose up -d
