import json
import jdatetime
import pytz
from datetime import datetime, timedelta
import os
import base64
import re
import dns.resolver
import ipaddress
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit
from telethon import TelegramClient
from telethon.sessions import StringSession
from validator import validate

resolver = dns.resolver.Resolver()

resolver.nameservers = [
    "1.1.1.1",    # Cloudflare
    "8.8.8.8",    # Google
    "9.9.9.9"     # Quad9 
]

resolver.lifetime = 6
resolver.timeout = 2

CHANNEL_OUTPUT_DIR = "channels"
os.makedirs(CHANNEL_OUTPUT_DIR, exist_ok=True)

SUB_OUTPUT_DIR = "sub"
os.makedirs(SUB_OUTPUT_DIR, exist_ok=True)

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION = os.environ["TG_SESSION"]

client = TelegramClient(
    StringSession(SESSION),
    API_ID,
    API_HASH
)

# =========================
# CONFIG (EDIT THIS ONLY)
# =========================
CHANNELS = {
    "ConfigsHUB2": 2600,
    "TheFreeConfigs": 150,
    "persianvpnhub": 120,
}

CHANNEL_ACTIVITY_DAYS = 3
DNS_WORKERS = 32
MAX_FILENAME_LENGTH = 100
# =========================

PATTERN = re.compile(
    r'((?:vmess|vless|trojan|ss|ssr|hy2|hysteria|tuic)://\S+)'
)

WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4",
    "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4",
    "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}

def sanitize_filename(name):
    if not name:
        return "unnamed"

    # remove invalid Windows filename characters
    invalid = '<>:"/\\|?*'

    name = "".join(
        c for c in name
        if c not in invalid and ord(c) >= 32
    )

    # trim spaces and trailing dots
    name = name.strip().rstrip(".")

    # prevent empty filename
    if not name:
        return "unnamed"

    # Windows reserved names
    if name.upper() in WINDOWS_RESERVED_NAMES:
        name += "_"

    # cap length
    if len(name) > MAX_FILENAME_LENGTH:
        name = name[:MAX_FILENAME_LENGTH]

    name = name.rstrip(" .")

def extract_configs(text):
    if not text:
        return []

    configs = []

    for config in PATTERN.findall(text):
        config = config.rstrip("`")      # Remove trailing backticks
        config = config.replace("`", "") # Remove any remaining backticks
        configs.append(config)

    return configs
    
def normalize_config(config: str) -> str:
    """
    Normalize a config for duplicate detection.

    Removes:
      - remark (#...)
      - backticks
      - whitespace

    Canonicalizes:
      - query parameter order

    Keeps:
      - protocol
      - host/IP
      - port
      - path
      - sni
      - host
      - uuid/password
      - every functional parameter
    """

    config = config.replace("`", "").strip()

    parts = urlsplit(config)

    # Parse query parameters and sort them alphabetically
    params = parse_qsl(parts.query, keep_blank_values=True)
    params = [
    (k, v.lower() if k.lower() in ("host", "sni") else v)
    for k, v in params
    ]
    params.sort()

    normalized_query = urlencode(params)

    # Remove remark (#...)
    return urlunsplit((
        parts.scheme,
        parts.netloc,
        parts.path,
        normalized_query,
        ""
    ))
    
def deduplicate_configs(configs):
    seen = set()
    result = []

    for config in configs:
        key = normalize_config(config)

        if key not in seen:
            seen.add(key)
            result.append(config)

    return result

def load_ir_networks_apnic():
    url = "https://ftp.apnic.net/stats/apnic/delegated-apnic-latest"

    networks = []

    with urllib.request.urlopen(url, timeout=20) as r:
        text = r.read().decode("utf-8")

    for line in text.splitlines():

        if line.startswith("#"):
            continue

        parts = line.split("|")

        if len(parts) < 7:
            continue

        registry, cc, typ, start, value = parts[:5]

        if cc != "IR":
            continue

        if typ not in ("ipv4", "ipv6"):
            continue

        if typ == "ipv4":
            network = ipaddress.summarize_address_range(
                ipaddress.IPv4Address(start),
                ipaddress.IPv4Address(
                    int(ipaddress.IPv4Address(start)) + int(value) - 1
                )
            )
        else:
            network = [
                ipaddress.ip_network(f"{start}/{value}")
            ]

        networks.extend(network)

    return networks
    
