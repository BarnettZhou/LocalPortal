# Local Portal (lportal)

📖 [中文文档](docs/readme-zh.md)

A real-time LAN text relay tool —— the Local Portal

## Features

- **Phone Input → PC Clipboard Sync**: Type on your phone, and the content instantly appears on your computer clipboard
- **File Transfer**: Send images and videos from your phone directly to your computer's download folder
- **Copy Mode Switching**: Supports cover mode (default) and append mode; multiple messages are automatically merged in append mode
- **Text Beautification**: Use LLM to convert colloquial input into structured documents, with streaming output and reasoning chain display
- **Multi-Device Isolation**: Each device registers independently with isolated sessions; messages and history are completely separated
- **Device Session Mode**: The server can establish dedicated sessions with specific devices for bidirectional messaging
- **Pure Browser Solution**: No app installation required on the phone; just open the browser and go
- **Interactive CLI**: The computer side provides a CLI terminal with slash command support
- **Pairing Code Security**: 4-digit numeric pairing code prevents unauthorized access

Use Cases:
- Quickly send URLs, verification codes, or long text to your computer
- Transfer photos and videos directly from your phone to your computer
- Temporary note and to-do transmission
- Type on your phone, paste on your computer
- Convert voice input into professionally structured documents with one click
- Multiple devices connected simultaneously with completely isolated data
- Server actively pushes messages and notifications to specified devices

## Installation

### Recommended: Install from PyPI

```bash
pip install localportal
```

Then run:

```bash
lportal
```

### Alternative: Global Install with uv

