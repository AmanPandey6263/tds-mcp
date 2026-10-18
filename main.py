import hashlib

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

EMAIL = "24f3004942@ds.study.iitm.ac.in".strip().lower()

TOOL = {
    "name": "solve_challenge",
    "description": "Returns first 16 hex chars of SHA-256(challenge:email), challenge read from X-Exam-Challenge header.",
    "inputSchema": {"type": "object", "properties": {}, "required": []},
}

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)


def handle(msg: dict, request: Request):
    method = msg.get("method")
    mid = msg.get("id")

    # Notifications (no id) get no response
    if mid is None:
        return None

    if method == "initialize":
        params = msg.get("params") or {}
        result = {
            "protocolVersion": params.get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "tds-mcp", "version": "1.0.0"},
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [TOOL]}
    elif method == "tools/call":
        name = (msg.get("params") or {}).get("name")
        if name != "solve_challenge":
            return {"jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32602, "message": f"Unknown tool: {name}"}}
        challenge = request.headers.get("x-exam-challenge", "")
        digest = hashlib.sha256(f"{challenge}:{EMAIL}".encode()).hexdigest()[:16]
        result = {"content": [{"type": "text", "text": digest}], "isError": False}
    else:
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32601, "message": f"Method not found: {method}"}}

    return {"jsonrpc": "2.0", "id": mid, "result": result}


@app.get("/")
def root():
    return {"status": "ok", "mcp": "/mcp"}


@app.get("/mcp")
def mcp_get():
    return Response(status_code=405)


@app.post("/mcp")
async def mcp_post(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={
            "jsonrpc": "2.0", "id": None,
            "error": {"code": -32700, "message": "Parse error"}})

    if isinstance(body, list):
        out = [r for r in (handle(m, request) for m in body) if r is not None]
        return JSONResponse(out) if out else Response(status_code=202)

    res = handle(body, request)
    if res is None:
        return Response(status_code=202)
    return JSONResponse(res)
