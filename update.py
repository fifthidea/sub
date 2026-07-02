import os
import re
import base64
from telethon import TelegramClient
from telethon.sessions import StringSession

# Telegram credentials from GitHub Secrets
API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION = os.environ["TG_SESSION"]

client = TelegramClient(
    StringSession(SESSION),
    API_ID,
    API_HASH
)

# Supported protocols
PATTERN = re.compile(
    r'(?im)^(vmess|vless|trojan|ss|ssr|hy2|hysteria|tuic)://\S+$'
)


async def main():
    channel = await client.get_entity("TheFreeConfigs")

    configs = []

    async for msg in client.iter_messages(channel, limit=300):
        if not msg.text:
            continue

        for line in msg.text.splitlines():
            line = line.strip()
            if PATTERN.match(line):
                configs.append(line)

    # Remove duplicates while preserving order
    configs = list(dict.fromkeys(configs))

    # Create Base64 subscription
    subscription = "\n".join(configs)
    encoded = base64.b64encode(subscription.encode("utf-8")).decode("utf-8")

    with open("sub.txt", "w", encoding="utf-8") as f:
        f.write(encoded)

    print(f"Saved {len(configs)} configs to sub.txt")


with client:
    client.loop.run_until_complete(main())
