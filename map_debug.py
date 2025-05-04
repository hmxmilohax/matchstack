#!/usr/bin/env python3
import argparse
import subprocess
import re
from pathlib import Path
from collections import defaultdict

# ——— ANSI COLORS ———
ADDR_COLOR   = '\033[96m'        # cyan for addresses & Data Stack Trace
SYM_COLOR    = '\033[92m'        # green for symbols
ARROW_COLOR  = '\033[91m'        # red for arrows
FAIL_COLOR   = '\033[38;5;208m'  # orange for FAIL-MSG text
DEM_COLOR    = '\033[93m'        # yellow for demangled names
DTA_COLOR    = '\033[94m'        # magenta for any file.ext(##) paths
RESET        = '\033[0m'

def run_stack_reader(stack_script, map_path, log_path, out_path):
    subprocess.run(
        [subprocess.sys.executable, stack_script, map_path, log_path, out_path],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

def pretty_print_resolved(out_path):
    with open(out_path, encoding='utf-8', errors='ignore') as f:
        for raw in f:
            line = raw.rstrip()
            if not line: continue
            if '->' in line:
                left, right = line.split('->', 1)
                addr, sym = left.split(':', 1)
                print(f"{ADDR_COLOR}{addr}:{RESET} "
                      f"{SYM_COLOR}{sym.strip()}{RESET} "
                      f"{ARROW_COLOR}->{RESET} "
                      f"{DEM_COLOR}{right.strip()}{RESET}")
            else:
                addr, sym = line.split(':', 1)
                print(f"{ADDR_COLOR}{addr}:{RESET} "
                      f"{SYM_COLOR}{sym.strip()}{RESET}")

def extract_fail_messages(log_path):
    fail_pattern = re.compile(r"FAIL-MSG:\s*(.*)")
    msgs = []
    with open(log_path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = fail_pattern.search(line)
            if m: msgs.append(m.group(1).strip())
    return msgs

def show_data_stack_trace(log_path):
    path_pattern = re.compile(r"\b(\S+\.\w+)\((\d+)\)")
    seen = False
    with open(log_path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not seen:
                if "Data Stack Trace" in line:
                    seen = True
                    print("\n=== Data Stack Trace ===\n")
                continue
            if not line.strip(): break
            parts = line.split("N[OSREPORT]:", 1)
            content = parts[1].rstrip() if len(parts)==2 else line.rstrip()
            if not path_pattern.search(content): break
            highlighted = path_pattern.sub(
                lambda m: f"{DTA_COLOR}{m.group(0)}{ADDR_COLOR}", content
            )
            print(f"{ADDR_COLOR}{highlighted}{RESET}")

def extract_data_stack_refs(log_path):
    pat = re.compile(r"\b(\S+\.\w+)\((\d+)\)")
    seen = False
    refs = []
    with open(log_path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not seen:
                if "Data Stack Trace" in line: seen = True
                continue
            if not line.strip(): break
            parts = line.split("N[OSREPORT]:",1)
            content = parts[1] if len(parts)==2 else line
            for path, num in pat.findall(content):
                refs.append((path, int(num)))
    return refs

def find_dta_references(log_path):
    pat = re.compile(r"\(file\s+([^,]+\.dta),\s*line\s*(\d+)\)")
    refs, seen_failed, seen_start = set(), False, False
    with open(log_path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not seen_failed:
                if "APP FAILED" in line: seen_failed = True
                continue
            if not seen_start:
                if "start stack trace" in line: seen_start = True
                continue
            m = pat.search(line)
            if m: refs.add((m.group(1), int(m.group(2))))
    return sorted(refs)

def correct_typos(refs, dta_root):
    by_dir = defaultdict(list)
    for path, num in refs:
        by_dir[str(Path(path).parent)].append((path, num))
    corrected = []
    for dirpath, items in by_dir.items():
        existing = [p for p,_ in items if Path(dta_root, p).exists()]
        majority = None
        if existing:
            names = [Path(p).name for p in existing]
            majority = max(set(names), key=names.count)
        for path, num in items:
            full = Path(dta_root) / path
            if full.exists():
                corrected.append((path, num))
            elif majority:
                fixed = str(Path(dirpath) / majority)
                corrected.append((fixed, num))
                print(f"{ARROW_COLOR}⟳ corrected{RESET}: {path} → {fixed}")
            else:
                corrected.append((path, num))
    return corrected

def run_dta_debug(matchstack_script, dta_root, refs):
    # only run for the first (top) reference
    path, lineno = refs[0]
    p = Path(path)
    if not p.is_absolute(): p = Path(dta_root)/p
    if not p.exists():
        print(f"⚠️  dta file not found: {p}", file=sys.stderr)
        return
    print(f"\n> Snippet for {p} @ line {lineno}:\n")
    subprocess.check_call([subprocess.sys.executable,
                           matchstack_script, str(p), str(lineno)])

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--map", required=True)
    p.add_argument("--log", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--dta-root", default=".")
    p.add_argument("--stack-tool", default="stack_trace_read.py")
    p.add_argument("--dta-tool", default="matchstack.py")
    args = p.parse_args()

    run_stack_reader(args.stack_tool, args.map, args.log, args.out)

    print("\n=== Resolved Stack Trace ===\n")
    pretty_print_resolved(args.out)

    print("\n=== FAIL-MSGs ===\n")
    fails = extract_fail_messages(args.log)
    if fails:
        for msg in fails:
            print(f" {ARROW_COLOR}•{RESET} {FAIL_COLOR}{msg}{RESET}")
    else:
        print(" (none found)")

    show_data_stack_trace(args.log)

    refs = find_dta_references(args.log)
    if not refs:
        refs = extract_data_stack_refs(args.log)
        if refs:
            print("\n🔄 Fallback to Data Stack Trace refs")

    refs = correct_typos(refs, args.dta_root)
    if refs:
        run_dta_debug(args.dta_tool, args.dta_root, refs)
    else:
        print("\n🔍 No .dta references found.")

if __name__ == "__main__":
    main()
