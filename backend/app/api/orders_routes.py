from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_identity, Identity
from app.tools.tool_gateway import call_tool, ToolError
from fastapi import HTTPException

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("")
def my_orders(identity: Identity = Depends(get_current_identity), db: Session = Depends(get_db)):
    res = call_tool("get_my_orders", {}, identity, db)
    return res["data"]


@router.get("/{order_id}")
def order_details(order_id: str, identity: Identity = Depends(get_current_identity), db: Session = Depends(get_db)):
    try:
        res = call_tool("get_order_details", {"order_id": order_id}, identity, db)
    except ToolError as e:
        raise HTTPException(status_code=403 if e.code == "forbidden" else 404, detail=e.message)
    return res["data"]
