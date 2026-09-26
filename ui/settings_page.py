import os

import streamlit as st

from config.settings import settings


def show_settings_page():
    st.title("⚙️ Settings")
    st.markdown("Configure your AI Interview Assistant")

    tabs = st.tabs(
        ["🤖 LLM Provider", "🎤 Speech-to-Text", "🗄️ Database", "🔧 Advanced", "ℹ️ About"]
    )

    with tabs[0]:
        show_llm_settings()

    with tabs[1]:
        show_speech_settings()

    with tabs[2]:
        show_database_settings()

    with tabs[3]:
        show_advanced_settings()

    with tabs[4]:
        show_about()


def show_llm_settings():
    st.subheader("LLM Provider Configuration")

    _current_provider = os.environ.get("LLM_PROVIDER", settings.llm_provider)
    _groq_key = os.environ.get("GROQ_API_KEY", settings.groq_api_key)
    _groq_model_env = os.environ.get("GROQ_MODEL", settings.groq_model)

    st.info(f"""
    **Current Provider:** {_current_provider.upper()}
    """)

    _mistral_key = os.environ.get("MISTRAL_API_KEY", settings.mistral_api_key)
    _mistral_model = os.environ.get("MISTRAL_MODEL", settings.mistral_model)
    _gemini_key = os.environ.get("GEMINI_API_KEY", settings.gemini_api_key)
    _gemini_model = os.environ.get("GEMINI_MODEL", settings.gemini_model)

    groq_models = [
        "groq/compound",
        "groq/compound-mini",
        "allam-2-7b",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-20b",
    ]
    mistral_models = [
        "mistral-small-latest",
        "mistral-medium-latest",
        "mistral-large-latest",
    ]
    gemini_models = [
        "gemini-3.6-flash",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
    ]

    st.markdown("### Gemini (Primary - Free Tier)")
    st.markdown("Get API key from: https://aistudio.google.com/apikey")

    col1, col2 = st.columns(2)
    with col1:
        gemini_key = st.text_input(
            "Gemini API Key",
            value=_gemini_key if _current_provider == "gemini" else "",
            type="password",
            help="Enter your Gemini API key",
        )
    with col2:
        try:
            _gemini_index = gemini_models.index(_gemini_model)
        except ValueError:
            _gemini_index = 0
        gemini_model = st.selectbox("Model", gemini_models, index=_gemini_index)

    st.markdown("### Groq (Free Tier)")
    st.markdown("Get API key from: https://console.groq.com/keys")

    col1, col2 = st.columns(2)
    with col1:
        groq_key = st.text_input(
            "Groq API Key",
            value=_groq_key if _current_provider == "groq" else "",
            type="password",
            help="Enter your Groq API key",
        )
    with col2:
        try:
            _groq_index = groq_models.index(_groq_model_env)
        except ValueError:
            _groq_index = 0
        groq_model = st.selectbox("Model", groq_models, index=_groq_index)

    st.markdown("### Mistral (Alternative - Free Tier)")
    st.markdown("Get API key from: https://console.mistral.ai/")

    col1, col2 = st.columns(2)
    with col1:
        mistral_key = st.text_input(
            "Mistral API Key",
            value=_mistral_key,
            type="password",
            help="Enter your Mistral API key",
        )
    with col2:
        try:
            _mistral_index = mistral_models.index(_mistral_model)
        except ValueError:
            _mistral_index = 0
        mistral_model = st.selectbox("Model", mistral_models, index=_mistral_index)

    st.markdown("### Provider Priority (Auto mode)")
    st.caption("When LLM_PROVIDER=auto, providers are tried in this order.")
    priority = st.text_input(
        "Priority (comma-separated)",
        value="groq,gemini,mistral",
        help="Reorder by dragging? No — just type comma-separated names.",
    )

    try:
        _provider_index = ["gemini", "groq", "mistral"].index(_current_provider)
    except ValueError:
        _provider_index = 0
    provider = st.radio(
        "Active Provider",
        ["gemini", "groq", "mistral", "auto"],
        index=_provider_index,
        horizontal=True,
    )

    if st.button("Save LLM Settings", type="primary"):
        os.environ["LLM_PROVIDER"] = provider
        if groq_key:
            os.environ["GROQ_API_KEY"] = groq_key
        if groq_model:
            os.environ["GROQ_MODEL"] = groq_model
        if mistral_key:
            os.environ["MISTRAL_API_KEY"] = mistral_key
        if mistral_model:
            os.environ["MISTRAL_MODEL"] = mistral_model
        if gemini_key:
            os.environ["GEMINI_API_KEY"] = gemini_key
        if gemini_model:
            os.environ["GEMINI_MODEL"] = gemini_model
        if priority:
            os.environ["PROVIDER_PRIORITY"] = priority

        from services.llm_service import reset_llm_service

        reset_llm_service()

        st.success("Settings saved! Changes are effective immediately.")
        st.info(
            "Add these to your .env file for persistence across restarts. "
            "Keys shown below are masked for your security."
        )
        st.code(f"""
LLM_PROVIDER={provider}
PROVIDER_PRIORITY={priority}

# Groq
GROQ_API_KEY={'*' * 8 if groq_key else ''}
GROQ_MODEL={groq_model if groq_model else ''}

# Mistral
MISTRAL_API_KEY={'*' * 8 if mistral_key else ''}
MISTRAL_MODEL={mistral_model if mistral_model else ''}

# Gemini
GEMINI_API_KEY={'*' * 8 if gemini_key else ''}
GEMINI_MODEL={gemini_model if gemini_model else ''}
            """)

    if st.button("🧪 Test Connection", use_container_width=True):
        if provider == "gemini":
            _test_llm_connection("gemini", gemini_key, gemini_model)
        elif provider == "groq":
            _test_llm_connection("groq", groq_key, groq_model)
        elif provider == "mistral":
            _test_llm_connection("mistral", mistral_key, mistral_model)
        else:
            _test_llm_connection("auto")


