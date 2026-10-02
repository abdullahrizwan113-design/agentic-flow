import time
import requests
import os # NAYA IMPORT
from openai import OpenAI

# Groq API configuration (Ab key hardcoded nahi hai)
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("OPENAI_API_KEY", "your-placeholder-key")
)

def update_frontend_status(node_id, status, result=None):
    payload = {"node_id": node_id, "status": status}
    if result:
        payload["result"] = result
    try:
        requests.post("http://localhost:8000/api/internal/broadcast", json=payload, timeout=2)
    except Exception as e:
        print(f"Telemetry error: {e}")

def execute_dag(workflow_id: str, definition: dict, initial_payload: dict):
    nodes = {node["id"]: node for node in definition.get("nodes", [])}
    edges = definition.get("edges", [])

    trigger_nodes = [n for n in nodes.values() if n.get("type") in ["trigger", "input"]]
    if not trigger_nodes:
        return {"error": "No trigger node found"}

    current_node = trigger_nodes[0]
    node_outputs = {current_node["id"]: initial_payload}
    
    update_frontend_status(current_node["id"], "success", initial_payload)
    print(f"\n[ENGINE] Started Workflow: {workflow_id}")

    while True:
        connected_edges = [e for e in edges if e["source"] == current_node["id"]]
        
        # --- ROUTER LOGIC: Choosing the path (True / False) ---
        if current_node.get("type") == "router":
            node_data = current_node.get("data", {})
            keyword = node_data.get("keyword", "").lower()
            input_text = str(node_outputs.get(current_node["id"], "")).lower()
            
            # Condition check
            condition_met = keyword in input_text if keyword else True
            print(f"🔀 [ROUTER] Checking if '{keyword}' is in input. Result: {condition_met}")
            
            # Filter edges based on condition
            valid_edges = []
            for e in connected_edges:
                handle = e.get("sourceHandle")
                if condition_met and handle == "true":
                    valid_edges.append(e)
                elif not condition_met and handle == "false":
                    valid_edges.append(e)
            connected_edges = valid_edges

        if not connected_edges:
            print("🏁 Workflow Execution Completed!\n")
            break

        # Proceed with the valid edge
        edge = connected_edges[0]
        target_id = edge["target"]
        target_node = nodes[target_id]
        input_data = node_outputs[current_node["id"]]
        node_type = target_node.get("type", "default")
        
        update_frontend_status(target_id, "running")
        
        # --- EXECUTE NODE BASED ON TYPE ---
        if node_type in ["aiModel", "ai_agent"]:
            node_data = target_node.get("data", {})
            custom_prompt = node_data.get("prompt", "You are a helpful AI assistant.")
            print(f"🤖 [AI TASK] Executing Llama 3 via Groq...")
            try:
                response = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[{"role": "system", "content": custom_prompt}, {"role": "user", "content": str(input_data)}]
                )
                output_data = {"ai_response": response.choices[0].message.content}
            except Exception as e:
                output_data = {"ai_response": f"(Error) {str(e)}"}
                time.sleep(2)

        elif node_type == "http":
            node_data = target_node.get("data", {})
            api_url = node_data.get("url", "https://jsonplaceholder.typicode.com/todos/1")
            print(f"🌐 [HTTP TASK] Fetching: {api_url}")
            try:
                res = requests.get(api_url, timeout=5)
                output_data = {"http_response": res.json() if res.headers.get('content-type', '').startswith('application/json') else res.text}
            except Exception as e:
                output_data = {"error": str(e)}

        elif node_type == "router":
            print(f"🔀 [ROUTER TASK] Reached router, preparing to split...")
            output_data = input_data # Data agle step tak forward kar raha hai
            time.sleep(0.5)
            
        else:
            time.sleep(1)
            output_data = {"action_result": f"Action completed using {input_data}"}

        # Update telemetry and move to next node
        update_frontend_status(target_id, "success", output_data)
        node_outputs[target_id] = output_data
        current_node = target_node

    return node_outputs