import os
import base64
import re
from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit
from telethon import TelegramClient
from telethon.sessions import StringSession

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
    "ConfigsHUB2": 1000,
    "TheFreeConfigs": 300,
}
# =========================

PATTERN = re.compile(
    r'((?:vmess|vless|trojan|ss|ssr|hy2|hysteria|tuic)://\S+)'
)

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


async def main():

    all_configs = []

    for channel_name, limit in CHANNELS.items():

        print(f"Processing {channel_name} (last {limit} messages)")

        entity = await client.get_entity(channel_name)

        channel_configs = []

        async for msg in client.iter_messages(entity, limit=limit):
            channel_configs.extend(extract_configs(msg.text))

        # dedupe per channel
        channel_configs = deduplicate_configs(channel_configs)

        # save per-channel file
        with open(f"{channel_name}.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(channel_configs))

        print(f"{channel_name}: {len(channel_configs)} configs")

        # add to global pool
        all_configs.extend(channel_configs)

    # global dedupe
    merged = deduplicate_configs(all_configs)

    # create sub.txt (base64)
    encoded = base64.b64encode("\n".join(merged).encode()).decode()

    with open("sub.txt", "w", encoding="utf-8") as f:
        f.write(encoded)

    print(f"TOTAL UNIQUE CONFIGS: {len(merged)}")


with client:
    client.loop.run_until_complete(main())