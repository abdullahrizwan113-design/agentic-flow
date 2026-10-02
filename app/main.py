from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from sqlalchemy.orm import Session
from app.core.database import engine, get_db
from app.models import schema
from app.services.worker import process_workflow_dag

schema.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Agentic Flow API",
    description="AI-native visual automation platform engine",
    version="1.0.0"
)

# CORS Middleware taake Next.js requests block na hon
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print("[WEBSOCKET] Client connected")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print("[WEBSOCKET] Client disconnected")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"status": "online", "message": "Agentic Flow Engine is running!"}

@app.post("/api/workflows/save")
async def save_workflow(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    workflow_id = payload.get("workflow_id", "demo_123")
    
    db_workflow = db.query(schema.Workflow).filter(schema.Workflow.id == workflow_id).first()
    if not db_workflow:
        db_workflow = schema.Workflow(id=workflow_id, title="My Agentic Flow")
        db.add(db_workflow)
        db.commit()

    new_version = schema.WorkflowVersion(
        workflow_id=workflow_id,
        definition={"nodes": payload.get("nodes"), "edges": payload.get("edges")}
    )
    db.add(new_version)
    db.commit()
    
    return {"status": "success", "message": "Workflow successfully saved to SQLite Database!"}

@app.post("/api/webhook/{workflow_id}")
async def ingest_webhook(workflow_id: str, request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    background_tasks.add_task(process_workflow_dag, workflow_id, payload)
    
    return {
        "status": "success",
        "message": "Workflow trigger queued.",
        "workflow_id": workflow_id
    }

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/internal/broadcast")
async def internal_broadcast(payload: dict):
    await manager.broadcast(payload)
    return {"status": "broadcasted"}