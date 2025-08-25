import streamlit as st
import requests
import time
from typing import Dict, List

# Page config
st.set_page_config(
    page_title="RAG Document QA",
    page_icon="📚",
    layout="wide"
)

# API configuration
API_BASE_URL = "http://fastapi:8000"
SECRET_API_KEY = st.secrets["STREAMLIT_SECRET_KEY"]

# Session state initialization
if 'api_key' not in st.session_state:
    st.session_state.api_key = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

def make_api_request(endpoint: str, method: str = "GET", data: Dict = None, files: Dict = None, headers: Dict = None):
    """Make API request with proper error handling"""
    
    if not headers:
        headers = {}
    
    if st.session_state.api_key:
        headers["Authorization"] = f"Bearer {st.session_state.api_key}"
    
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            if files:
                response = requests.post(url, files=files, headers=headers)
            else:
                response = requests.post(url, json=data, headers=headers)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        
        if response.status_code == 429:
            st.error("Rate limit exceeded. Please wait before trying again.")
            return None
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return None

def create_user():
    """Create new user"""
    response = make_api_request("/users", "POST")
    if response:
        st.session_state.api_key = response['api_key']
        st.session_state.user_id = response['user_id']
        return True
    return False

def main():
    st.title("📚 RAG Document QA System")
    
    # API Key management
    with st.sidebar:
        st.header("🔑 Authentication")
        
        if not st.session_state.api_key:
            st.info("You need an API key to use this service.")
            
            api_key_input = st.text_input("Enter your API key:", type="password")
            if st.button("Use Existing Key"):
                if api_key_input:
                    st.session_state.api_key = api_key_input
                    st.rerun()
            
            st.divider()
            
            if st.button("Create New Account"):
                if create_user():
                    st.success("Account created successfully!")
                    st.info(f"Your API key: `{st.session_state.api_key}`")
                    st.warning("⚠️ Save your API key! You won't see it again.")
                    st.rerun()
        else:
            st.success("✅ Authenticated")
            st.info(f"User ID: `{st.session_state.user_id or 'Unknown'}`")
            
            if st.button("Logout"):
                st.session_state.api_key = None
                st.session_state.user_id = None
                st.rerun()
    
    if not st.session_state.api_key:
        st.warning("Please authenticate to continue.")
        return
    
    # Main interface
    tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload", "💬 Chat", "📁 Files", "⚙️ Settings"])
    
    with tab1:
        st.header("📤 Upload Documents")
        
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload PDF documents to chat with them"
        )
        
        if uploaded_file and st.button("Upload & Process"):
            with st.spinner("Processing document..."):
                files = {"file": uploaded_file}
                response = make_api_request("/upload", "POST", files=files)
                
                if response:
                    st.success(f"✅ File processed successfully!")
                    st.info(f"Generated {response['chunk_count']} text chunks")
                    time.sleep(1)
                    st.rerun()
    
    with tab2:
        st.header("💬 Chat with Documents")
        
        # Check if user has files
        files_response = make_api_request("/files")
        if not files_response or not files_response.get('files'):
            st.warning("Please upload some documents first!")
            return
        
        # Chat interface
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message["role"] == "assistant" and "sources" in message:
                    with st.expander("📎 Sources"):
                        for source in message["sources"]:
                            st.write(f"• {source['filename']} (score: {source['score']:.3f})")
        
        # Chat input
        if prompt := st.chat_input("Ask a question about your documents"):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Get AI response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = make_api_request("/ask", "POST", {"question": prompt})
                    
                    if response:
                        st.markdown(response['answer'])
                        
                        # Store assistant message with sources
                        assistant_message = {
                            "role": "assistant", 
                            "content": response['answer'],
                            "sources": response.get('sources', [])
                        }
                        st.session_state.messages.append(assistant_message)
                        
                        # Show sources
                        if response.get('sources'):
                            with st.expander("📎 Sources"):
                                for source in response['sources']:
                                    st.write(f"• {source['filename']} (score: {source['score']:.3f})")
    
    with tab3:
        st.header("📁 File Management")
        
        files_response = make_api_request("/files")
        if files_response and files_response.get('files'):
            st.subheader("Your Documents")
            
            for file in files_response['files']:
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(f"📄 {file['filename']}")
                    st.caption(f"Chunks: {file['chunk_count']} | Uploaded: {file['created_at'][:10]}")
                
                with col2:
                    if st.button(f"🗑️ Delete", key=f"delete_{file['id']}"):
                        if make_api_request(f"/files/{file['id']}", "DELETE"):
                            st.success("File deleted!")
                            st.rerun()
            
            st.divider()
            
            if st.button("🗑️ Delete All Files", type="secondary"):
                if st.button("⚠️ Confirm Delete All", type="primary"):
                    if make_api_request("/user/data", "DELETE"):
                        st.success("All files deleted!")
                        st.rerun()
        else:
            st.info("No documents uploaded yet.")
    
    with tab4:
        st.header("⚙️ Settings")
        
        # Get current config
        config_response = make_api_request("/config")
        if config_response:
            current_prompt = config_response.get('system_prompt', '')
            
            st.subheader("System Prompt")
            new_prompt = st.text_area(
                "Customize how the AI responds:",
                value=current_prompt,
                height=150,
                help="This prompt will be used for all AI responses"
            )
            
            if st.button("💾 Save Settings"):
                response = make_api_request("/config", "PUT", {"system_prompt": new_prompt})
                if response:
                    st.success("Settings saved successfully!")

if __name__ == "__main__":
    main()