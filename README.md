# Telegram V2Ray Subscription Generator
Automatically builds V2Ray subscriptions from one or more public Telegram channels using **Telethon** and GitHub Actions.

Every 15 minutes, the workflow fetches the latest configurable number of messages from each channel, extracts supported proxy configs, validates and deduplicates them, then generates both per-channel and merged subscriptions. Channels inactive for the configured period are automatically excluded from merged subscriptions until they publish new configs again.

---

#  Supported Protocols

The extractor currently supports the following proxy protocols:

`vless://`, `vmess://`, `trojan://`, `ss://`, `ssr://`, `hy2://`, `hysteria://` and `tuic://`

# Validation `(validator.py)`

Every extracted configuration is validated before deduplication or subscription generation. The validator checks only the minimum fields required for V2Ray-compatible clients to parse a configuration.

> Currently only **VLESS**, **VMess**, and **Trojan** are validated, as they make up the vast majority of extracted nodes.

| Protocol   | Required fields                                                                                                                              |
|------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| **VLESS**  | Valid `UUID`, server address (IPv4/IPv6/domain), valid port (`0-65535`), `pbk` when `security=reality`, valid transport if `type` is present |
| **VMess**  | Valid `UUID`, server address (IPv4/IPv6/domain), valid port (`0-65535`), `pbk` when `tls=reality`, valid transport if `net` is present       |
| **Trojan** | Non-empty password, server address (IPv4/IPv6/domain), valid port (`0-65535`), valid transport if `type` is present                          |

Configurations missing any required field are discarded.

The validator is intentionally conservative. It only rejects configurations that are **guaranteed to be structurally invalid**.

It does **not** validate optional fields such as `host`, `path`, `sni`, `flow`, `fp`, or `sid`, nor does it check whether servers are online. This minimizes false positives and avoids discarding potentially working configurations.

## Why Validation Exists

Some clients (such as **Exclave** and **v2rayNG**) fail to initialize **Balancer** profiles if even one malformed outbound exists in the subscription. Although working nodes can still be selected manually through URL Test or Real Delay, malformed configs may prevent automatic balancing from functioning correctly.

#  Deduplication

Deduplication happens in two stages:

- **Per-channel:** each Telegram channel is deduplicated before its own subscription is generated.
- **Global:** all channels are merged and deduplicated again before generating the combined subscriptions.

> `sub-tiny`, `sub-lite`, and `sub-medium` are generated from the already deduplicated merged subscription.

## Duplicate detection

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

| File                       | Description                                                                         |
| -------------------------- | ----------------------------------------------------------------------------------- |
| `sub/*-base64.txt`         | Configs from merge pool encoded in base64                                           |
| `sub/*-plaintxt.txt`       | Configs from merge pool in plaintxt                                                 |
| `channels/*.txt`           | All unique configs from that channel in plaintext.                                  |
| `stats.json`               | Update time, subscription sizes, per-channel statistics and activity information.   |
| `sub/sub-tiny-*.txt`       | includes 300 newest unique configs from merge pool.                                 |
| `sub/sub-lite-*.txt`       | includes 750 newest unique configs from merge pool.                                 |
| `sub/sub-medium-*.txt`     | includes 1500 newest unique configs from merge pool.                                |
| `sub/sub-full-*.txt`       | includes all configs from merge pool.                                               |


### `stats.json`

Contains the update time, subscription sizes, and active status of every channel included in the merged subscriptions.

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
        }
    }
}
```

---

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

The value for each channel specifies how many recent Telegram messages will be scanned.

`CHANNEL_ACTIVITY_DAYS` defines how many days may pass since a channel last published at least one valid proxy configuration before it is excluded from merged subscriptions.

> Once an inactive channel publishes configs again, it is automatically included on the next workflow run.

#  Telethon

Telethon is required to fetch Telegram messages. If `TG_SESSION`, `TG_API_ID`, or `TG_API_HASH` are missing, the workflow will fail.

## Setting Up Telethon

### 1. Create a Telegram API Application

1. Log in to **https://my.telegram.org**.
2. Click **API development tools**.
3. Fill out the form:
   - **App title:** Any name
   - **Short name:** Any unique name
   - **Platform:** Desktop (or any platform)
4. Click **Create application**.
5. Save **API ID** as `TG_API_ID` and **API Hash** as `TG_API_HASH`.

> Alternatively, You can use Telegram Desktop's official API
> ```
> TG_API_ID = 2040
> TG_API_HASH = b18441a1ff607e10a989891a5462e627
> ```

### 2. Generate a Session

Install Telethon:

```bash
pip install telethon
```

Create `generate_session.py`:

```python
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = 12345678          # Replace with your API ID
API_HASH = "your_api_hash" # Replace with your API Hash

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print(client.session.save())
```

Run:

```bash
python generate_session.py
```

The first time, Telethon asks for your phone number, login code, and 2FA password (if enabled), then prints a string like:

```text
1AQAOMT...
```

Copy it as your `TG_SESSION`.

### 3. Add GitHub Secrets

Open **Settings → Secrets and variables → Actions → New repository secret** and create:

| Secret Name   | Value                        |
|---------------|------------------------------|
| `TG_API_ID`   | Your API ID                  |
| `TG_API_HASH` | Your API Hash                |
| `TG_SESSION`  | The generated session string |

# Want your own subscription generator?

1. Fork this repository.
2. Edit `update.py` and add your own channels.
3. Add the required Telethon secrets in **Settings → Secrets and variables → Actions**.
4. Enable the schedule in `.github/workflows/sub.yml` by uncommenting:
```yaml
#schedule:
#  - cron: "*/15 * * * *"
```

> You can change the cron expression to any schedule you prefer.

> For more reliable scheduling, consider using a Cloudflare Worker with GitHub API access to trigger the workflow. GitHub's built-in scheduled workflows may be delayed during peak traffic.

5. Run the workflow manually at least once.

## Use Cloudflare worker for workflow schedule (Optional but more reliable)

1. Click on your Github profile and go to **Settings → Developer Settings → Personal access tokens → Fine-grained tokens**
2. click on **Generate new token**
3. Enter your github account password if asked
4. Enter any name for **Token name**
   set Expiration to **No expiration**
   set Repository access to **Only select repositories** and select your forked repository
   click **Add permissions** and select **Actions**
   set **Access** for Action permission to **Access: Read and write**
5. Click **Generate token**
6. Copy the shown token as you will not be able to see it again.
   it will be something like `github_pat_xxx...`
7. Go to **https://dash.cloudflare.com** and login
   If you don't have account, sign-up and verify account
8. Go to **Compute → Workers & Pages** and click **Create Application**
9. Click **Start with Hello World** and choose any name for Worker name, then click **Deploy**
10. In your woker's dashboard, go to **Settings → Variables and secrets → Add**
11. Set **Secret** for Type. **`GITHUB_TOKEN`** for Variable name and paste your github token into **Value** field, then click **Deploy**
12. Now click on **Trigger events → Add** and select **Cron triggers**.
13. Set **Execute Worker every** to your desired value. alternatively you can use **Cron expression**. then click Add.
14. Click on **Edit code**.
15. Remove all default code and paste the code below:
```

# Security Notes

- Never commit `TG_API_ID`, `TG_API_HASH`, or `TG_SESSION` to Git.
- If you are using Cloudflare worker for workflow schedule, never commit your Github Token.
- Never share `TG_SESSION`; it grants access to your Telegram account.
- If it is ever leaked, revoke the session from **Telegram → Settings → Devices** and generate a new one.
