import os
import base64
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


PROTOCOLS = (
    "vmess://",
    "vless://",
    "trojan://",
    "ss://",
    "ssr://",
    "hy2://",
    "hysteria://",
    "tuic://",
)


def extract_configs(text):
    if not text:
        return []

    return PATTERN.findall(text)


async def main():

    all_configs = {}

    for channel_name, limit in CHANNELS.items():

        print(f"Processing {channel_name} (last {limit} messages)")

        entity = await client.get_entity(channel_name)

        channel_configs = []

        async for msg in client.iter_messages(entity, limit=limit):
            channel_configs.extend(extract_configs(msg.text))

        # dedupe per channel
        channel_configs = list(dict.fromkeys(channel_configs))

        # save per-channel file
        with open(f"{channel_name}.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(channel_configs))

        print(f"{channel_name}: {len(channel_configs)} configs")

        # add to global pool
        for c in channel_configs:
            all_configs[c] = None

    # global dedupe
    merged = list(all_configs.keys())

    # create sub.txt (base64)
    encoded = base64.b64encode("\n".join(merged).encode()).decode()

    with open("sub.txt", "w", encoding="utf-8") as f:
        f.write(encoded)

    print(f"TOTAL UNIQUE CONFIGS: {len(merged)}")


with client:
    client.loop.run_until_complete(main())