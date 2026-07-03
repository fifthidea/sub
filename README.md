# Telegram V2Ray Subscription Generator
Automatically builds V2Ray subscriptions from one or more public Telegram channels using **Telethon** and **GitHub Actions** cron job.

The workflow runs automatically on a schedule using GitHub Actions. It fetches the latest configurable number of messages from each Telegram channel via Telethon, extracts supported proxy configurations, and removes duplicates within each channel before generating individual subscription files. Configs from all **active** channels are then merged, deduplicated again, and published as `sub.txt`, `sub-medium.txt`, and `sub-lite.txt`. Channels that haven't published any configs within the configured activity window (7 days by default) are automatically excluded from the merged subscriptions while still keeping their own subscription file up to date. If an inactive channel starts publishing configs again, it is automatically included in the merged subscriptions on the next workflow run.

---
## 📡 Supported Protocols
The extractor currently supports the following proxy protocols:
* `vless://`
* `vmess://`
* `trojan://`
* `ss://`
* `ssr://`
* `hy2://`
* `hysteria://`
* `tuic://`
\
Only valid protocol URLs are extracted from Telegram messages. Any surrounding text, captions, emojis, or formatting are ignored.

---
## 🔄 Deduplication
Deduplication happens in two stages.\
\
**Per-channel:** Each Telegram channel is deduplicated independently before its own `.txt` subscription file is generated.\
**Global:** After all channels are processed, every config is merged and deduplicated again before generating `sub.txt`.

> `sub-lite.txt` and `sub-medium.txt` are generated using `sub.txt` which is deduplicated before.

### Duplicate detection
The following differences are **ignored**:
* Display name / remark (`#...`)
* Query parameter order
* Markdown backticks (`` ` ``)
* Upper/lowercase differences in `host` and `sni`

For example, these two configs are considered identical:

```text
vless://...?host=a.com&sni=b.com&type=ws#Server A
```
```text
vless://...?type=ws&sni=B.Com&host=a.com#Server B
```

Configs are **NOT** considered duplicates if they differ in functional parameters such as:

* UUID / Password
* Host
* SNI
* Path
* Protocol
* Port
* Server address
* Security settings

This means different configurations pointing to the same IP address are preserved if they are functionally different.

---

## 📁 Generated Files

| File                 | Description                                                                         |
| -------------------- | ----------------------------------------------------------------------------------- |
| `sub.txt`            | Every unique config from all active channels encoded in base64.                     |
| `sub-medium.txt`     | Newest 1,500 unique configs from active channels encoded in base64.                 |
| `sub-lite.txt`       | Newest 750 unique configs from active channels encoded in base64.                   |
| `TheFreeConfigs.txt` | All unique configs from that channel in plaintext.                                  |
| `ConfigsHUB2.txt`    | All unique configs from that channel in plaintext.                                  |
| `stats.json`         | Update time, subscription sizes, per-channel statistics and activity information.   |

### `stats.json`
Contains update date and time, config counts and if it's active for the merge pool.

Example:
```json
{
    "updated": "1405/04/13 01:06",
    "subscriptions": {
        "sub": 1391,
        "sub-medium": 1391,
        "sub-lite": 750
    },
    "channels": {
        "ConfigsHUB2": {
            "configs": 662,
            "active": true,
            "last_config": "2026-07-03 21:36"
        },
        "TheFreeConfigs": {
            "configs": 792,
            "active": true,
            "last_config": "2026-07-03 21:17"
        }
    }
}
```
## ⚙️ Configuration
Telegram channels are configured in `update.py`.

Example:
```python
CHANNELS = {
    "ConfigsHUB2": 1000,
    "TheFreeConfigs": 300,
}

CHANNEL_ACTIVITY_DAYS = 7
```

The number in front of Channel ID represents how many of the latest Telegram messages will be scanned for each channel.\
`CHANNEL_ACTIVITY_DAYS` defines how many days may pass since a channel's most recent message containing at least one valid proxy config before that channel is excluded from the merged subscriptions (`sub.txt`, `sub-medium.txt`, and `sub-lite.txt`).

> If an inactive channel starts publishing configs again, it is automatically included in the merged subscriptions on the next workflow run.

---
## 🔐 Required GitHub Secrets
Create the following repository secrets:

* `TG_API_ID`
* `TG_API_HASH`
* `TG_SESSION`

These credentials are used by Telethon to access Telegram.

---
## ⚠️ Disclaimer

This project **does not verify** whether a proxy is reachable or functional.
Connectivity depends on many factors such as geographic location, ISP, routing, censorship, and network conditions. Therefore, this repository only aggregates publicly available Telegram configs, performs normalization and deduplication, and republishes them as subscription files.
