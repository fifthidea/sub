# Telegram V2Ray Subscription Generator
Automatically builds V2Ray subscriptions from one or more public Telegram channels using **Telethon** and **GitHub Actions** cron trigger.

The workflow runs automatically via GitHub Actions, fetches the latest configurable number of messages from each Telegram channel every 15 minutes, validates and deduplicates supported proxy configs, and generates both per-channel and merged subscriptions. Channels that remain inactive for the configured activity period are automatically excluded from the merged subscriptions until they publish new configs again.

---
##  Supported Protocols
The extractor currently supports the following proxy protocols:
* `vless://`
* `vmess://`
* `trojan://`
* `ss://`
* `ssr://`
* `hy2://`
* `hysteria://`
* `tuic://`

---
## Validation `(validator.py)`

Before any deduplication or subscription generation takes place, every extracted configuration is passed through a lightweight validation step. The goal of the validator is to ensure that each configuration contains the minimum set of fields required for the corresponding protocol to be parsed and used by V2Ray-compatible clients.

> only VLESS, VMess, and Trojan configurations are currently validated, as these protocols account for the vast majority of extracted nodes and malformed links.

These are the required fields:
### VLESS

* A valid `UUID` (user ID)
* A server address (IPv4, IPv6, or domain name)
* A valid port number
* When `security=reality` is used, a non-empty REALITY public key (`pbk`)

### VMess

* A valid `UUID` (user ID)
* A server address (IPv4, IPv6, or domain name)
* A valid port number
* When `tls=reality` is used, a non-empty REALITY public key (`pbk`)

### Trojan

* A non-empty password
* A server address (IPv4, IPv6, or domain name)
* A valid port number

Configurations missing any of these required fields are discarded.


### Why Validation Exists

Some V2Ray clients (such as Exclave and v2rayNG) fail to initialize **Balancer** profiles if even a single malformed outbound is present in the subscription. Although these clients allow manually selecting working nodes through URL Test or Real Delay, a malformed configuration can prevent automatic balancing from functioning correctly.


---
##  Deduplication
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

---
##  Generated Files

| File                          | Description                                                                         |
| ----------------------------- | ----------------------------------------------------------------------------------- |
| `sub-base64.txt`              | Every unique config from all active channels encoded in base64.                     |
| `sub-tiny-base64.txt`         | Newest 300 unique configs from active channels encoded in base64.                   |
| `sub-lite-base64.txt`         | Newest 750 unique configs from active channels encoded in base64.                   |
| `sub-medium-base64.txt`       | Newest 1,500 unique configs from active channels encoded in base64.                 |
| `sub-plaintxt.txt`            | Every unique config from all active channels in plaintext.                          |
| `sub-tiny-plaintxt.txt`       | Newest 300 unique configs from active channels in plaintext.                        |
| `sub-lite-plaintxt.txt`       | Newest 750 unique configs from active channels in plaintext.                        |
| `sub-medium-plaintxt.txt`     | Newest 1,500 unique configs from active channels in plaintext.                      |
| `channels/TheFreeConfigs.txt` | All unique configs from that channel in plaintext.                                  |
| `channels/ConfigsHUB2.txt`    | All unique configs from that channel in plaintext.                                  |
| `stats.json`                  | Update time, subscription sizes, per-channel statistics and activity information.   |

### `stats.json`
Contains update date and time, config counts and active status for the `sub.txt` merge pool.

Example:
```json
{
    "updated": "1405/04/13 09:02",
    "subscriptions": {
        "sub": 1871,
        "sub-medium": 1500,
        "sub-lite": 750,
        "sub-tiny": 300
    },
    "channels": {
        "ConfigsHUB2": {
            "configs": 971,
            "active": true,
            "last_config": "1405/04/13 09:02"
        },
        "TheFreeConfigs": {
            "configs": 809,
            "active": true,
            "last_config": "1405/04/13 08:58"
        },
        "persianvpnhub": {
            "configs": 439,
            "active": true,
            "last_config": "1405/04/13 04:56"
        }
    }
}
```
##  Configuration
Telegram channels are configured in `update.py`.

Example:
```python
CHANNELS = {
    "ConfigsHUB2": 2000,
    "TheFreeConfigs": 300,
    "persianvpnhub": 600,
}

CHANNEL_ACTIVITY_DAYS = 7
```

The number in front of Channel ID represents how many of the latest Telegram messages will be scanned for each channel.\
`CHANNEL_ACTIVITY_DAYS` defines how many days may pass since a channel's most recent message containing at least one valid proxy config before that channel is excluded from the merged subscriptions.

> If an inactive channel starts publishing configs again, it is automatically included in the merged subscriptions on the next workflow run.

---
##  Required GitHub Secrets
Create the following repository secrets:

* `TG_API_ID`
* `TG_API_HASH`
* `TG_SESSION`

These credentials are used by Telethon to access Telegram.

---
## ⚠️ Disclaimer

This project **does not verify** whether a proxy is reachable or functional.
Connectivity depends on many factors such as geographic location, ISP, routing, censorship, and network conditions. Therefore, this repository only aggregates publicly available Telegram configs, performs normalization and deduplication, and republishes them as subscription files.
