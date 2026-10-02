from app.services.dag_engine import execute_dag
from app.core.database import SessionLocal
from app.models import schema

def process_workflow_dag(workflow_id: str, payload: dict):
    print(f"\n[WORKER] Picked up job for Workflow ID: {workflow_id}")
    
    # Database session open karein
    db = SessionLocal()
    try:
        # Is workflow_id ki sabse latest saved version fetch karein
        workflow_version = db.query(schema.WorkflowVersion)\
            .filter(schema.WorkflowVersion.workflow_id == workflow_id)\
            .order_by(schema.WorkflowVersion.id.desc())\
            .first()
        
        if not workflow_version or not workflow_version.definition:
            print("[WORKER] Error: No saved workflow definition found!")
            return {"status": "error", "message": "Workflow definition not found. Please save canvas first."}
            
        definition = workflow_version.definition
        print(f"[WORKER] Executing Dynamic DAG with {len(definition.get('nodes', []))} nodes.")
        
        # Asal saved definition ko DAG Engine mein pass karein
        final_state = execute_dag(workflow_id, definition, payload)
        return {"status": "success", "final_state": final_state}
        
    finally:
        db.close()