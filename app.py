import streamlit as st
import os
import sys
import time
import nest_asyncio
import asyncio
from google.cloud import pubsub_v1
from google.cloud import storage
from vertexai.preview import reasoning_engines
import vertexai
import json
import re
from ultralytics import YOLO

from mcp_playwright_agent.agent import root_agent, demo_agent

from mcp_playwright_agent.demo_agent import login

# --- 1. SYSTEM CONFIGURATION ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

nest_asyncio.apply()

os.environ["PYTHONUNBUFFERED"] = "1"  # Prevents hanging on Windows

# --- 2. PROJECT SETTINGS ---
PROJECT_ID = 'capstonec06-474100'
LOCATION = "asia-northeast1"
SUBSCRIPTION_ID = "ocr-results-sub"
BUCKET_NAME = "extracted_data_bucket"

st.set_page_config(page_title="Auto-Order Agent", page_icon="📦", layout="wide")
st.title("📦 Auto-Order Agent")


# --- 4. AGENT INITIALIZATION ---
@st.cache_resource
def init_resources():
    vertexai.init(project=PROJECT_ID, location=LOCATION)


def create_app():
    print("🔄 SYSTEM: Starting new Agent...")
    # return reasoning_engines.AdkApp(agent=root_agent, enable_tracing=True)
    return reasoning_engines.AdkApp(agent=demo_agent, enable_tracing=True)


def destroy_app():
    """Forcefully destroy the ADK app and all its connections."""
    app = st.session_state.get("app_instance")
    if not app:
        return

    # 1. Try graceful shutdown methods
    for method in ["close", "stop", "shutdown", "__del__"]:
        if hasattr(app, method):
            try:
                getattr(app, method)()
            except Exception as e:
                print(f"App {method}() failed: {e}")

    # 2. Kill internal processes if app tracks them
    if hasattr(app, "_processes"):
        for proc in app._processes:
            try:
                proc.terminate()
                proc.kill()
            except:
                pass

    # 3. Force garbage collection
    st.session_state.pop("app_instance", None)
    st.session_state.pop("session_id", None)

def create_demo_app():
    pass

def ensure_new_session():
    """Recreate agent app and start a fresh session."""
    destroy_app()

    try:
        # Remove existing app instance if present
        if "app_instance" in st.session_state:
            try:
                del st.session_state.app_instance

            except Exception:
                pass

        init_resources()
        st.session_state.app_instance = create_app()

        # Create a fresh session synchronously (existing pattern in file)
        session = st.session_state.app_instance.create_session(user_id="user")
        st.session_state.session_id = session.id

        print("🔄 New agent session created:", st.session_state.session_id)
        return True
    except Exception as e:
        st.error(f"Session Creation Error: {e}")
        return False


# Session Management
if "app_instance" not in st.session_state:
    init_resources()
    st.session_state.app_instance = create_app()

if "session_id" not in st.session_state:
    try:
        session = st.session_state.app_instance.create_session(user_id="user")
        st.session_state.session_id = session.id
    except Exception as e:
        st.error(f"Session Error: {e}")

if "messages" not in st.session_state:
    st.session_state.messages = []


# --- 5. UPLOAD & PUBSUB LOGIC ---

def upload_to_gcs(file_obj):
    """Uploads file to the raw_photos/ folder in GCS"""
    try:
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(BUCKET_NAME)

        # Add folder prefix
        destination_blob_name = f"raw_photos/{file_obj.name}"

        blob = bucket.blob(destination_blob_name)
        blob.upload_from_file(file_obj)
        print(f"✅ Uploaded to: {destination_blob_name}")
        ensure_new_session()
        return True
    except Exception as e:
        st.error(f"GCS Upload Error: {e}")
        return False


def listen_for_ocr_result(timeout=60):
    """Listens for Pub/Sub message from Cloud Function"""
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

    start_time = time.time()
    st.toast("⏳ Waiting for Cloud Function OCR...", icon="☁️")

    while (time.time() - start_time) < timeout:
        try:
            response = subscriber.pull(
                request={"subscription": subscription_path, "max_messages": 1},
                timeout=2.0
            )

            if response.received_messages:
                msg = response.received_messages[0]
                payload = msg.message.data.decode("utf-8")
                subscriber.acknowledge(request={"subscription": subscription_path, "ack_ids": [msg.ack_id]})
                return payload

        except Exception as e:
            if "DeadlineExceeded" not in str(e):
                print(f"PubSub Check: {e}")

        time.sleep(1)

    return None


def check_oil_status(ocr_json_string):
    """Parses OCR and returns style settings for the UI"""
    try:
        data = json.loads(ocr_json_string)
        material = data.get("material", "Unknown")

        # Logic extracted from Cloud Function
        prefix = re.match(r'^([A-Za-z]+)(?=\d)', material)
        material_type = prefix.group(1) if prefix else "Unknown"

        if not material_type:
            return material, "⚠️ Unknown Material", st.info

        # Decision Logic
        if material_type[0] == 'S' and material_type != 'SUS':
            return material, "🛢️ APPLY OIL REQUIRED", st.error  # Red/Error box for visibility
        elif material_type[0] == 'A':
            return material, "✅ NO OIL NEEDED", st.success  # Green box
        else:
            return material, "🛢️ APPLY OIL REQUIRED", st.error  # Default to caution

    except Exception as e:
        return "Error", "⚠️ Check Data", st.warning


