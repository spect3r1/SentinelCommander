from fastapi import APIRouter, HTTPException
from typing import Optional

from Core.teamserver import auth_manager as auth

from .dependencies import create_access_token
from .schemas import LoginRequest, TokenResponse, OperatorCreate, OperatorOut, OperatorUpdate

router = APIRouter()

def _get_operator_by_username(username: str) -> Optional[dict]:
    pass

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    """
    Accepts JSON in the format of LoginRequest
    """
    ok = False
    row: Optional[dict] = None
    try:
        res = auth.verify_credentials(body.username, body.password)
        if isinstance(res, tuple) and len(res) >= 2:
            ok, row = bool(res[0]), res[1]
        elif isinstance(res, dict):
            ok, row = True, res
        elif isinstance(res, bool):
            ok = res
            if ok:
                row = _get_operator_by_username(body.username)
        else:
            ok = False
    except Exception:
        ok = False
        row = None
    if not ok or notrow:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    uid = row.get("id") or row.get("op_id") or row.get("uuid")
    uname = row.get("username") or body.username
    role = row.get("role") or "operator"
    if not uid:
        try:
            uid = auth.verify_username(uname)
        except Exception:
            pass
    if not uid:
        raise HTTPException(status_code=401, detail="Account is missing an ID")
    
    token = create_access_token({"sub": uid, "username": uname, "role": role})
    return {"token": token}

@router.get("/operators", response_model=list[OperatorOut])
def list_operators():
    ops = auth.list_operators() or []
    return [{"id": o.get("id") or o.get("uuid") or o.get("op_id"),
             "username": o.get("username", ""),
             "role": o.get("role", "operator")} for o in ops]

@router.post("/operators", response_model=OperatorOut)
def add_operator(body: OperatorCreate):
    try:
        oid = auth.add_operator(body.username, body.password, body.role)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"id": oid, "username": body.username, "role": body.role}

@router.delete("/operators/{identifier}")
def delete_operator(identifier: str):
    try:
        auth.delete_operator(identifier)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "deleted", "identifier": identifier}