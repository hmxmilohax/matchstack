import bisect
import os
import re
import subprocess
import sys

map_symbol_pattern = re.compile(r"\s*[0-9A-Fa-f]{8}\s+[0-9A-Fa-f]{6}\s+([0-9A-Fa-f]{8})\s+[0-9A-Fa-f]{8}\s+[0-9]+\s+(\S*?)\s+.*")
log_msg_pattern = re.compile(r"\d+:\d+:\d+ [^:]+:\d+ N\[OSREPORT\]: (.*)")
log_addr_pattern = re.compile(r"\s*([0-9A-Fa-f]+)")
# Match table-style rows: frame: back-chain   LR Save
table_row_pattern   = re.compile(r"\s*(?:0x)?[0-9A-Fa-f]+:\s*(?:0x)?[0-9A-Fa-f]+\s*(?:0x)?([0-9A-Fa-f]+)")

map_path = sys.argv[1]
log_path = sys.argv[2]
output_path = sys.argv[3]

# Probe for cwdemangle
try:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    cwdemangle_path = os.path.join(script_dir, "cwdemangle")
    demangle = lambda symbol: subprocess.check_output([cwdemangle_path, symbol]).decode().strip('\n')
    assert demangle("main__FPCci") == "main(const char*, int)"
    #print("Using cwdemangle in script directory")
except:
    try:
        demangle = lambda symbol: subprocess.check_output(["cwdemangle", symbol]).decode().strip('\n')
        assert demangle("main__FPCci") == "main(const char*, int)"
        #print("Using cwdemangle in PATH")
    except:
        demangle = lambda symbol: (_ for _ in ()).throw(Exception("cwdemangle not available"))
        print("Couldn't find cwdemangle, symbols will not be demangled.")

#print("Reading map file...")
map_symbols: list[tuple[int, str]] = []
with open(map_path) as map_file:
    for line in map_file.readlines():
        match = map_symbol_pattern.match(line)
        if not match:
            continue

        address = int(match.group(1), base=16)
        symbol = match.group(2)
        map_symbols.append((address, symbol))

map_symbols = sorted(map_symbols, key=lambda v: v[0])
# Precompute list of addresses for bisect
map_addrs   = [addr for addr, _ in map_symbols]

print(f"Read {len(map_symbols)} symbols.")

#print("Reading log file...")
stack_trace_symbols: list[str] = []
with open(log_path) as log_file:
    stack_trace_found = False
    table_trace_found = False
    for line in log_file.readlines():
        # Strip log message header
        match = log_msg_pattern.match(line)
        message = match.group(1) if match else line

        # detect start of old‐style or table‐style trace
        if not stack_trace_found and not table_trace_found:
            if message == "Stack Trace (map file unavailable)":
                stack_trace_found = True
                #rint("Found stack trace, reading addresses...")
                continue
            if message.startswith("Address:") and "LR Save" in message:
                table_trace_found = True
                continue
            continue

        # parse LR Save from table‐style output
        if table_trace_found:
            m = table_row_pattern.match(message)
            if not m:
                #print("Reached end of stack trace.")
                break
            address = int(m.group(1), base=16)
        else:
            # old‐style single‐column addresses
            m = log_addr_pattern.match(message)
            if not m:
                #print("Reached end of stack trace.")
                break
            address = int(m.group(1), base=16)

        # find the symbol <= address
        symbol_index = bisect.bisect_right(map_addrs, address) - 1
        if symbol_index < 0:
            print(f"Invalid stack address {address}")
            stack_trace_symbols.append((address, "<invalid>", None))
            continue

        base, symbol = map_symbols[symbol_index]

        # Try to demangle using cwdemangle, if available
        try:
            demangled = demangle(symbol)
        except:
            demangled = None
            pass

        stack_trace_symbols.append((base, symbol, demangled))

#print("Writing converted stack trace...")
with open(output_path, "w") as output_file:
    for address, symbol, demangled in stack_trace_symbols:
        line = f"{address:x}: {symbol}"
        if demangled:
            if len(line) < 60:
                line += ' ' * (60 - len(line))
            line += f" -> {demangled}"

        print(line, file=output_file, end="\n")

#print("Finished.")
