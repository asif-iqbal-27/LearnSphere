import streamlit as st
import requests
import os
from PIL import Image

# Configure Streamlit
st.set_page_config(
    page_title="EduGPT",
    page_icon="📚",
    layout="wide"
)

API_BASE_URL = "http://localhost:8000/api/v1"

def display_images(image_paths: list):
    """Display multiple images side by side"""
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
                if os.path.exists(img_path):
                    image = Image.open(img_path)
                    cols[idx].image(image, use_container_width=False, width=160)
        except Exception as e:
            cols[idx].error(f"Error: {str(e)}")

def parse_collection_name(name: str):
    """Parse collection name like 'class_six_BGS_English'"""
    parts = name.replace(".pdf", "").split("_")
    if len(parts) == 4:
        class_name = f"{parts[0].capitalize()} {parts[1].capitalize()}"
        subject = parts[2]
        version = parts[3].capitalize()
        return class_name, subject, version
    return None, None, None

def chat_page():
    st.header("💬 Chat with Document")

    # Fetch documents
    try:
        response = requests.get(f"{API_BASE_URL}/documents/documents")
        if response.status_code != 200:
            st.error("Failed to fetch documents")
            return
        documents_raw = response.json()["documents"]

        # Parse and deduplicate
        seen = set()
        documents = []
        for doc in documents_raw:
            cname = doc["collection_name"]
            if cname not in seen:
                class_name, subject, version = parse_collection_name(cname)
                if class_name:
                    documents.append({
                        "collection_name": cname,
                        "class_name": class_name,
                        "subject": subject,
                        "version": version
                    })
                seen.add(cname)

        if not documents:
            st.info("No documents available. Please upload a document first.")
            return

        # Class / Version / Subject selection
        classes = sorted(set(doc["class_name"] for doc in documents))
        selected_class = st.selectbox("Select Class", ["--Select--"] + classes)
        if selected_class == "--Select--":
            return

        versions = sorted(set(doc["version"] for doc in documents if doc["class_name"] == selected_class))
        selected_version = st.selectbox("Select Version", ["--Select--"] + versions)
        if selected_version == "--Select--":
            return

        subjects = sorted(set(
            doc["subject"] for doc in documents
            if doc["class_name"] == selected_class and doc["version"] == selected_version
        ))
        selected_subject = st.selectbox("Select Subject", ["--Select--"] + subjects)
        if selected_subject == "--Select--":
            return

        collection_name = next(
            (doc["collection_name"] for doc in documents
             if doc["class_name"] == selected_class and
                doc["version"] == selected_version and
                doc["subject"] == selected_subject),
            None
        )
        if not collection_name:
            st.error("Collection not found")
            return

        st.info(f"Chatting with: **{selected_class} - {selected_subject} - {selected_version}**")

        # Initialize session state for this collection
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = {}
        if collection_name not in st.session_state.chat_history:
            st.session_state.chat_history[collection_name] = []

        current_chat = st.session_state.chat_history[collection_name]

        # Display previous messages only once
        for message in current_chat:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message.get("images"):
                    display_images(message["images"])

        # Chat input
        if prompt := st.chat_input("Ask a question about the document"):
            # Add user message
            current_chat.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Assistant response
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

                            # Save assistant message
                            current_chat.append({
                                "role": "assistant",
                                "content": response_text,
                                "images": images
                            })
                        else:
                            error_detail = response.json().get('detail', 'Unknown error')
                            st.error(f"Error: {error_detail}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

        # Clear chat button
        col1, _ = st.columns([1, 4])
        with col1:
            if st.button("Clear Chat"):
                st.session_state.chat_history[collection_name] = []
                st.experimental_rerun()

    except Exception as e:
        st.error(f"Error loading documents: {str(e)}")

def main():
    st.title("📚 EduGPT")
    st.markdown("Chat with your educational documents!")
    chat_page()

if __name__ == "__main__":
    main()