If you use [uv](https://docs.astral.sh/uv/), you can also install globally as a tool:

```bash
uv tool install localportal
```

`uv tool` installs the package into an isolated environment (e.g. `%APPDATA%\uv\tools\lportal\` on Windows, `~/.local/share/uv/tools/lportal/` on Linux/macOS) and creates an executable in your user's script directory, so it won't pollute your system Python.

**Upgrade / Uninstall**:
```bash
uv tool upgrade localportal   # upgrade
uv tool uninstall localportal # uninstall
```

### Development

If you want to run from source or contribute:

**With uv**:
```bash
uv sync        # install dependencies
uv run lportal # run
```

**With pip (editable)**:
```bash
# Create virtual environment (recommended)
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install in editable mode
pip install -e .

# Run
lportal
```

**Build & install a local wheel**:
```bash
python -m build
pip install dist/localportal-*.whl
lportal
```

## Usage

```bash
# Default start (port 14554)
lportal

# Specify port
lportal --port 8080

# Disable auto-copy
lportal --no-auto-copy

# Set max history entries
lportal --max-history 20
```

### Set Download Directory

Files (images, videos) are saved to the system download directory (`~/Downloads`) by default. You can customize the download path via the `LPORTAL_DOWNLOAD_DIR` environment variable:

```bash
# Windows PowerShell
$env:LPORTAL_DOWNLOAD_DIR="D:\\MyDownloads"
lportal

# Windows CMD
set LPORTAL_DOWNLOAD_DIR=D:\\MyDownloads
lportal

# Linux / Mac
export LPORTAL_DOWNLOAD_DIR=/home/user/MyDownloads
lportal
```

### LLM Configuration (Text Beautification)

The `/beauty` command requires an OpenAI-compatible API. Create a `.env` file in one of the following locations:

**Option 1: User Config Directory (Recommended for global install users)**

```bash
# Windows
mkdir "%APPDATA%\localportal"
echo OPENAI_BASE_URL=https://api.openai.com/v1 > "%APPDATA%\localportal\.env"
echo OPENAI_API_KEY=sk-xxxxxx >> "%APPDATA%\localportal\.env"
echo OPENAI_MODEL=gpt-4o-mini >> "%APPDATA%\localportal\.env"

# macOS
mkdir -p ~/Library/Application\ Support/localportal
cat > ~/Library/Application\ Support/localportal/.env << EOF
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-xxxxxx
OPENAI_MODEL=gpt-4o-mini
EOF

# Linux
mkdir -p ~/.config/localportal
cat > ~/.config/localportal/.env << EOF
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-xxxxxx
OPENAI_MODEL=gpt-4o-mini
EOF
```

**Option 2: Current Working Directory (Good for development & debugging)**

Create a `.env` file in the project directory or any working directory:

```bash
OPENAI_BASE_URL=https://api.openai.com/v1/chat/completions
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini
```

**Note**: The `.env` in the current working directory takes precedence over the user config directory.

The system prompt is located at `src/prompt/text-beauty.md`; feel free to modify it as needed.

### Device Registration

The mobile side must pass two verification steps after connecting:

1. **Pairing Code Verification**: Enter the 4-digit pairing code displayed on the computer
2. **Device Registration**: Enter a device name (must be unique among currently online devices). After successful registration, a unique `login_id` is assigned

- When the same device reconnects, as long as the server has not restarted, the `login_id` remains unchanged and history can be restored
- Use the `/devices` command to view all online devices

### Pairing Code Security

A 4-digit pairing code is generated on startup; the mobile side must enter the correct code to connect.

- **Scan to connect**: Use the `/qr` command to display a QR code; scanning it auto-fills the pairing code
- **Manual connect**: Open the browser address and enter the pairing code
- **Refresh pairing code**: Use `/refresh-qrcode` (`/rq`) to generate a new pairing code; old connections will be disconnected
- **Switch copy mode**: Use `/mode [cover|add]` to switch between cover and append modes; changes are synchronized to all online devices
- **Refresh session**: In append mode, use `/new-session` to start a new session
- **Text beautification**: Use `/beauty [N]` to structure and polish the Nth history message via LLM

## Commands

| Command | Description |
|---------|-------------|
| `/auto [on\|off]` | Toggle auto-copy mode |
| `/copy [N]` | Copy history message (N=1-10, no arg = most recent) |
| `/list` (`/ls`) | List history messages |
| `/status` | Show service status (including pairing code) |
| `/open` | Open the main page in browser |
| `/qrcode` (`/qr`) | Display ASCII QR code (scan to connect) |
| `/downloads` | Open download folder |
| `/refresh-qrcode` (`/rq`) | Refresh pairing code (disconnects all connections) |
| `/mode [cover\|add]` | Switch copy mode: cover = overwrite, add = append |
| `/new-session` | Refresh session in append mode (clear buffer) |
| `/beauty [N]` | Beautify the Nth history message via LLM (default: most recent) |
| `/beauty-history` | View the last 10 text beautification tasks |
| `/beauty-copy [N]` | Copy the Nth beautification result (default: most recent) |
| `/devices` | View all logged-in devices (name, login_id, login time) |
| `/link <name\|id>` | Enter session mode with a specific device; prompt becomes `lportal[device]>` |
| `/unlink` | Exit device session mode |
| `/send <filepath>` | Send a file to the current session device (use after `/link`) |
| `/help` | Show help |
| `/exit` | Exit the program |

### Device Session Mode

After entering session mode, you can directly type text to send to the device without slash commands. You can also use `/send` to transfer files:

```
lportal> /link iPhone
[OK] Entered device session mode: iPhone (a3f9b2c1)

lportal[iPhone]> Hello, this is a server message
[11:30:15] -> iPhone: Hello, this is a server message...

lportal[iPhone]> /send C:\Users\xx\Documents\file.pdf
[OK] File sent to iPhone: file.pdf (123.4KB)

lportal[iPhone]> /unlink
[OK] Exited session mode with iPhone
```

## Tech Stack

- Python 3.9+
- aiohttp (HTTP/WebSocket)
- typer (CLI)
- prompt_toolkit (Interactive terminal)
- rich (Terminal styling)
- pyperclip (Clipboard)

## TODO

- [x] Image transfer support
- [x] Video transfer support
- [x] Copy mode switching (cover / add)
- [x] Session management (grouped display in append mode)
- [ ] Message persistent storage
- [ ] Multi-device online management
- [ ] Encrypted transmission support
- [ ] Web dark / light theme switching

## License

MIT
