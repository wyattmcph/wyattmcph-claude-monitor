#!/usr/bin/env bash
# Claude Monitor — one-line macOS / Linux installer
#
#   curl -fsSL https://raw.githubusercontent.com/wyattmcph/wyattmcph-claude-monitor/main/install.sh | bash
#
# Downloads the latest standalone binary to ~/.local/bin. No Python required.

set -euo pipefail

REPO="wyattmcph/wyattmcph-claude-monitor"

case "$(uname -s)" in
    Darwin) ASSET="claude-monitor-macos" ;;
    Linux)  ASSET="claude-monitor-linux" ;;
    *)      echo "Unsupported OS: $(uname -s). Try: pip install wyattmcph-claude-monitor"; exit 1 ;;
esac

DIR="$HOME/.local/bin"
DEST="$DIR/claude-monitor"
URL="https://github.com/$REPO/releases/latest/download/$ASSET"

echo ""
echo "  Claude Monitor installer"
echo "  ------------------------"
mkdir -p "$DIR"

echo "  Downloading the latest release..."
curl -fsSL "$URL" -o "$DEST"
chmod +x "$DEST"

echo "  Installed to $DEST"

case ":$PATH:" in
    *":$DIR:"*) ;;
    *) echo "  Add this to your shell profile:  export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
esac

echo ""
echo "  Installed!  Run:  claude-monitor"
echo ""
