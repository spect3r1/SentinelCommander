import os, sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from core.teamserver import auth_manager as auth


from .websocket_operators import router as operators_ws_router
from TeamServer.websocket_listeners import router as listeners_ws_router
from .websocket_sessions import router as sessions_ws_router
from .files import router as files_router
from .payloads import router as payloads_router
from .websocket_console import router as ws_router
# from .websocket_sentinelshell import router as ss_router
from .websocket_files import router as files_ws_router
# from .websocket_ldap import router as ldap_ws_router

app = FastAPI(title="SentinelCommander Integrated API", version="1.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup():

    auth._connect()
    ops = auth.list_operators() or []
    if not ops:
        auth.add_operator("admin", "admin", "admin")

# Routers
app.include_router(operators_ws_router)
app.include_router(listeners_ws_router)

app.include_router(sessions_ws_router)
app.include_router(files_ws_router)
app.include_router(payloads_router, prefix="/payloads", tags=["payloads"])
app.include_router(ws_router, tags=["websocket"])
# app.include_router(gs_router, tags=["websocket"])
# app.include_router(ldap_ws_router, tags=["websocket"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("SENTINEL_BACKEND_PORT", "6060")))
