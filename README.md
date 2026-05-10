# Groundwork

A personal system for tracking habits and tasks — built around plain Markdown files, systemd services, and Claude Code.

```
shabits           — tick off your habits for the day
board             — manage tasks across domains (Claude Code skill)
p0                — today's tasks across all domains
```

## What it is

Three interlocked tools that live inside `~/Board/`:

**Habits (shabits)**
- Define habits in `~/Board/board/shabits/shabits.json`
- Tick them off by editing `shabits.md` in nvim, or with `shabits done <name>`
- History stored as append-only CSV (`~/Board/board/done/shabits.csv`)
- Plotly charts (completion grid, streaks, rolling score) embedded as PNGs in the MD file
- Syncs to Nextcloud CalDAV via vdirsyncer

**Board**
- Task files are plain `.md` files in `~/Board/board/<domain>/<lane>/`
- Lanes: `p0` (today), `p1` (this week), `p2` (this month), `done/`
- Multiple domains (personal, work, projects) live as subdirectories
- Work boards can be symlinked in: `~/Board/board/work → ~/Work/MyProject/board/`
- Claude Code manages tasks via the board skill (create, complete, prioritize)

**Automation**
- `habits-watch` — watches `shabits.md` for checkbox edits, auto-marks done/undone
- `board-watch` — watches all p0/p1/p2 dirs, triggers CalDAV sync on changes
- `board-sync.timer` — hourly fallback sync to CalDAV
- `groundwork-monitor` — Claude Code SessionStart hook that detects system issues and creates board tasks

## Requirements

| Tool | Purpose |
|------|---------|
| `python3` + `pip` | shabits, board-sync, shabits-graphs |
| `inotify-tools` | habits-watch, board-watch file watching |
| `vdirsyncer` | CalDAV sync to Nextcloud |
| `nvim` | opening habit/task files |
| `Claude Code` | board skill (task management) |
| `plotly` + `kaleido` | habit charts |

Optional: image.nvim (LazyVim) + Kitty terminal for inline chart rendering.

## Install

```bash
git clone <repo> ~/Projects/Groundwork
cd ~/Projects/Groundwork
chmod +x install.sh
./install.sh
```

The installer:
1. Checks dependencies
2. Creates `~/Board/board/` directory structure
3. Copies scripts to `~/.local/bin/`
4. Installs and enables systemd user services
5. Drops example configs if none exist

After install, edit `~/Board/board/shabits/shabits.json` to define your habits.

## Board structure

```
~/Board/
├── board/
│   ├── <domain>/
│   │   ├── p0/        ← today's tasks (.md files)
│   │   ├── p1/        ← this week
│   │   ├── p2/        ← this month
│   │   └── done/      ← completed tasks
│   ├── shabits/
│   │   ├── shabits.json   ← habit definitions
│   │   ├── shabits.md     ← today's tick file (edit this)
│   │   └── charts/        ← generated PNGs
│   └── done/
│       └── shabits.csv    ← completion history
├── p0.md              ← aggregated today view (auto-generated)
├── p1.md
└── p2.md
```

To add a work project: `ln -s ~/Work/MyProject/board ~/Board/board/work`

## Habits config

`~/Board/board/shabits/shabits.json`:
```json
[
  {
    "id": "morning-routine",
    "name": "Morning Routine",
    "days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
    "caldav_file": "habit-morning-routine.ics"
  }
]
```

`days` is a subset of `["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]`.

## Commands

```bash
shabits                    # today's habits + streaks
shabits done <name>        # mark done
shabits undo <name>        # untick
shabits stats              # completion rates table
shabits graph              # ASCII completion grid
shabits history [name]     # completion log

p0                         # list today's tasks
p0 open                    # open p0.md in nvim

board-sync                 # manually sync tasks to CalDAV
board-sync --dry           # preview changes
board-pages                # regenerate p0/p1/p2 aggregated views
```

## Claude Code — board skill

Open Claude Code from inside `~/Board/`. Tasks are managed via natural language:

```
board create "Fix login bug" --lane p0
board complete <task-id>
board priority <task-id> p1
```

The `groundwork-monitor` hook runs at each session start and reports service failures, missing files, or stale syncs as p0 tasks.

## CalDAV setup (vdirsyncer)

Add to `~/.config/vdirsyncer/config`:

```ini
[pair nextcloud_tasks]
a = "local_tasks"
b = "remote_tasks"
collections = ["from a", "from b"]

[storage local_tasks]
type = "filesystem"
path = "~/.local/share/vdirsyncer/tasks"
fileext = ".ics"

[storage remote_tasks]
type = "caldav"
url = "https://YOUR_NEXTCLOUD/remote.php/dav/calendars/YOUR_USER/"
username = "YOUR_USER"
password = "YOUR_PASSWORD"
```

Then: `vdirsyncer discover && vdirsyncer sync`
