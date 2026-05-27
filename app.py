import os
import json
import uuid
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Import the core agent logic
from main import (
    make_initial_state,
    step_web_search,
    step_research_summary,
    step_email_generation,
    step_format_and_save
)
from utils.logger import get_logger

logger = get_logger("app")

# Thread-safe in-memory store for agent execution status and logs
agent_runs = {}
runs_lock = threading.Lock()

def run_agent_in_background(run_id, topic):
    logger.info(f"Starting background run {run_id} for topic: {topic}")
    
    with runs_lock:
        run_info = agent_runs[run_id]
        
    state = make_initial_state(topic)
    
    def log_to_run(message):
        logger.info(f"[{run_id}] {message}")
        with runs_lock:
            run_info["logs"].append(message)

    try:
        # Step 1: Web Search
        with runs_lock:
            run_info["step"] = "web_search"
        log_to_run("Step 1/4: Querying web search engines (Tavily/DuckDuckGo)...")
        state = step_web_search(state)
        
        search_results = state.get("search_results") or ""
        log_to_run(f"Web search completed successfully. Retrieved {len(search_results)} characters of content.")

        # Step 2: Synthesize Research
        with runs_lock:
            run_info["step"] = "research_summary"
        log_to_run("Step 2/4: Synthesizing search results using Groq LLM...")
        state = step_research_summary(state)
        
        research_summary = state.get("research_summary") or ""
        log_to_run(f"Research summary generated successfully ({len(research_summary)} characters).")

        # Step 3: Draft Email
        with runs_lock:
            run_info["step"] = "email_generation"
        log_to_run("Step 3/4: Drafting structured email template using Groq LLM...")
        state = step_email_generation(state)
        
        email_body = state.get("email_body") or ""
        log_to_run(f"Email body drafted successfully ({len(email_body)} characters).")

        # Step 4: Save & Format
        with runs_lock:
            run_info["step"] = "format_and_save"
        log_to_run("Step 4/4: Formatting output and validating structure...")
        state = step_format_and_save(state)

        # Check for errors in state
        errors = state.get("errors", [])
        if errors:
            err_msg = "; ".join(errors)
            log_to_run(f"Validation failed or errors encountered: {err_msg}")
            with runs_lock:
                run_info["status"] = "failed"
            return

        formatted_email = state.get("formatted_email") or ""
        output_path = state.get("output_path") or ""
        log_to_run(f"Email saved to disk: {output_path}")
        
        with runs_lock:
            run_info["status"] = "completed"
            run_info["step"] = "done"
            run_info["result"] = {
                "formatted_email": formatted_email,
                "research_summary": research_summary,
                "output_path": str(output_path)
            }
            run_info["logs"].append("Execution finished successfully!")

    except Exception as e:
        logger.exception(f"Fatal error in background run {run_id}")
        log_to_run(f"Error: {str(e)}")
        with runs_lock:
            run_info["status"] = "failed"


class DashboardRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if path == "/":
            # Serve the dashboard index.html
            try:
                with open("index.html", "r", encoding="utf-8") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error loading index.html: {e}".encode("utf-8"))
                
        elif path == "/api/status":
            query_params = parse_qs(parsed_url.query)
            run_id = query_params.get("id", [None])[0]
            
            if not run_id:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "Missing run ID"}')
                return
                
            with runs_lock:
                run_info = agent_runs.get(run_id)
                
            if not run_info:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'{"error": "Run session not found"}')
                return
                
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            with runs_lock:
                # Create a copy of the dictionary to release the lock quickly
                run_data = json.dumps(run_info)
            self.wfile.write(run_data.encode("utf-8"))
            
        else:
            # Fallback to 404
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if path == "/api/run":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            
            try:
                body = json.loads(post_data.decode("utf-8"))
                topic = body.get("topic", "").strip()
            except Exception:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "Invalid JSON body"}')
                return
                
            if not topic:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "Topic cannot be empty"}')
                return
                
            # Create a new run session
            run_id = str(uuid.uuid4())
            with runs_lock:
                agent_runs[run_id] = {
                    "id": run_id,
                    "topic": topic,
                    "status": "running",
                    "step": "web_search",
                    "logs": ["Agent session initialized.", f"Target topic: '{topic}'"],
                    "result": None
                }
                
            # Start background thread to run the agent pipeline
            thread = threading.Thread(
                target=run_agent_in_background,
                args=(run_id, topic),
                daemon=True
            )
            thread.start()
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"id": run_id}).encode("utf-8"))
            
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")


def start_http_server(port):
    try:
        server = HTTPServer(('0.0.0.0', port), DashboardRequestHandler)
        logger.info(f"Dashboard web server listening on port {port}...")
        server.serve_forever()
    except Exception as e:
        logger.error(f"Failed to start web server: {e}")


if __name__ == "__main__":
    # Render sets PORT environment variable, defaults to 10000
    port = int(os.environ.get("PORT", 10000))
    start_http_server(port)