def _test_llm_connection(provider_name, api_key=None, model_name=None):
    if provider_name == "auto":
        api_key = (
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("MISTRAL_API_KEY")
            or os.environ.get("GROQ_API_KEY", "")
        )
        model_name = (
            os.environ.get("GEMINI_MODEL")
            or os.environ.get("MISTRAL_MODEL")
            or os.environ.get("GROQ_MODEL", "auto")
        )

    if not api_key:
        st.error("🔑 Please enter an API key first.")
        return

    with st.spinner("Testing connection..."):
        try:
            from services.llm_service import LLMService, reset_llm_service

            if provider_name == "gemini":
                os.environ["LLM_PROVIDER"] = "gemini"
                os.environ["GEMINI_API_KEY"] = api_key
                os.environ["GEMINI_MODEL"] = model_name or settings.gemini_model
            elif provider_name == "mistral":
                os.environ["LLM_PROVIDER"] = "mistral"
                os.environ["MISTRAL_API_KEY"] = api_key
                os.environ["MISTRAL_MODEL"] = model_name or settings.mistral_model
            elif provider_name == "groq":
                os.environ["LLM_PROVIDER"] = "groq"
                os.environ["GROQ_API_KEY"] = api_key
                os.environ["GROQ_MODEL"] = model_name or settings.groq_model

            reset_llm_service()

            test_service = LLMService()
            response = test_service.generate("Say hello in one word.", max_tokens=10)

            st.success(
                f"✅ Connection successful! Model: {response.provider} "
                f"({response.model}) responded: {response.content.strip()}"
            )
        except ValueError as e:
            if "API key" in str(e) or "not provided" in str(e):
                st.error("🔑 API key not provided or invalid.")
            else:
                st.error(f"❌ {e!s}")
        except Exception as e:
            msg = str(e)
            if "HTTP 401" in msg or "unauthorized" in msg.lower():
                st.error("🔑 Invalid API key. Please check your key.")
            elif "HTTP 404" in msg:
                st.error(f"❌ Model not available: {msg}")
            elif "HTTP 429" in msg or "rate limit" in msg.lower():
                st.error("⏱️ Rate limit exceeded. Please wait and try again.")
            elif "timeout" in msg.lower() or "timed out" in msg.lower():
                st.error("⌛ Request timed out. Check your connection.")
            elif "All configured AI providers" in msg:
                st.error("❌ No working providers. Check API keys and try again.")
            else:
                st.error(f"❌ Connection failed: {msg}")

        reset_llm_service()


def show_speech_settings():
    st.subheader("Speech-to-Text (Whisper) Configuration")

    st.info(f"""
    **Current Model:** {settings.whisper_model}
    **Device:** {settings.whisper_device}
    """)

    col1, col2 = st.columns(2)
    with col1:
        whisper_model = st.selectbox(
            "Whisper Model",
            ["tiny", "base", "small", "medium", "large"],
            index=["tiny", "base", "small", "medium", "large"].index(settings.whisper_model),
        )

    with col2:
        whisper_device = st.selectbox(
            "Device",
            ["cpu", "cuda"],
            index=0 if settings.whisper_device == "cpu" else 1,
        )

    st.markdown("**Model Sizes & Accuracy:**")
    st.markdown("""
    | Model | Size | Speed | Accuracy |
    |-------|------|-------|----------|
    | tiny | ~39 MB | Fastest | Lowest |
    | base | ~74 MB | Fast | Good |
    | small | ~244 MB | Medium | Better |
    | medium | ~769 MB | Slow | High |
    | large | ~1550 MB | Slowest | Highest |
    """)

    if st.button("💾 Save Speech Settings"):
        os.environ["WHISPER_MODEL"] = whisper_model
        os.environ["WHISPER_DEVICE"] = whisper_device

        from services.speech_to_text import reset_speech_to_text

        reset_speech_to_text()

        st.success("Settings saved!")