def clean_scene():
    """
    Stop the agent, clear UI state and temp files, and recreate a fresh local app/session
    without stopping the Streamlit app itself.
    """
    # 1. Cancel any running async tasks
    try:
        loop = asyncio.get_event_loop()
        for task in asyncio.all_tasks(loop):
            if not task.done():
                task.cancel()
    except Exception as e:
        print(f"Clean: async task cancellation failed: {e}")

    # 2. Explicitly close/stop the app instance before destroying session
    app = st.session_state.get("app_instance")
    if app:
        try:
            if hasattr(app, "close"):
                app.close()
            elif hasattr(app, "stop"):
                app.stop()
        except Exception as e:
            print(f"Clean: app close failed: {e}")

    # 3. Tear down remote session if any
    try:
        destroy_app()
    except Exception as e:
        print(f"Clean: destroy_current_session failed: {e}")

    # 4. Remove local app_instance and session id
    st.session_state.pop("app_instance", None)
    st.session_state.pop("session_id", None)

    # 5. Clear UI / workflow keys (keep global settings if any)
    keys_to_clear = ("messages", "auto_trigger_prompt", "yolo_camera", "yolo_upload")
    for k in keys_to_clear:
        st.session_state.pop(k, None)

    # 6. Remove temporary files created by detection flow
    try:
        temp_path = "temp_capture.jpg"
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception as e:
        print(f"Clean: temp file removal failed: {e}")

    # 7. Small delay to ensure cleanup completes
    time.sleep(0.5)

    # 8. Reinitialize resources and create a fresh agent session
    try:
        init_resources()
        st.session_state.app_instance = create_app()
        session = st.session_state.app_instance.create_session(user_id="user")
        st.session_state.session_id = session.id
        st.session_state.messages = []
        st.success("Scene cleaned and agent restarted.")
    except Exception as e:
        st.error(f"Clean Scene Error: {e}")

    # 9. Refresh UI to reflect the cleared state
    st.rerun()


# --- 6. AGENT EXECUTION (TIMELINE MODE) ---
def run_agent(user_input, auto_mode=False):
    # 1. User Message
    prefix = "🤖 [OCR START] " if auto_mode else "👤 "
    st.session_state.messages.append({"role": "user", "content": f"{prefix}{user_input}"})

    with st.chat_message("user"):
        st.markdown(f"{prefix}{user_input}")

    # 2. Assistant Message (Stream)
    with st.chat_message("assistant"):

        # Це змінна для всього тексту (щоб зберегти в історію в кінці)
        full_transcript = ""

        # Це змінна для поточного шматка тексту (між діями)
        current_text_block = ""

        # Створюємо перше "місце" для тексту
        text_placeholder = st.empty()

        try:
            app = st.session_state.app_instance
            print(f"👉 Executing: {user_input[:50]}...")

            response_generator = app.stream_query(
                user_id="user",
                session_id=st.session_state.session_id,
                message=user_input,
            )

            for event in response_generator:
                print(f"📥 RAW: {event}")

                # Розбір подій
                if isinstance(event, dict) and "content" in event:
                    parts = event["content"].get("parts", [])

                    for part in parts:
                        # --- ЯКЩО ЦЕ ТЕКСТ (ДУМКА АГЕНТА) ---
                        if "text" in part:
                            text_chunk = part["text"]
                            current_text_block += text_chunk
                            full_transcript += text_chunk
                            # Оновлюємо поточний текстовий блок
                            text_placeholder.markdown(current_text_block + "▌")

                        # --- ЯКЩО ЦЕ ІНСТРУМЕНТ (ДІЯ) ---
                        if "function_call" in part:
                            # 1. Спочатку "закриваємо" попередній текст
                            if current_text_block:
                                text_placeholder.markdown(current_text_block)
                                current_text_block = ""  # Очищаємо буфер для наступного тексту
                            else:
                                text_placeholder.empty()  # Прибираємо курсор, якщо тексту не було

                            # 2. Малюємо блок інструменту
                            fname = part["function_call"].get("name", "tool")
                            args = part["function_call"].get("args", {})

                            # Відображаємо гарний блок дії
                            with st.status(f"⚡ Action: **{fname}**", expanded=False) as status:
                                st.code(f"Args: {args}", language="json")
                                status.update(state="complete")

                            # 3. Створюємо НОВЕ місце для тексту, який буде ПІСЛЯ дії
                            text_placeholder = st.empty()

                # Обробка інших форматів (на всяк випадок)
                elif hasattr(event, "text"):
                    current_text_block += event.text
                    full_transcript += event.text
                    text_placeholder.markdown(current_text_block + "▌")

            # Фіналізація останнього шматка тексту
            text_placeholder.markdown(current_text_block)

            if not full_transcript:
                st.success("✅ Action completed (No text response).")
                full_transcript = "[Action Completed]"

            # Зберігаємо повну історію
            st.session_state.messages.append({"role": "assistant", "content": full_transcript})

        except Exception as e:
            st.error(f"⚠️ Connection Lost: {e}")
            if st.button("🔄 Reconnect Agent"):
                try:
                    del st.session_state.app_instance
                except:
                    pass
                st.session_state.app_instance = create_app()
                st.rerun()


