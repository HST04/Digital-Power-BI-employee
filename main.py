import os
import shutil
import uuid
import json
import asyncio
import re
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.profiler import profile_excel_file, format_profile_as_markdown
from app.agent import root_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from app.app_utils.pbip_generator import generate_pbip_zip

# Initialize FastAPI App
app = FastAPI(title="Digital Power BI Employee Backend")

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Session Service for ADK
session_service = InMemorySessionService()

# Directory for file uploads and pbip projects
UPLOAD_DIR = os.path.abspath("temp_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

PBIP_DIR = os.path.abspath("temp_pbip")
os.makedirs(PBIP_DIR, exist_ok=True)

# Serve static files (Frontend app)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_index():
    index_path = os.path.join("static", "index.html")
    if not os.path.exists(index_path):
        return HTMLResponse(
            content="<h1>Frontend files not found. Ensure static/index.html is created.</h1>",
            status_code=404
        )
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    filename = file.filename
    if not filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload an Excel workbook (.xlsx or .xls)."
        )
    
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(filename)[1]
    saved_filename = f"{file_id}{ext}"
    saved_path = os.path.join(UPLOAD_DIR, saved_filename)
    
    try:
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Programmatically profile the spreadsheet
        profile_data = profile_excel_file(saved_path)
        
        if "error" in profile_data:
            raise HTTPException(status_code=500, detail=profile_data["error"])
            
        profile_markdown = format_profile_as_markdown(profile_data)
        
        return {
            "status": "success",
            "file_id": file_id,
            "original_filename": filename,
            "sheet_names": list(profile_data["sheets"].keys()),
            "profile_markdown": profile_markdown,
            "profile_data": profile_data
        }
    except Exception as e:
        if os.path.exists(saved_path):
            os.remove(saved_path)
        raise HTTPException(status_code=500, detail=f"Failed to profile spreadsheet: {str(e)}")

def extract_json_from_schema(schema_text: str) -> dict:
    if not schema_text:
        return {}
    try:
        return json.loads(schema_text)
    except Exception:
        match = re.search(r'```json\s*(.*?)\s*```', schema_text, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
    return {}

@app.post("/analyze")
async def analyze_model(
    file_id: str = Form(...),
    user_prompt: str = Form(...),
    profile_data_str: str = Form(...)
):
    try:
        profile_data = json.loads(profile_data_str)
        profile_markdown = format_profile_as_markdown(profile_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid profile metadata: {str(e)}")
        
    session_id = f"session_{uuid.uuid4().hex[:12]}"
    user_id = "powerbi_user"
    
    # Instantiate initial session state
    initial_state = {
        "user_prompt": user_prompt,
        "excel_profile": profile_markdown
    }
    
    await session_service.create_session(
        app_name="powerbi_developer_system",
        user_id=user_id,
        session_id=session_id,
        state=initial_state
    )
    
    async def sse_event_generator():
        # Setup the ADK execution runner
        runner = Runner(
            agent=root_agent,
            app_name="powerbi_developer_system",
            session_service=session_service
        )
        
        yield f"data: {json.dumps({'status': 'started', 'message': 'Bootstrapping multi-agent system...'})}\n\n"
        await asyncio.sleep(0.3)
        
        current_agent = None
        
        try:
            # Run the agent pipeline asynchronously
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(role="user", parts=[types.Part.from_text(text="Please compile the developer handbook and schema json.")]),
            ):
                author = event.author
                # Detect which agent is currently executing based on event author names
                if author and author != current_agent and author != "powerbi_user":
                    current_agent = author
                    display_name = author.replace("_", " ").title()
                    yield f"data: {json.dumps({'status': 'agent_change', 'agent': author, 'message': f'{display_name} is running...'})}\n\n"
                
                # Check for intermediate messages or events we might want to log
                await asyncio.sleep(0.01)
                
            # Retrieve final session state
            session = await session_service.get_session(
                app_name="powerbi_developer_system",
                user_id=user_id,
                session_id=session_id
            )
            
            final_report = session.state.get("final_output")
            schema_json_str = session.state.get("schema_json")
            
            pbip_download_url = None
            if schema_json_str:
                schema_dict = extract_json_from_schema(schema_json_str)
                if schema_dict:
                    zip_bytes = generate_pbip_zip(schema_dict)
                    zip_filename = f"Project_{session_id}.pbip.zip"
                    zip_path = os.path.join(PBIP_DIR, zip_filename)
                    with open(zip_path, "wb") as f:
                        f.write(zip_bytes)
                    pbip_download_url = f"/download/{zip_filename}"
            
            if not final_report:
                final_report = "Error: Final compiler agent did not return a report. Please verify your Gemini API key in `app/.env` and try again."
                yield f"data: {json.dumps({'status': 'error', 'message': final_report})}\n\n"
            else:
                yield f"data: {json.dumps({'status': 'completed', 'report': final_report, 'pbip_url': pbip_download_url})}\n\n"
                
        except Exception as e:
            # Yield error event
            yield f"data: {json.dumps({'status': 'error', 'message': f'Engine error: {str(e)}'})}\n\n"
            
    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")

@app.get("/download/{filename}")
async def download_pbip(filename: str):
    file_path = os.path.join(PBIP_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/zip", filename="PowerBI_Project.pbip.zip")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
