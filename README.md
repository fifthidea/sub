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

- A valid `UUID` (user ID)
- A server address (IPv4, IPv6, or domain name)
- A valid port number (`0-65535`)
- When `security=reality` is used, a non-empty REALITY public key (`pbk`)
- If the `type` parameter is present and non-empty, it must be a valid transport

### VMess

- A valid `UUID` (user ID)
- A server address (IPv4, IPv6, or domain name)
- A valid port number (`0-65535`)
- When `tls=reality` is used, a non-empty REALITY public key (`pbk`)
- If the `net` field is present and non-empty, it must be a valid transport

### Trojan

- A non-empty password
- A server address (IPv4, IPv6, or domain name)
- A valid port number (`0-65535`)
- If the `type` parameter is present and non-empty, it must be a valid transport

Configurations missing any required field are discarded.

The validator is intentionally conservative. It only rejects configurations that are **guaranteed to be structurally invalid**.

It **does not** validate optional parameters such as `host`, `path`, `sni`, `flow`, `fp`, `sid`, or verify whether a server is online or reachable. This minimizes false positives and ensures that potentially working configurations are not discarded unnecessarily.


### Why Validation Exists

Some V2Ray clients (such as Exclave and v2rayNG) fail to initialize **Balancer** profiles if even a single malformed outbound is present in the subscription. Although these clients allow manually selecting working nodes through URL Test or Real Delay, a malformed configuration can prevent automatic balancing from functioning correctly.


---
##  Deduplication
Deduplication happens in two stages.\
\
**Per-channel:** Each Telegram channel is deduplicated independently before its own `.txt` subscription file is generated.\
**Global:** After all channels are processed, every config is merged and deduplicated again before generating `sub.txt`.

> `sub-tiny.txt`, `sub-lite.txt` and `sub-medium.txt` are generated using `sub.txt` which is deduplicated before.

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
##  Telethon

Telethon is mandatory to fetch telegram channels messages. if `TG_SESSION`, `TG_API_HASH` and `TG_API_ID` secrets are not present, the subscription generator will fail.

## Setting up Telegram Credentials for Telethon

### Step 1 — Create a Telegram API Application

1. Log in to **https://my.telegram.org** using the Telegram account you want the bot/user session to use.
2. Click **API development tools**.
3. Fill out the form:
   - **App title:** Any name (e.g. `MyProject`)
   - **Short name:** Any unique short name
   - **Platform:** Desktop (or anything you prefer)
4. Click **Create application**.

You will receive:

- **API ID** → save as `TG_API_ID`
- **API Hash** → save as `TG_API_HASH`

> You can also use Telegram Desktop's official API
> ```
> API_ID = 2040
> API_HASH = "b18441a1ff607e10a989891a5462e627"
> ```

---

### Step 2 — Generate a Telethon Session

Install Telethon:

```bash
pip install telethon
```

Create a file named `generate_session.py`:

```python
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = 12345678          # Replace with your API ID
API_HASH = "your_api_hash" # Replace with your API Hash

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print(client.session.save())
```

Run it:

```bash
python generate_session.py
```

The first time you run it, Telethon will ask for:

- Your phone number
- The login code sent by Telegram
- Your 2FA password (if enabled)

After logging in, it will print a long string similar to:

```text
1AQAOMT...
```

Copy this entire string.

This is your `TG_SESSION`.

---

### Step 3 — Add GitHub Secrets

Open your GitHub repository.

Go to:

```
Settings
→ Secrets and variables
→ Actions
→ New repository secret
```

Create these three secrets:

| Secret Name   | Value                        |
|---------------|------------------------------|
| `TG_API_ID`   | Your API ID                  |
| `TG_API_HASH` | Your API Hash                |
| `TG_SESSION`  | The generated session string |

These credentials are used by Telethon to access Telegram.

#### Security Notes

- Never commit these values to Git.
- Never share your `TG_SESSION` with anyone. It grants access to your Telegram account.
- If your session is ever leaked, revoke it from **Telegram → Settings → Devices** and generate a new one.

## Want your own subscription generator?

1. Fork this repo
2. Configure `update.py` (add your own channels)
3. Add required secrets in `Secrets and variables --> Actions` so telethon can be used.
4. Uncomment these two lines in `sub.yml` workflow
```
 #schedule:
    #- cron: "*/15 * * * *"
```

> Note: you can change cron trigger schedule time from 15 minutes to your desired number.

> I recommend using Cloudflare worker with API access to your github repo for cron trigger schedule. Github's schedules are delayed because of traffic and peak-hours.

5. Manually run the workflow atleast once
