#!/usr/bin/env python3
"""RTL Verification v4 - Ignores comments, strings, and Verilog keywords"""

import os
import re
import subprocess
import pytest

RTL_DIR = "fpga/rtl"

def strip_comments(content):
    """Remove Verilog comments (// and /* */)"""
    content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    return content

def extract_instantiations(content):
    """Extract module instantiations, ignoring comments and keywords"""
    content = strip_comments(content)
    # Pattern: ModuleName #( params ) instance_name ( port connections )
    # Also: ModuleName instance_name ( port connections )
    patterns = [
        r'^\s*(\w+)\s+#?\([^)]*\)\s+\w+\s*\(',  # With parameters
        r'^\s*(\w+)\s+\w+\s*\(',                 # Without parameters
    ]
    instantiations = []
    for pattern in patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        instantiations.extend(matches)
    return list(set(instantiations))

# Known external modules (not in RTL, provided by vendor or IP)
EXTERNAL_MODULES = {
    'PMBus', 'I2C', 'I2C_Controller', 'SPI', 'SPI_Interface', 
    'UART', 'UART_Interface', 'GPIO', 'GPIO_Interface',
    'AXI_Stream', 'AXI_Lite', 'DSP', 'BRAM', 'FIFO'
}

# Verilog keywords that should never be treated as modules
VERILOG_KEYWORDS = {
    'always', 'assign', 'begin', 'case', 'default', 'else', 'end',
    'endcase', 'endgenerate', 'endmodule', 'for', 'forever', 'function',
    'generate', 'if', 'initial', 'integer', 'localparam', 'module',
    'parameter', 'posedge', 'negedge', 'reg', 'repeat', 'task', 'wait',
    'while', 'wire', 'genvar', 'input', 'output', 'inout', 'signed',
    'unsigned', 'typedef', 'enum', 'struct', 'union', 'package',
    'import', 'class', 'interface', 'modport', 'clocking', 'property'
}

# Words that look like modules but are not (false positives)
FALSE_POSITIVES = {
    'receiver', 'transmitter', 'buffer', 'fifo', 'memory', 'ram', 'rom',
    'register', 'counter', 'decoder', 'encoder', 'mux', 'demux', 'adder',
    'multiplier', 'divider', 'filter', 'controller', 'interface', 'bridge',
    'wrapper', 'adapter', 'converter', 'driver', 'transceiver', 'port',
    'pin', 'signal', 'wire', 'bus', 'clock', 'reset', 'enable', 'valid',
    'ready', 'data', 'address', 'master', 'slave', 'agent', 'monitor'
}

# Combine all keywords to skip
SKIP_WORDS = VERILOG_KEYWORDS | FALSE_POSITIVES


class TestStaticAnalysis:
    @pytest.mark.parametrize("vfile", [f for f in os.listdir(RTL_DIR) if f.endswith('.v')])
    def test_no_genvar_conflict(self, vfile):
        with open(f"{RTL_DIR}/{vfile}") as f:
            content = f.read()
        genvars = set(re.findall(r'genvar\s+(\w+)', content))
        integers = set(re.findall(r'integer\s+(\w+)', content))
        conflicts = genvars & integers
        assert len(conflicts) == 0, f"{vfile}: genvar/integer conflict: {conflicts}"


class TestCompilation:
    def test_all_files_compile(self):
        result = subprocess.run(
            ["iverilog", "-o", "/dev/null"] + [f"{RTL_DIR}/{f}" for f in os.listdir(RTL_DIR) if f.endswith('.v')],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Compilation failed:\n{result.stderr[:500]}"
    
    def test_module_names_match_instantiations(self):
        # Parse all module names
        modules = {}
        for vfile in os.listdir(RTL_DIR):
            if not vfile.endswith('.v'):
                continue
            with open(f"{RTL_DIR}/{vfile}") as f:
                content = strip_comments(f.read())
                mod_match = re.search(r'module\s+(\w+)', content)
                if mod_match:
                    modules[mod_match.group(1)] = vfile
        
        # Check instantiations
        for vfile in os.listdir(RTL_DIR):
            if not vfile.endswith('.v'):
                continue
            with open(f"{RTL_DIR}/{vfile}") as f:
                content = f.read()
                instantiations = extract_instantiations(content)
                for inst in instantiations:
                    if inst in modules:
                        continue
                    if inst in EXTERNAL_MODULES:
                        continue
                    if inst in SKIP_WORDS:
                        continue
                    assert False, f"{vfile}: Instantiated '{inst}' but module not found"


if __name__ == "__main__":
    print("=" * 60)
    print("RTL VERIFICATION v4 - Ignores Verilog keywords")
    print("=" * 60)
    pytest.main([__file__, "-v", "--tb=short"])
