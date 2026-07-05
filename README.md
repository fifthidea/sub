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

Create `generate_session.py`, make sure to add your `API_ID` and `API_HASH` values :

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

## Use a Cloudflare Worker for Scheduling (Optional)

A Cloudflare Worker provides a more reliable workflow schedule than GitHub's built-in cron.

### 1. Create a GitHub Personal Access Token

1. Open **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens**.
2. Click **Generate new token**.
3. Enter your password if prompted.
4. Configure:
   - **Token name:** Any name
   - **Expiration:** **No expiration**
   - **Repository access:** **Only select repositories** → select your fork
   - **Add permissions:** **Actions → Access: Read and write**
5. Click **Generate token**.
6. Copy the token (for example, `github_pat_xxx...`). You won't be able to view it again.

### 2. Create a Cloudflare Worker

1. Log in to **https://dash.cloudflare.com** (create an account if needed).
2. Go to **Compute → Workers & Pages → Create Application**.
3. Select **Start with Hello World**, choose any worker name, and click **Deploy**.
4. Open **Settings → Variables and secrets → Add**.
5. Create a secret:
   - **Type:** Secret
   - **Name:** `GITHUB_TOKEN`
   - **Value:** Your GitHub personal access token
6. Click **Deploy**.
7. Open **Trigger events → Add → Cron triggers**.
8. Choose either **Execute Worker every** or enter your own **Cron expression**, then click **Add**.
9. Open **Edit code**, replace the default code with the following, and update `owner` and `repo` to match your repository:
    
```javascript
async function trigger(env) {
  const owner = "fifthidea";      // YOUR github username
  const repo = "sub";             // YOUR github repo's name
  const workflow = "sub.yml";     // workflow file name
  const branch = "main";          // repo branch

  const response = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "Cloudflare-Worker-GitHub-Dispatcher",
      },
      body: JSON.stringify({
        ref: branch,
      }),
    }
  );

  const body = await response.text();

  return {
    success: response.ok,
    status: response.status,
    body: body || "Workflow dispatched successfully.",
  };
}

export default {
  async scheduled(event, env, ctx) {
    const result = await trigger(env);

    if (!result.success) {
      console.error(result);
      throw new Error(result.body);
    }

    console.log("Workflow dispatched successfully.");
  },
};
```

16. Click **Deploy**

### 3. Disable GitHub's Schedule

Comment out or remove the schedule from `.github/workflows/sub.yml`:

```yaml
#schedule:
#  - cron: "*/15 * * * *"
```

# Security Notes

- Never commit `TG_API_ID`, `TG_API_HASH`, or `TG_SESSION` to Git.
- If you are using Cloudflare worker for workflow schedule, never commit your Github Token.
- Never share `TG_SESSION`; it grants access to your Telegram account.
- If it is ever leaked, revoke the session from **Telegram → Settings → Devices** and generate a new one.
