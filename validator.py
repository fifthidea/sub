import base64
import uuid
import json
from urllib.parse import urlsplit, parse_qs

def has_value(value):
    return value is not None and str(value).strip() != ""
    
def valid_port(port: str) -> bool:
    if not has_value(port):
        return False

    try:
        port = int(port)
    except ValueError:
        return False

    return 0 <= port <= 65535
    
def valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False
    
def validate_vless(parts):
    if "@" not in parts.netloc:
        return False

    uuid, server = parts.netloc.split("@", 1)

    if not valid_uuid(uuid):
        return False

    if ":" not in server:
        return False

    host, port = server.rsplit(":", 1)

    if not has_value(host):
        return False

    if not valid_port(port):
        return False

    q = parse_qs(parts.query)

    security = q.get("security", [""])[0]

    if security == "reality":
        for key in ("pbk",):
            if not has_value(q.get(key, [""])[0]):
                return False

    return True
    
def validate_trojan(parts):
    if "@" not in parts.netloc:
        return False

    password, server = parts.netloc.split("@", 1)

    if not has_value(password):
        return False

    if ":" not in server:
        return False

    host, port = server.rsplit(":", 1)

    return has_value(host) and valid_port(port)
    
def validate_vmess(parts):
    try:
        data = base64.urlsafe_b64decode(parts.netloc + "===")
        obj = json.loads(data)

        required = [
            "id",
            "add",
            "port",
        ]

        for key in required:
            if not has_value(obj.get(key)):
                return False
                
        if not valid_uuid(str(obj.get("id"))):
            return False
                
        if not valid_port(str(obj.get("port"))):
            return False

        if obj.get("tls") == "reality":
            if not has_value(obj.get("pbk")):
                return False

        return True

    except Exception:
        return False
        
        
def validate(config):
    try:
        parts = urlsplit(config)

        scheme = parts.scheme.lower()

        if scheme == "vless":
            return validate_vless(parts)

        if scheme == "vmess":
            return validate_vmess(parts)

        if scheme == "trojan":
            return validate_trojan(parts)

        return False

    except Exception:
        return False
        

