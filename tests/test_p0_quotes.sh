#!/usr/bin/env bash
# Tests for p0 quote-stripping bug — task files with quoted summary values

pass=0
fail=0

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# Create a fake board root with one p0 task
FAKE_BOARD="$TMPDIR/board"
DOMAIN_P0="$FAKE_BOARD/personal/p0"
mkdir -p "$DOMAIN_P0"

cat > "$DOMAIN_P0/001_fix_login.md" << 'EOF'
---
id: fix-login-bug
summary: 'Fix login bug'
---

Details here.
EOF

# Inline the p0 logic (find + grep + sed, same as the script)
run_p0() {
    local board_root="$1"
    while IFS= read -r -d '' task; do
        p0_dir=$(dirname "$task")
        domain_path="${p0_dir%/p0}"
        domain="${domain_path#$board_root/}"
        summary=$(grep -m1 "^summary:" "$task" 2>/dev/null | sed "s/^summary: *//;s/^['\"]//;s/['\"]$//")
        name=$(basename "$task" .md | sed 's/^[0-9]*_//')
        echo "[$domain] $name${summary:+ — $summary}"
    done < <(find -L "$board_root" -path "*/p0/*.md" -not -name "SKILL.md" -print0 | sort -z)
}

output=$(run_p0 "$FAKE_BOARD")

echo "p0 quote-stripping tests"
echo "========================"
echo "  Output: $output"

# Should NOT contain single quotes around the summary
if echo "$output" | grep -q "'Fix login bug'"; then
    echo "  FAIL: output contains unstripped quotes — got: $output"
    ((fail++))
else
    echo "  PASS: no quotes in output"
    ((pass++))
fi

# Should contain the plain summary text
if echo "$output" | grep -q "Fix login bug"; then
    echo "  PASS: summary text present"
    ((pass++))
else
    echo "  FAIL: summary text missing"
    ((fail++))
fi

echo ""
echo "Results: $pass passed, $fail failed"
[ $fail -eq 0 ] && exit 0 || exit 1
