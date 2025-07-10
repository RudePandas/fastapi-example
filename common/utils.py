from fastapi.responses import JSONResponse
import json
from datetime import datetime

class CustomJSONResponse(JSONResponse):
    def render(self, content: object) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            default=lambda o: o.isoformat() if isinstance(o, datetime) else None
        ).encode("utf-8")