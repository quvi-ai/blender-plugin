# QUVIAI Render — Blender Add-on

Official Blender add-on for [QUVIAI](https://quvi.ai). Captures your 3D Viewport and transforms it into a photorealistic architectural render using the QUVIAI AI API.

## Requirements

- Blender 4.0 or newer (tested on Blender 5.1 on Linux, macOS, Windows)
- A [QUVIAI account](https://quvi.ai)

## Installation

### From a release ZIP (recommended)

1. Download the latest `quviai_blender_vX.Y.Z.zip` from [Releases](https://github.com/quvi-ai/blender-plugin/releases)
2. In Blender: **Edit → Preferences → Add-ons → Install…**
3. Select the downloaded `.zip` — do **not** unzip it first
4. Enable **QUVIAI Render** in the add-on list
5. Go to **Edit → Preferences → Add-ons → QUVIAI Render** and log in

### Building from source

```bash
git clone https://github.com/quvi-ai/blender-plugin.git
cd blender-plugin
bash scripts/update_vendor.sh   # copies the SDK into quviai_blender/vendor/
# Then zip the quviai_blender/ folder and install in Blender as above
```

## Logging in

Open **Edit → Preferences → Add-ons → QUVIAI Render**:

- **Email / password**: enter your QUVIAI credentials and click **Log In**
- **Google**: click **Log In with Google** — your browser opens and the add-on handles the callback automatically

After login your credit balance is shown. Use the **↻** button to refresh it.

## Usage

1. Open a **3D Viewport** and press `N` to show the side panel
2. Click the **QUVIAI** tab
3. Set your **Prompt**, **Style**, **Render Type**, **Time of Day**, and **Weather**
4. Click **Render with QUVIAI**
5. The result appears in the Image Editor when complete

Default settings mirror the QUVIAI web app: **Exterior / Day / Sunny**.

## Render parameters

| Parameter | Description | Example values |
|-----------|-------------|----------------|
| Prompt | Text description of the scene | "modern office lobby with plants" |
| Style | Architectural or artistic style | Modern, Art Deco, Futuristic … |
| Render Type | Type of architectural render | Exterior, Interior, Site |
| Time of Day | Lighting preset | Day, Night |
| Weather | Atmosphere preset | Sunny, Cloudy, Rainy … |

## Advanced settings

Under **Edit → Preferences → Add-ons → QUVIAI Render → Advanced**:

- **Base URL** — change only if using a custom API endpoint (default: `https://quvi.ai`)

## Error messages

| Message | Cause | Fix |
|---------|-------|-----|
| Not logged in | No token stored | Log in via Preferences |
| Insufficient credits | Account balance is 0 | Top up at [quvi.ai](https://quvi.ai) |
| Rate limit exceeded | Too many concurrent requests | Wait and retry |
| Content policy violation | Prompt blocked | Revise the prompt |
| Session expired | Token expired | Log in again |

## Developer setup

```bash
# Install the SDK in editable mode for local development
pip install -e ../quviai-python-sdk

# After SDK changes, resync the vendor copy
bash scripts/update_vendor.sh
```

The add-on bundles the SDK inside `quviai_blender/vendor/` so it works without any external pip install.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