def load_ir_networks_ipdeny():
    url = "https://www.ipdeny.com/ipblocks/data/countries/ir.zone"

    with urllib.request.urlopen(url) as r:
        return [
            ipaddress.ip_network(line.decode().strip())
            for line in r
            if line.strip()
        ]
        
def load_ir_networks_local():
    networks = []

    with open("ir-range.txt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            networks.append(
                ipaddress.ip_network(line)
            )

    return networks

try:
    IR_NETWORKS = load_ir_networks_apnic()
except Exception:
    try:
        IR_NETWORKS = load_ir_networks_ipdeny()
    except Exception:
        IR_NETWORKS = load_ir_networks_local()

def is_iran_ip(value):
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False

    return any(ip in net for net in IR_NETWORKS)
    
@lru_cache(maxsize=4096)
def resolves_to_iran_ip(hostname):
    try:
        # IPv4
        try:
            answers = resolver.resolve(hostname, "A")
            for answer in answers:
                if is_iran_ip(answer.to_text()):
                    return True
        except Exception:
            pass

        # IPv6
        try:
            answers = resolver.resolve(hostname, "AAAA")
            for answer in answers:
                if is_iran_ip(answer.to_text()):
                    return True
        except Exception:
            pass

    except Exception:
        pass

    return False
    
def is_iran_host(value):
    if not value:
        return False

    value = value.strip().rstrip(".").lower()

    if value.endswith(".ir"):
        return True

    if is_iran_ip(value):
        return True

    if resolves_to_iran_ip(value):
        return True

    return False
   
    
def config_iran_flags(config):
    """
    Returns:
        (is_ir, server_is_ir)
    """

    try:
        parts = urlsplit(config)
        scheme = parts.scheme.lower()

        if scheme == "vmess":
            obj = json.loads(
                base64.urlsafe_b64decode(parts.netloc + "===")
            )

            server = obj.get("add", "")
            server_is_ir = is_iran_host(server)

            if server_is_ir:
                return True, True

            for key in ("host", "sni"):
                if is_iran_host(obj.get(key, "")):
                    return True, False

            return False, False

        params = dict(parse_qsl(parts.query))

        server = parts.hostname or ""
        server_is_ir = is_iran_host(server)

        if server_is_ir:
            return True, True

        for key in ("host", "sni"):
            if is_iran_host(params.get(key, "")):
                return True, False

    except Exception:
        pass

    return False, False
    