def show_database_settings():
    st.subheader("Database Configuration")

    st.info(f"""
    **Database Path:** {settings.database_path}
    **Vector Store:** {settings.vector_store_type} at {settings.vector_store_path}
    """)

    if st.button("🗑️ Clear All Data", type="secondary"):
        if st.checkbox("I understand this will delete all my data"):
            clear_all_data()
            st.success("All data cleared!")
            st.rerun()

    if st.button("📊 Show Database Stats"):
        show_db_stats()


def show_advanced_settings():
    st.subheader("Advanced Settings")

    col1, col2 = st.columns(2)
    with col1:
        chunk_size = st.number_input(
            "Chunk Size", value=settings.chunk_size, min_value=100, max_value=5000
        )
        chunk_overlap = st.number_input(
            "Chunk Overlap", value=settings.chunk_overlap, min_value=0, max_value=1000
        )
        top_k = st.number_input(
            "Top-K Retrieval", value=settings.top_k_retrieval, min_value=1, max_value=20
        )

    with col2:
        request_timeout = st.number_input(
            "Request Timeout (s)",
            value=settings.request_timeout,
            min_value=10,
            max_value=300,
        )
        max_retries = st.number_input(
            "Max Retries", value=settings.max_retries, min_value=1, max_value=10
        )
        backoff = st.number_input(
            "Retry Backoff Factor",
            value=settings.retry_backoff_factor,
            min_value=1.0,
            max_value=5.0,
        )

    st.markdown("### RAG Settings")
    embedding_model = st.selectbox(
        "Embedding Model",
        [
            "sentence-transformers/all-MiniLM-L6-v2",
            "sentence-transformers/all-mpnet-base-v2",
        ],
        index=0,
    )

    if st.button("Save Advanced Settings"):
        os.environ["CHUNK_SIZE"] = str(chunk_size)
        os.environ["CHUNK_OVERLAP"] = str(chunk_overlap)
        os.environ["TOP_K_RETRIEVAL"] = str(top_k)
        os.environ["REQUEST_TIMEOUT"] = str(request_timeout)
        os.environ["MAX_RETRIES"] = str(max_retries)
        os.environ["RETRY_BACKOFF_FACTOR"] = str(backoff)
        os.environ["EMBEDDING_MODEL"] = embedding_model

        settings.chunk_size = int(chunk_size)
        settings.chunk_overlap = int(chunk_overlap)
        settings.top_k_retrieval = int(top_k)
        settings.request_timeout = int(request_timeout)
        settings.max_retries = int(max_retries)
        settings.retry_backoff_factor = float(backoff)
        settings.embedding_model = embedding_model

        st.success("Settings saved and applied!")


def show_about():
    st.subheader("About AI Interview Assistant")

    st.markdown("""
    **AI Interview Assistant** - Final Year University Project
    
    A comprehensive AI-powered interview preparation tool that helps students and job seekers 
    prepare for real-world job interviews through:
    
    - 📄 Resume analysis and scoring
    - 🎯 Job description matching
    - 🤖 Personalized interview question generation
    - 🎤 Mock interviews with AI evaluation
    - 📊 Detailed performance reports
    - 📈 Progress tracking
    
    **Technologies Used:**
    - **LLM:** Groq (Llama 3.1/Qwen) / Mistral / Gemini
    - **Embeddings:** Sentence Transformers (all-MiniLM-L6-v2)
    - **Vector DB:** FAISS
    - **Speech-to-Text:** Faster-Whisper
    - **Frontend:** Streamlit
    - **Database:** SQLite
    - **Framework:** LangChain (core components)
    
    **Version:** 1.0.0
    **License:** MIT
    
    ---
    
    **Note:** This application uses free APIs and open-source models.
    No paid services are required.
    """)


def clear_all_data():
    import shutil

    if os.path.exists(settings.database_path):
        os.remove(settings.database_path)

    if os.path.exists(settings.vector_store_path):
        shutil.rmtree(settings.vector_store_path)

    upload_dir = "./data/uploads"
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)

    from database import init_database

    init_database()


def show_db_stats():
    from database import get_db_context
    from database.models import (
        InterviewQuestion,
        InterviewSession,
        JobDescription,
        ResumeAnalysis,
        UserSession,
    )

    with get_db_context() as db:
        session = (
            db.query(UserSession)
            .filter(UserSession.session_id == st.session_state.user_session_id)
            .first()
        )

        if not session:
            st.info("No session found")
            return

        stats = {
            "Resumes": db.query(ResumeAnalysis)
            .filter(ResumeAnalysis.session_id == session.id)
            .count(),
            "Job Descriptions": db.query(JobDescription)
            .filter(JobDescription.session_id == session.id)
            .count(),
            "Interviews": db.query(InterviewSession)
            .filter(InterviewSession.session_id == session.id)
            .count(),
            "Questions": db.query(InterviewQuestion)
            .join(InterviewSession)
            .filter(InterviewSession.session_id == session.id)
            .count(),
        }

        for key, value in stats.items():
            st.metric(key, value)
