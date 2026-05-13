#!/usr/bin/env bash
# Groundwork install script
# Sets up the full system in ~/Board for the current user.

set -euo pipefail

BOARD_ROOT="$HOME/Board/board"
SCRIPTS_DST="$HOME/.local/bin"
SYSTEMD_DST="$HOME/.config/systemd/user"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓${NC} $*"; }
warn() { echo -e "${YELLOW}  !${NC} $*"; }
fail() { echo -e "${RED}  ✗${NC} $*"; exit 1; }

echo ""
echo "  Groundwork installer"
echo "  ════════════════════"
echo ""

# ── dependency checks ─────────────────────────────────────────────────────────

check_cmd() { command -v "$1" &>/dev/null || fail "Required: $1 (not found in PATH)"; }

check_cmd python3
check_cmd inotifywait   # inotify-tools package
check_cmd vdirsyncer
check_cmd nvim
ok "Dependencies OK"

# ── Python packages ───────────────────────────────────────────────────────────

python3 -c "import plotly" 2>/dev/null || {
    warn "plotly not found — attempting install..."
    if command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm python-plotly || warn "Could not install python-plotly — run: sudo pacman -S python-plotly"
    else
        python3 -m pip install --user plotly || warn "Could not install plotly"
    fi
}
python3 -c "import kaleido" 2>/dev/null || \
    warn "kaleido not found — PNG chart export disabled (install manually: sudo pip install kaleido --break-system-packages)"
ok "Python packages OK"

# ── board directory structure ─────────────────────────────────────────────────

mkdir -p \
    "$BOARD_ROOT" \
    "$BOARD_ROOT/shabits/charts" \
    "$BOARD_ROOT/done" \
    "$HOME/Board"

ok "Board directories created"

# ── shabits config ────────────────────────────────────────────────────────────

JSON="$BOARD_ROOT/shabits/shabits.json"
if [ ! -f "$JSON" ]; then
    cp "$SCRIPT_DIR/config/shabits.json.example" "$JSON"
    ok "Installed example shabits.json — edit $JSON to add your habits"
else
    warn "shabits.json already exists — skipping"
fi

CSV="$BOARD_ROOT/done/shabits.csv"
if [ ! -f "$CSV" ]; then
    echo "date,habit_id" > "$CSV"
    ok "Created empty shabits.csv"
fi

# ── scripts ───────────────────────────────────────────────────────────────────

mkdir -p "$SCRIPTS_DST"
for script in shabits shabits-graphs habits-watch board-pages board-watch board-sync p0 groundwork-monitor; do
    src="$SCRIPT_DIR/scripts/$script"
    dst="$SCRIPTS_DST/$script"
    cp "$src" "$dst"
    chmod +x "$dst"
    ok "Installed $script → $dst"
done

# shabits-caldav is named with underscores for Python import compatibility
cp "$SCRIPT_DIR/scripts/shabits_caldav.py" "$SCRIPTS_DST/shabits-caldav"
chmod +x "$SCRIPTS_DST/shabits-caldav"
ok "Installed shabits-caldav → $SCRIPTS_DST/shabits-caldav"

# ── Claude Code settings ──────────────────────────────────────────────────────

CLAUDE_CFG="$HOME/Board/.claude/settings.json"
if [ ! -f "$CLAUDE_CFG" ]; then
    mkdir -p "$(dirname "$CLAUDE_CFG")"
    sed "s|YOUR_USER|$(whoami)|g" "$SCRIPT_DIR/config/claude-settings.json.example" > "$CLAUDE_CFG"
    ok "Installed Claude Code settings → $CLAUDE_CFG"
else
    warn "Claude Code settings already exist — skipping (see config/claude-settings.json.example)"
fi

# ── systemd services ──────────────────────────────────────────────────────────

mkdir -p "$SYSTEMD_DST"
for svc in habits-watch.service board-watch.service board-sync.service board-sync.timer shabits-caldav.service shabits-caldav.timer; do
    cp "$SCRIPT_DIR/systemd/$svc" "$SYSTEMD_DST/$svc"
    ok "Installed $svc"
done

systemctl --user daemon-reload

for svc in habits-watch board-watch board-sync.timer shabits-caldav.timer; do
    systemctl --user enable --now "$svc" 2>/dev/null && ok "Enabled $svc" || warn "Could not enable $svc (enable manually)"
done

# ── done ─────────────────────────────────────────────────────────────────────

echo ""
echo "  Done! Run: shabits"
echo ""
echo "  Next steps:"
echo "    1. Edit ~/Board/board/shabits/shabits.json to define your habits"
echo "    2. Configure vdirsyncer for Nextcloud CalDAV sync"
echo "    3. Open Claude Code inside ~/Board/ to use the board skill"
echo ""