async def main():

    all_configs = []
    channel_stats = {}
    tehran = pytz.timezone("Asia/Tehran")
    cutoff = datetime.now(tehran) - timedelta(days=CHANNEL_ACTIVITY_DAYS)
    
    for channel_ref, info in CHANNELS.items():

        if isinstance(info, int):
            limit = info
            custom_name = None

        else:
            limit = info.get("limit")

            if limit is None:
                raise ValueError(
                    f"{channel_ref}: missing 'limit'"
                )
                
            custom_name = info.get("name")

        print(f"Processing {channel_ref} (last {limit} messages)")

        entity = await client.get_entity(channel_ref)
        
        if getattr(entity, "username", None):
            channel_display = entity.username
        else:
            channel_display = entity.title

        channel_configs = []
        latest_config_date = None

        async for msg in client.iter_messages(entity, limit=limit):

            configs = extract_configs(msg.text)

            if configs:
                channel_configs.extend(configs)

                if latest_config_date is None:
                    latest_config_date = msg.date.astimezone(tehran)
                    
        channel_configs = [cfg for cfg in channel_configs if validate(cfg)]

        # dedupe per channel
        channel_configs = deduplicate_configs(channel_configs)
        channel_stats[channel_display] = {
            "configs": len(channel_configs),
            "active": (
                latest_config_date is not None
                and latest_config_date >= cutoff
            ),
            "last_config": (
                jdatetime.datetime.fromgregorian(
                datetime=latest_config_date
                    ).strftime("%Y/%m/%d %H:%M")
                if latest_config_date
                else None
            )
        }

        # save per-channel file
        if custom_name:
            filename = custom_name

        elif getattr(entity, "username", None):
            filename = entity.username

        else:
            filename = str(entity.id)

        filename = sanitize_filename(filename)

        channel_file = os.path.join(
            CHANNEL_OUTPUT_DIR,
            f"{filename}.txt"
        )

        with open(channel_file, "w", encoding="utf-8") as f:
            f.write("\n".join(channel_configs))

        print(f"{channel_display}: {len(channel_configs)} configs")

        # add to global pool
        if (
            latest_config_date is not None
            and latest_config_date >= cutoff
        ):
            all_configs.extend(channel_configs)
            print(f"{channel_display}: ACTIVE")
        else:
            print(f"{channel_display}: INACTIVE (not merged)")

    # global dedupe
    merged = deduplicate_configs(all_configs)
    
    with ThreadPoolExecutor(max_workers=DNS_WORKERS) as executor:

        ir_results = executor.map(config_iran_flags, merged)

        ir_configs = []
        ir_actual_configs = []

        for cfg, (is_ir, server_is_ir) in zip(merged, ir_results):
            if is_ir:
                ir_configs.append(cfg)

            if server_is_ir:
                ir_actual_configs.append(cfg)

    # create sub (base64)
    def write_subscription(filename, configs):
        encoded = base64.b64encode(
            "\n".join(configs).encode()
        ).decode()

        with open(filename, "w", encoding="utf-8") as f:
            f.write(encoded)
            
    def write_plaintext(filename, configs):
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(configs))

    write_subscription(os.path.join(SUB_OUTPUT_DIR, "sub-full-base64.txt"), merged)
    write_subscription(os.path.join(SUB_OUTPUT_DIR, "sub-medium-base64.txt"), merged[:1500])
    write_subscription(os.path.join(SUB_OUTPUT_DIR, "sub-lite-base64.txt"), merged[:750])
    write_subscription(os.path.join(SUB_OUTPUT_DIR, "sub-tiny-base64.txt"), merged[:300])

    write_plaintext(os.path.join(SUB_OUTPUT_DIR, "sub-full-plaintxt.txt"), merged)
    write_plaintext(os.path.join(SUB_OUTPUT_DIR, "sub-medium-plaintxt.txt"), merged[:1500])
    write_plaintext(os.path.join(SUB_OUTPUT_DIR, "sub-lite-plaintxt.txt"), merged[:750])
    write_plaintext(os.path.join(SUB_OUTPUT_DIR, "sub-tiny-plaintxt.txt"), merged[:300])
    
    write_plaintext(os.path.join(SUB_OUTPUT_DIR, "ir.txt"), ir_configs)
    write_plaintext(os.path.join(SUB_OUTPUT_DIR, "ir-actual.txt"), ir_actual_configs)

    now = datetime.now(tehran)
    jalali = jdatetime.datetime.fromgregorian(datetime=now)

    stats = {
        "updated": jalali.strftime("%Y/%m/%d %H:%M"),
        "subscriptions": {
            "sub-full": len(merged),
            "sub-medium": min(1500, len(merged)),
            "sub-lite": min(750, len(merged)),
            "sub-tiny": min(300, len(merged)),
            "ir": len(ir_configs),
            "ir-actual": len(ir_actual_configs)
        },
        "channels": channel_stats
    }

    with open("stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4, ensure_ascii=False)

        print(f"TOTAL UNIQUE CONFIGS: {len(merged)}")

        commit_message = (
            f"Update subscription | "
            f"{jalali.strftime('%Y/%m/%d %H:%M')}"
        )

    with open("commit_message.txt", "w", encoding="utf-8") as f:
        f.write(commit_message)


with client:
    client.loop.run_until_complete(main())
