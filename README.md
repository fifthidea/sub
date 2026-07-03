# Telegram V2Ray Subscription Generator

Automatically builds V2Ray subscriptions from one or more public Telegram channels using **Telethon** and **GitHub Actions**.

The workflow periodically fetches the latest messages from configured Telegram channels, extracts supported proxy links, removes duplicates, and publishes ready-to-use subscription files.

---

## ✨ Features

* Fetches the latest **N messages** from one or more Telegram channels.
* Uses **Telethon** (Telegram API) instead of web scraping.
* Generates a separate subscription file for each Telegram channel.
* Generates a merged subscription (`sub.txt`) containing configs from all channels.
* Automatically updates via **GitHub Actions** (configurable schedule).
* Generates a `stats.json` file containing update time and config counts.
* Uses **Jalali (Shamsi)** date and **Asia/Tehran** time for update information.

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

Only valid protocol URLs are extracted from Telegram messages. Any surrounding text, captions, emojis, or formatting are ignored.

---

## 🔄 Deduplication

Deduplication happens in two stages.

### Per-channel

Each Telegram channel is deduplicated independently before its own `.txt` subscription file is generated.

### Global

After all channels are processed, every config is merged and deduplicated again before generating `sub.txt`.

### Duplicate detection

Two configs are considered duplicates if they are functionally identical after normalization.

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

### `sub.txt`

Base64-encoded subscription containing all unique configs collected from every configured Telegram channel.

### `<ChannelName>.txt`

A plain-text subscription generated for each Telegram channel.

Example:

```text
TheFreeConfigs.txt
ConfigsHUB2.txt
```

### `stats.json`

Contains update information and config counts.

Example:

```json
{
    "updated": "1405/04/14 19:42",
    "total": 1394,
    "channels": {
        "TheFreeConfigs": 782,
        "ConfigsHUB2": 637
    }
}
```

---

## ⚙️ Configuration

Telegram channels are configured in `update.py`.

Example:

```python
CHANNELS = {
    "TheFreeConfigs": 300,
    "ConfigsHUB2": 1000,
}
```

The number represents how many of the latest Telegram messages will be scanned for each channel.

---

## 🔐 Required GitHub Secrets

Create the following repository secrets:

* `TG_API_ID`
* `TG_API_HASH`
* `TG_SESSION`

These credentials are used by Telethon to access Telegram.

---

## 🚀 Automatic Workflow

Each scheduled GitHub Actions run performs the following steps:

1. Connects to Telegram.
2. Reads the configured channels.
3. Extracts supported proxy configs.
4. Deduplicates configs within each channel.
5. Generates a subscription file for each channel.
6. Merges all channels.
7. Deduplicates the merged list.
8. Generates `sub.txt`.
9. Generates `stats.json`.
10. Commits and pushes the updated files automatically.

---

## ⚠️ Disclaimer

This project **does not verify** whether a proxy is reachable or functional.

Connectivity depends on many factors such as geographic location, ISP, routing, censorship, and network conditions. Therefore, this repository only aggregates publicly available Telegram configs, performs normalization and deduplication, and republishes them as subscription files.
