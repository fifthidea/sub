import json
import jdatetime
import pytz
from datetime import datetime, timedelta
import os
import base64
import re
from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit
from telethon import TelegramClient
from telethon.sessions import StringSession
from validator import validate

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
    channel_stats = {}
    tehran = pytz.timezone("Asia/Tehran")
    cutoff = datetime.now(tehran) - timedelta(days=CHANNEL_ACTIVITY_DAYS)
    
    for channel_name, limit in CHANNELS.items():

        print(f"Processing {channel_name} (last {limit} messages)")

        entity = await client.get_entity(channel_name)

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
        channel_stats[channel_name] = {
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
        channel_file = os.path.join(
            CHANNEL_OUTPUT_DIR,
            f"{channel_name}.txt"
        )

        with open(channel_file, "w", encoding="utf-8") as f:
            f.write("\n".join(channel_configs))

        print(f"{channel_name}: {len(channel_configs)} configs")

        # add to global pool
        if (
            latest_config_date is not None
            and latest_config_date >= cutoff
        ):
            all_configs.extend(channel_configs)
            print(f"{channel_name}: ACTIVE")
        else:
            print(f"{channel_name}: INACTIVE (not merged)")

    # global dedupe
    merged = deduplicate_configs(all_configs)

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

    now = datetime.now(tehran)
    jalali = jdatetime.datetime.fromgregorian(datetime=now)

    stats = {
        "updated": jalali.strftime("%Y/%m/%d %H:%M"),
        "subscriptions": {
            "sub-full": len(merged),
            "sub-medium": min(1500, len(merged)),
            "sub-lite": min(750, len(merged)),
            "sub-tiny": min(300, len(merged))
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
