#!/usr/bin/env python3
import argparse
import subprocess
import re
from pathlib import Path

# ——— ANSI COLORS ———
ADDR_COLOR   = '\033[96m'        # cyan for addresses & Data Stack Trace
SYM_COLOR    = '\033[92m'        # green for symbols
ARROW_COLOR  = '\033[91m'        # red for arrows
FAIL_COLOR   = '\033[38;5;208m'  # orange for FAIL-MSG text
DEM_COLOR    = '\033[93m'        # yellow for demangled names
DTA_COLOR    = '\033[94m'        # magenta for any file.ext(##) paths
RESET        = '\033[0m'

def run_stack_reader(stack_script, map_path, log_path, out_path):
    # suppress ALL output from the reader
    subprocess.run(
        [subprocess.sys.executable, stack_script, map_path, log_path, out_path],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

def pretty_print_resolved(out_path):
    """
    Colorize each line of resolved stack:
      addr in cyan, symbol in green, '->' in red, demangled in yellow.
    """
    with open(out_path, encoding='utf-8', errors='ignore') as f:
        for raw in f:
            line = raw.rstrip()
            if not line:
                continue
            if '->' in line:
                left, right = line.split('->', 1)
                addr, sym = left.split(':', 1)
                print(
                    f"{ADDR_COLOR}{addr}:{RESET} "
                    f"{SYM_COLOR}{sym.strip()}{RESET} "
                    f"{ARROW_COLOR}->{RESET} "
                    f"{DEM_COLOR}{right.strip()}{RESET}"
                )
            else:
                addr, sym = line.split(':', 1)
                print(
                    f"{ADDR_COLOR}{addr}:{RESET} "
                    f"{SYM_COLOR}{sym.strip()}{RESET}"
                )

def extract_fail_messages(log_path):
    """
    Grab all FAIL-MSG: lines anywhere in the log.
    """
    fail_pattern = re.compile(r"FAIL-MSG:\s*(.*)")
    msgs = []
    with open(log_path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = fail_pattern.search(line)
            if m:
                msgs.append(m.group(1).strip())
    return msgs

def show_data_stack_trace(log_path):
    """
    After "Data Stack Trace", print each subsequent non-empty line
    that contains a file.ext(##) reference. Stop on the first line
    that does NOT match.
    """
    path_pattern = re.compile(r"\b(\S+\.\w+)\((\d+)\)")
    seen = False

    with open(log_path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not seen:
                if "Data Stack Trace" in line:
                    seen = True
                    print("\n=== Data Stack Trace ===\n")
                continue
            if not line.strip():
                break

            # strip prefix up to N[OSREPORT]:
            parts = line.split("N[OSREPORT]:", 1)
            content = parts[1].rstrip() if len(parts) == 2 else line.rstrip()

            # if this line doesn't have a file.ext(##), we're done
            if not path_pattern.search(content):
                break

            # highlight file.ext(##) in magenta, rest stays cyan
            highlighted = path_pattern.sub(
                lambda m: f"{DTA_COLOR}{m.group(0)}{ADDR_COLOR}", 
                content
            )
            print(f"{ADDR_COLOR}{highlighted}{RESET}")

def find_dta_references(log_path):
    """
    Only collect .dta file+line refs after:
      1) seeing "APP FAILED"
      2) then seeing "start stack trace"
    """
    pattern = re.compile(r"\(file\s+([^,]+\.dta),\s*line\s*(\d+)\)")
    refs = set()
    seen_failed = False
    seen_start  = False

    with open(log_path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not seen_failed:
                if "APP FAILED" in line:
                    seen_failed = True
                continue
            if not seen_start:
                if "start stack trace" in line:
                    seen_start = True
                continue
            m = pattern.search(line)
            if m:
                refs.add((m.group(1), int(m.group(2))))
    return sorted(refs)

def run_dta_debug(matchstack_script, dta_root, refs):
    for relpath, lineno in refs:
        p = Path(relpath)
        if not p.is_absolute():
            p = Path(dta_root) / p
        if not p.exists():
            print(f"⚠️  dta file not found: {p}", file=sys.stderr)
            continue

        print(f"\n> Snippet for {p} @ line {lineno}:\n")
        subprocess.check_call(
            [subprocess.sys.executable, matchstack_script, str(p), str(lineno)]
        )

def main():
    parser = argparse.ArgumentParser(
        description="Resolve stack, colorize it, show FAIL-MSGs, Data Stack Trace, run matchstack.py snippets."
    )
    parser.add_argument("--map",       required=True, help="path to .map file")
    parser.add_argument("--log",       required=True, help="path to dolphin.log")
    parser.add_argument("--out",       required=True, help="where to write resolved stack")
    parser.add_argument("--dta-root",  default=".",     help="base dir for relative .dta paths")
    parser.add_argument("--stack-tool",default="stack_trace_read.py",
                        help="your stack_trace_read script")
    parser.add_argument("--dta-tool",  default="matchstack.py",
                        help="your dta-snippet tool (matchstack.py)")
    args = parser.parse_args()

    # 1) Run the symbol resolver (silently)
    run_stack_reader(args.stack_tool, args.map, args.log, args.out)

    # 2) Print only the colorized, resolved stack trace
    print("\n=== Resolved Stack Trace ===\n")
    pretty_print_resolved(args.out)

    # 3) Print all FAIL-MSGs in orange
    fails = extract_fail_messages(args.log)
    print("\n=== FAIL-MSGs ===\n")
    if fails:
        for msg in fails:
            print(f" {ARROW_COLOR}•{RESET} {FAIL_COLOR}{msg}{RESET}")
    else:
        print(" (none found)")

    # 4) Print the Data Stack Trace (cyan with magenta paths), stop before unwanted blocks
    show_data_stack_trace(args.log)

    # 5) Finally, invoke matchstack.py for each .dta+line reference
    refs = find_dta_references(args.log)
    if refs:
        run_dta_debug(args.dta_tool, args.dta_root, refs)
    else:
        print("\n🔍 No post-trace .dta references found.")

if __name__ == "__main__":
    main()
