#!/usr/bin/env bash
# Tests for habits-watch checkbox regex — bug: [A-Za-z\ ]+ misses names with numbers/hyphens

pass=0
fail=0

assert_match() {
    local desc="$1"
    local line="$2"
    if [[ "$line" =~ ^-\ \[([xX ])\]\ ([A-Za-z0-9\ \-]+) ]]; then
        echo "  PASS: $desc"
        ((pass++))
    else
        echo "  FAIL: $desc — expected match, got none"
        ((fail++))
    fi
}

assert_no_match() {
    local desc="$1"
    local line="$2"
    if [[ "$line" =~ ^-\ \[([xX ])\]\ ([A-Za-z0-9\ \-]+) ]]; then
        echo "  FAIL: $desc — expected no match, got match"
        ((fail++))
    else
        echo "  PASS: $desc"
        ((pass++))
    fi
}

echo "habits-watch regex tests"
echo "========================"

# Should match (letters only)
assert_match "plain name matches" "- [x] Morning Routine          (streak 3 | best 7)"
assert_match "unchecked box matches" "- [ ] Evening Walk             (streak 0 | best 4)"
assert_match "uppercase X matches" "- [X] Read before sleep        (streak 1 | best 2)"

# Should match but currently DON'T (the bug)
assert_match "name with hyphen matches" "- [x] Push-ups                 (streak 3 | best 7)"
assert_match "name with number matches" "- [x] 25 Push-ups              (streak 3 | best 7)"
assert_match "name with digit prefix" "- [x] 7-minute workout         (streak 2 | best 5)"

echo ""
echo "Results: $pass passed, $fail failed"
[ $fail -eq 0 ] && exit 0 || exit 1
