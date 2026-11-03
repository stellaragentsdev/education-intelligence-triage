#!/usr/bin/env python3
"""Local-only chat UI proxy for Ollama with Copilot Studio & n8n Drag-and-Drop Workflow Engine."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = 11435
ROOT = Path(__file__).resolve().parent
CHATS_FILE = ROOT / "chats.json"
PROJECTS_DIR = ROOT.parent / "projects"
OLLAMA_LOCAL_BIN = ROOT.parent / "bin" / "ollama"
OLLAMA_API = "http://127.0.0.1:11434"


def get_ollama_bin() -> str:
    if OLLAMA_LOCAL_BIN.exists():
        return str(OLLAMA_LOCAL_BIN)
    sys_bin = shutil.which("ollama")
    if sys_bin:
        return sys_bin
    return str(OLLAMA_LOCAL_BIN)


def ensure_ollama() -> None:
    try:
        urllib.request.urlopen(f"{OLLAMA_API}/api/tags", timeout=1.5).close()
        return
    except Exception:
        pass
    env = os.environ.copy()
    models_dir = ROOT.parent / ".ollama" / "models"
    if models_dir.exists():
        env["OLLAMA_MODELS"] = str(models_dir)
    ollama_bin = get_ollama_bin()
    subprocess.Popen(
        [ollama_bin, "serve"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def get_projects_list():
    if not PROJECTS_DIR.exists():
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    res = []
    for pdir in PROJECTS_DIR.iterdir():
        if pdir.is_dir():
            cfg_file = pdir / "project.json"
            if cfg_file.exists():
                try:
                    data = json.loads(cfg_file.read_text())
                    res.append(data)
                except Exception:
                    pass
    return res


def get_project_details(project_id: str):
    pdir = PROJECTS_DIR / project_id
    if not pdir.exists():
        return None
    cfg_file = pdir / "project.json"
    data = json.loads(cfg_file.read_text()) if cfg_file.exists() else {"id": project_id, "name": project_id}

    # Read instructions
    inst_file = pdir / "instructions.md"
    data["instructions_content"] = inst_file.read_text() if inst_file.exists() else ""

    # Read knowledge files list and contents
    k_dir = pdir / "knowledge"
    knowledge_items = []
    if k_dir.exists():
        for f in k_dir.iterdir():
            if f.is_file() and not f.name.startswith("."):
                try:
                    knowledge_items.append({"name": f.name, "content": f.read_text()})
                except Exception:
                    pass
    data["knowledge_files"] = knowledge_items

    # Read skills
    s_dir = pdir / "skills"
    skills_items = []
    if s_dir.exists():
        for f in s_dir.iterdir():
            if f.is_file() and not f.name.startswith("."):
                try:
                    skills_items.append({"name": f.name, "content": f.read_text()})
                except Exception:
                    pass
    data["skills_files"] = skills_items

    # Workflows
    wf_dir = pdir / "workflows"
    workflows = []
    if wf_dir.exists():
        for f in wf_dir.iterdir():
            if f.name.endswith(".json"):
                try:
                    workflows.append(json.loads(f.read_text()))
                except Exception:
                    pass
    data["workflows_list"] = workflows

    return data


def run_graph_workflow(req_json: dict) -> dict:
    project_id = req_json.get("project_id", "startup-grant-assistant")
    nodes = req_json.get("nodes", [])
    connections = req_json.get("connections", [])
    user_input = req_json.get("input", "")

    pdir = PROJECTS_DIR / project_id
    knowledge_context = ""
    k_dir = pdir / "knowledge"
    if k_dir.exists():
        for kf in k_dir.iterdir():
            if kf.is_file() and not kf.name.startswith("."):
                try:
                    knowledge_context += f"\n--- Knowledge File: {kf.name} ---\n{kf.read_text()}\n"
                except Exception:
                    pass

    # Map node outputs
    outputs = {}
    node_logs = []

    for node in nodes:
        node_id = node.get("id")
        node_type = node.get("type")
        node_name = node.get("name", node_type)
        config = node.get("config", {})

        log_item = {"node_id": node_id, "node_name": node_name, "type": node_type, "status": "running"}
        node_logs.append(log_item)

        # Compute incoming payload from connected parent nodes
        incoming_data = user_input
        parent_conn = [c for c in connections if c.get("to") == node_id]
        if parent_conn:
            parent_id = parent_conn[0].get("from")
            if parent_id in outputs:
                incoming_data = outputs[parent_id]

        if node_type == "trigger":
            out_val = config.get("default") or user_input or "Default Trigger Input"
            outputs[node_id] = out_val
            log_item["status"] = "completed"
            log_item["output"] = out_val

        elif node_type == "knowledge":
            fname = config.get("file", "")
            content = ""
            if fname and (k_dir / fname).exists():
                content = (k_dir / fname).read_text()
            else:
                content = knowledge_context
            out_val = f"{incoming_data}\n\n[Injected Knowledge Context]:\n{content}"
            outputs[node_id] = out_val
            log_item["status"] = "completed"
            log_item["output"] = f"Injected knowledge ({len(content)} bytes)."

        elif node_type == "llm":
            model = config.get("model", "qwen2.5-coder:1.5b")
            sys_inst = config.get("system_instruction", "You are an AI assistant.")

            prompt_str = f"System Instructions:\n{sys_inst}\n\nContext & Input:\n{incoming_data}"

            try:
                ollama_req = urllib.request.Request(
                    f"{OLLAMA_API}/api/chat",
                    data=json.dumps({
                        "model": model,
                        "messages": [{"role": "user", "content": prompt_str}],
                        "stream": False
                    }).encode(),
                    method="POST",
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(ollama_req, timeout=120) as resp:
                    resp_data = json.loads(resp.read())
                    ans = resp_data.get("message", {}).get("content", "")
                    outputs[node_id] = ans
                    log_item["status"] = "completed"
                    log_item["output"] = ans
            except Exception as e:
                log_item["status"] = "failed"
                log_item["error"] = str(e)
                outputs[node_id] = f"Error: {e}"

        elif node_type == "tool":
            script_name = config.get("script", "python_runner.py")
            tool_path = pdir / "tools" / script_name
            if tool_path.exists():
                try:
                    res = subprocess.run(
                        [sys.executable, str(tool_path), incoming_data],
                        capture_output=True,
                        text=True,
                        timeout=15
                    )
                    tout = res.stdout or res.stderr
                    outputs[node_id] = tout
                    log_item["status"] = "completed"
                    log_item["output"] = tout
                except Exception as e:
                    log_item["status"] = "failed"
                    log_item["error"] = str(e)
            else:
                outputs[node_id] = f"Tool {script_name} not found."
                log_item["status"] = "skipped"

        elif node_type == "output":
            outputs[node_id] = incoming_data
            log_item["status"] = "completed"
            log_item["output"] = incoming_data

    last_out = list(outputs.values())[-1] if outputs else "No node output."
    return {"status": "ok", "logs": node_logs, "outputs": outputs, "final_output": last_out}


class Handler(BaseHTTPRequestHandler):
    headers_sent = False

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.headers_sent = True
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.headers_sent = True

    def do_GET(self) -> None:
        self.headers_sent = False
        if self.path == "/" or self.path == "/index.html":
            self._send(200, "text/html; charset=utf-8", (ROOT / "index.html").read_bytes())
            return
        if self.path in ("/education-triage", "/kalki"):
            dash = PROJECTS_DIR / "education-intelligence-triage" / "dashboard.html"
            if dash.exists():
                self._send(200, "text/html; charset=utf-8", dash.read_bytes())
                return
        if self.path == "/api/edu/students":
            try:
                edu_tools = str(PROJECTS_DIR / "education-intelligence-triage" / "tools")
                if edu_tools not in sys.path:
                    sys.path.insert(0, edu_tools)
                import telemetry_store
                import triage_engine

                students = telemetry_store.list_students()
                enriched = []
                for s in students:
                    rep = triage_engine.evaluate_student_5d(s)
                    hist = telemetry_store.get_student_history(s["id"])
                    enriched.append({"profile": s, "triage": rep, "history": hist})
                self._send(200, "application/json", json.dumps({"students": enriched}).encode())
            except Exception as exc:
                self._send(500, "application/json", json.dumps({"error": str(exc)}).encode())
            return
        if self.path == "/api/models":
            self._proxy("GET", "/api/tags")
            return
        if self.path == "/api/status":
            self._handle_status()
            return
        if self.path == "/api/chats":
            self._handle_get_chats()
            return
        if self.path == "/api/projects":
            self._send(200, "application/json", json.dumps(get_projects_list()).encode())
            return
        if self.path.startswith("/api/projects/"):
            pid = self.path[len("/api/projects/"):]
            details = get_project_details(pid)
            if details:
                self._send(200, "application/json", json.dumps(details).encode())
            else:
                self._send(404, "application/json", b'{"error":"Project not found"}')
            return

        self._send(404, "application/json", b'{"error":"Not found"}')

    def do_POST(self) -> None:
        self.headers_sent = False

        if self.path == "/api/chat":
            length = min(int(self.headers.get("Content-Length", "0")), 2_000_000)
            body = self.rfile.read(length)
            try:
                request = json.loads(body)
                request["stream"] = False
                request.setdefault("model", "qwen2.5-coder:1.5b")
                body = json.dumps(request).encode()
            except (ValueError, TypeError):
                self._send(400, "application/json", b'{"error":"Invalid JSON"}')
                return
            self._proxy("POST", "/api/chat", body)
            return

        if self.path == "/api/chat/stream":
            self._handle_chat_stream()
            return

        if self.path == "/api/models/pull":
            self._handle_model_pull_stream()
            return

        if self.path == "/api/chats":
            length = min(int(self.headers.get("Content-Length", "0")), 5_000_000)
            body = self.rfile.read(length)
            try:
                chats = json.loads(body)
                CHATS_FILE.write_text(json.dumps(chats, indent=2))
                self._send(200, "application/json", b'{"status":"ok"}')
            except Exception as e:
                self._send(400, "application/json", json.dumps({"error": str(e)}).encode())
            return

        # Add Knowledge File Endpoint
        if self.path.startswith("/api/projects/") and "/knowledge" in self.path:
            parts = self.path.split("/")
            pid = parts[3]
            length = min(int(self.headers.get("Content-Length", "0")), 5_000_000)
            body = self.rfile.read(length)
            try:
                req_data = json.loads(body)
                filename = req_data.get("filename", "knowledge.md")
                content = req_data.get("content", "")
                k_dir = PROJECTS_DIR / pid / "knowledge"
                k_dir.mkdir(parents=True, exist_ok=True)
                (k_dir / filename).write_text(content)
                self._send(200, "application/json", b'{"status":"ok"}')
            except Exception as e:
                self._send(400, "application/json", json.dumps({"error": str(e)}).encode())
            return

        # Add Skill File Endpoint
        if self.path.startswith("/api/projects/") and "/skills" in self.path:
            parts = self.path.split("/")
            pid = parts[3]
            length = min(int(self.headers.get("Content-Length", "0")), 5_000_000)
            body = self.rfile.read(length)
            try:
                req_data = json.loads(body)
                filename = req_data.get("filename", "skill.md")
                if not filename.endswith(".md"):
                    filename += ".md"
                content = req_data.get("content", "")
                s_dir = PROJECTS_DIR / pid / "skills"
                s_dir.mkdir(parents=True, exist_ok=True)
                (s_dir / filename).write_text(content)
                self._send(200, "application/json", b'{"status":"ok"}')
            except Exception as e:
                self._send(400, "application/json", json.dumps({"error": str(e)}).encode())
            return

        # Save Instructions Endpoint
        if self.path.startswith("/api/projects/") and "/instructions" in self.path:
            parts = self.path.split("/")
            pid = parts[3]
            length = min(int(self.headers.get("Content-Length", "0")), 2_000_000)
            body = self.rfile.read(length)
            try:
                req_data = json.loads(body)
                content = req_data.get("content", "")
                pdir = PROJECTS_DIR / pid
                (pdir / "instructions.md").write_text(content)
                self._send(200, "application/json", b'{"status":"ok"}')
            except Exception as e:
                self._send(400, "application/json", json.dumps({"error": str(e)}).encode())
            return

        # Graph Workflow Execution Endpoint
        if self.path == "/api/workflows/execute-graph":
            length = min(int(self.headers.get("Content-Length", "0")), 5_000_000)
            body = self.rfile.read(length)
            try:
                req_data = json.loads(body)
                result = run_graph_workflow(req_data)
                self._send(200, "application/json", json.dumps(result).encode())
            except Exception as e:
                self._send(400, "application/json", json.dumps({"error": str(e)}).encode())
            return

        # Education Intelligence: Arcade Telemetry & Bio-Psycho-Social Check-in Endpoints
        if self.path in ("/api/edu/arcade-telemetry", "/api/edu/checkin"):
            length = min(int(self.headers.get("Content-Length", "0")), 1_000_000)
            body = self.rfile.read(length)
            try:
                edu_tools = str(PROJECTS_DIR / "education-intelligence-triage" / "tools")
                if edu_tools not in sys.path:
                    sys.path.insert(0, edu_tools)
                import telemetry_store
                import triage_engine

                req_data = json.loads(body)
                sid = req_data.get("student_id", "STU-101")
                if self.path == "/api/edu/arcade-telemetry":
                    updated = telemetry_store.record_arcade_event(
                        sid,
                        req_data.get("game_type", "go_nogo_impulse"),
                        int(req_data.get("score", 75)),
                        req_data.get("metrics", {}),
                    )
                else:
                    updated = telemetry_store.record_checkin(sid, req_data)

                if not updated:
                    self._send(404, "application/json", b'{"error":"Student not found"}')
                    return
                rep = triage_engine.evaluate_student_5d(updated)
                hist = telemetry_store.get_student_history(sid)
                self._send(
                    200,
                    "application/json",
                    json.dumps({"status": "ok", "profile": updated, "triage": rep, "history": hist}).encode(),
                )
            except Exception as exc:
                self._send(400, "application/json", json.dumps({"error": str(exc)}).encode())
            return

        self._send(404, "application/json", b'{"error":"Not found"}')

    def do_DELETE(self) -> None:
        self.headers_sent = False
        if self.path.startswith("/api/models/"):
            model_name = self.path[len("/api/models/"):]
            body = json.dumps({"name": model_name}).encode()
            self._proxy("DELETE", "/api/delete", body)
            return

        # Delete Knowledge File
        if self.path.startswith("/api/projects/") and "/knowledge/" in self.path:
            parts = self.path.split("/")
            pid = parts[3]
            fname = urllib.parse.unquote(parts[5])
            fpath = PROJECTS_DIR / pid / "knowledge" / fname
            if fpath.exists():
                fpath.unlink()
                self._send(200, "application/json", b'{"status":"deleted"}')
            else:
                self._send(404, "application/json", b'{"error":"File not found"}')
            return

        # Delete Skill File
        if self.path.startswith("/api/projects/") and "/skills/" in self.path:
            parts = self.path.split("/")
            pid = parts[3]
            fname = urllib.parse.unquote(parts[5])
            fpath = PROJECTS_DIR / pid / "skills" / fname
            if fpath.exists():
                fpath.unlink()
                self._send(200, "application/json", b'{"status":"deleted"}')
            else:
                self._send(404, "application/json", b'{"error":"File not found"}')
            return

        self._send(404, "application/json", b'{"error":"Not found"}')

    def _handle_status(self) -> None:
        try:
            req = urllib.request.Request(f"{OLLAMA_API}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read())
                models = [m.get("name") for m in data.get("models", [])]
                payload = json.dumps({
                    "status": "online",
                    "binary": get_ollama_bin(),
                    "models": models,
                    "model_count": len(models),
                    "projects_count": len(get_projects_list())
                }).encode()
                self._send(200, "application/json", payload)
        except Exception as exc:
            payload = json.dumps({
                "status": "offline",
                "error": str(exc),
                "binary": get_ollama_bin(),
                "models": [],
                "model_count": 0,
                "projects_count": len(get_projects_list())
            }).encode()
            self._send(200, "application/json", payload)

    def _handle_get_chats(self) -> None:
        if CHATS_FILE.exists():
            try:
                self._send(200, "application/json", CHATS_FILE.read_bytes())
                return
            except Exception:
                pass
        self._send(200, "application/json", b"[]")

    def _handle_chat_stream(self) -> None:
        length = min(int(self.headers.get("Content-Length", "0")), 2_000_000)
        raw_body = self.rfile.read(length)
        try:
            req_json = json.loads(raw_body)
            req_json["stream"] = True
            req_json.setdefault("model", "qwen2.5-coder:1.5b")

            project_id = req_json.get("project_id")
            if project_id:
                pdetails = get_project_details(project_id)
                if pdetails:
                    k_str = ""
                    for kf in pdetails.get("knowledge_files", []):
                        k_str += f"\n--- Knowledge File: {kf['name']} ---\n{kf['content']}\n"
                    if k_str:
                        msgs = req_json.get("messages", [])
                        if msgs and msgs[0]["role"] == "system":
                            msgs[0]["content"] += f"\n\nProject Knowledge Base:\n{k_str}"
                        else:
                            msgs.insert(0, {"role": "system", "content": f"Project Knowledge Base:\n{k_str}"})

            body = json.dumps(req_json).encode()
        except Exception:
            self._send(400, "application/json", b'{"error":"Invalid JSON"}')
            return

        try:
            req = urllib.request.Request(
                f"{OLLAMA_API}/api/chat",
                data=body,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=300) as response:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.headers_sent = True

                while True:
                    line = response.readline()
                    if not line:
                        break
                    self.wfile.write(b"data: " + line.strip() + b"\n\n")
                    self.wfile.flush()
        except Exception as exc:
            err_json = json.dumps({"error": f"Streaming failed: {exc}"}).encode()
            if not self.headers_sent:
                self._send(503, "application/json", err_json)

    def _handle_model_pull_stream(self) -> None:
        length = min(int(self.headers.get("Content-Length", "0")), 100_000)
        raw_body = self.rfile.read(length)
        try:
            req_json = json.loads(raw_body)
            req_json["stream"] = True
            body = json.dumps(req_json).encode()
        except Exception:
            self._send(400, "application/json", b'{"error":"Invalid JSON"}')
            return

        try:
            req = urllib.request.Request(
                f"{OLLAMA_API}/api/pull",
                data=body,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=1800) as response:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.headers_sent = True

                while True:
                    line = response.readline()
                    if not line:
                        break
                    self.wfile.write(b"data: " + line.strip() + b"\n\n")
                    self.wfile.flush()
        except Exception as exc:
            err_json = json.dumps({"error": f"Pull failed: {exc}"}).encode()
            if not self.headers_sent:
                self._send(503, "application/json", err_json)

    def _proxy(self, method: str, path: str, body: bytes | None = None) -> None:
        try:
            req = urllib.request.Request(
                f"{OLLAMA_API}{path}",
                data=body,
                method=method,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=300) as response:
                self._send(response.status, "application/json", response.read())
        except urllib.error.HTTPError as exc:
            self._send(exc.code, "application/json", exc.read())
        except Exception as exc:
            payload = json.dumps({"error": f"Ollama unavailable: {exc}"}).encode()
            self._send(503, "application/json", payload)

    def log_message(self, _format: str, *_args: object) -> None:
        return


if __name__ == "__main__":
    ensure_ollama()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Stellar Ollama Proxy running on http://{HOST}:{PORT}")
    server.serve_forever()