# --- 7. UI LAYOUT ---

# --- SIDEBAR (UPLOAD) ---
with st.sidebar:
    st.header("📤 1. File Upload")
    uploaded_file = st.file_uploader("Select Invoice/Order (Image/PDF)", type=['png', 'jpg', 'jpeg', 'pdf'])

    if uploaded_file:
        # Standard Streamlit pattern: Button triggers the flow
        if st.button("🚀 Process & Run", type="primary"):
            ocr_result = None  # Variable to store result outside the status block

            # --- PHASE 1: LOADING (Collapsible) ---
            with st.status("Processing...", expanded=True) as status:
                st.write("Uploading to Google Cloud Storage...")
                if upload_to_gcs(uploaded_file):
                    st.write("✅ Upload complete.")

                    st.write("Waiting for OCR (Pub/Sub)...")
                    ocr_result = listen_for_ocr_result(timeout=60)  # Store result in variable

                    if ocr_result:
                        status.update(label="✅ processing Complete!", state="complete", expanded=False)
                    else:
                        status.update(label="❌ OCR Timeout", state="error")
                else:
                    status.update(label="❌ Upload Failed", state="error")

            # --- PHASE 2: RESULTS (Always Visible) ---
            # This runs OUTSIDE the status block, so it is always visible
            if ocr_result:
                # 1. Run the Logic
                mat_name, oil_msg, display_box = check_oil_status(ocr_result)

                # 2. Display BIG Visual Indicators
                st.divider()

                # Use columns to make it stand out
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(f"**Material:**\n`{mat_name}`")
                with col2:
                    # This box will be Bright Red (st.error) or Green (st.success)
                    display_box(f"**{oil_msg}**", icon="🔧")

                st.divider()

                # 3. Optional: Show raw data in an expander (hidden by default to keep UI clean)
                with st.expander("View Raw OCR Data"):
                    st.code(ocr_result, language="json")

                # 4. Trigger Agent
                prompt = f"Use this OCR data to process the order immediately. Data: {ocr_result}"
                st.session_state.auto_trigger_prompt = prompt

    st.divider()
    st.header("🛠️ Controls")
    if st.button("🧹 Clean Scene (Reset Agent)"):
        clean_scene()
    if st.button("🔴 Hard Reset (Kill Processes)"):
        os.system("taskkill /F /IM node.exe /T")
        os.system("taskkill /F /IM python.exe /T")
        st.session_state.clear()
        st.rerun()

# --- MAIN CHAT ---
col_chat, col_detect = st.columns([2, 1], gap="large")

with col_chat:
    st.subheader("💬 Agent Chat Log")

    # 1. Show history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 2. Check for Auto-Start from Sidebar (THIS MOVES IT TO THE RIGHT)
    if "auto_trigger_prompt" in st.session_state and st.session_state.auto_trigger_prompt:
        # Run the agent in the main area
        run_agent(st.session_state.auto_trigger_prompt, auto_mode=True)
        # Clear the trigger so it doesn't run twice
        st.session_state.auto_trigger_prompt = None

with col_detect:
    # --- YOLO DETECTION ---
    st.subheader("🔍 Part Detection")

    # Camera input for YOLO
    camera_temp = st.camera_input("Capture Image for Part Detection", key="yolo_camera")

    # Dropdown for manual upload
    uploaded_yolo_file = st.file_uploader("Or Upload Image for Part Detection", type=['png', 'jpg', 'jpeg'],
                                          key="yolo_upload")
    if uploaded_yolo_file:
        camera_temp = uploaded_yolo_file

    if camera_temp:
        # Save to a temp file
        with open("temp_capture.jpg", "wb") as f:
            f.write(camera_temp.getbuffer())

        st.info("Running part detection...")

        # Run YOLO inference
        model_path = "my_model_latest.pt"
        model = YOLO(model_path, task='detect')
        labels = model.names
        results = model.predict(source="temp_capture.jpg", conf=0.5, save=False)

        # Display results
        for result in results:
            annotated_frame = result.plot()
            st.image(annotated_frame, caption="Detected Parts")

            # List detected parts
            if result.boxes:
                st.markdown("**Detected Parts:**")
                box = result.boxes[0]
                cls_id = int(box.cls[0])
                part_name = labels.get(cls_id, "Unknown")
                conf_score = box.conf[0].item()
                st.write(f"This is a {part_name}")

            else:
                st.write("No parts detected.")
