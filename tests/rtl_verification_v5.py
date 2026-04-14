#!/usr/bin/env python3
"""RTL Verification v5 - Correct module instantiation extraction"""

import os
import re
import subprocess
import pytest

RTL_DIR = "fpga/rtl"

def strip_comments(content):
    """Remove Verilog comments"""
    # Remove // comments
    content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
    # Remove /* */ comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    return content

def extract_module_instantiations(content):
    """
    Correctly extract module instantiations.
    Pattern: ModuleName #(params) instance_name ( .port(value), .port(value) );
    """
    content = strip_comments(content)
    
    # Remove strings (they might contain parentheses)
    content = re.sub(r'"[^"]*"', '', content)
    
    # Match module instantiation pattern
    # Module name must start with capital letter (by convention) or be in our known list
    # Followed by optional #(parameters)
    # Followed by instance name
    # Followed by ( port connections )
    pattern = r'\b([A-Z][a-zA-Z0-9_]*)\s+(?:#\([^)]*\)\s+)?([a-z][a-zA-Z0-9_]*)\s*\('
    
    matches = re.findall(pattern, content)
    return [m[0] for m in matches]  # Return module names

# Known external modules (not in RTL, will be provided by vendor)
EXTERNAL_MODULES = {
    'PMBus', 'I2C', 'SPI', 'UART', 'GPIO',
    'AXI_Stream', 'AXI_Lite', 'DSP', 'BRAM', 'FIFO'
}


class TestCompilation:
    def test_all_files_compile(self):
        """All RTL files must compile together"""
        result = subprocess.run(
            ["iverilog", "-o", "/dev/null"] + [f"{RTL_DIR}/{f}" for f in os.listdir(RTL_DIR) if f.endswith('.v')],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Compilation failed:\n{result.stderr[:500]}"
    
    def test_no_missing_modules(self):
        """Every instantiated module must exist in RTL or be external"""
        # Parse all module names from RTL files
        modules = {}
        for vfile in os.listdir(RTL_DIR):
            if not vfile.endswith('.v'):
                continue
            with open(f"{RTL_DIR}/{vfile}") as f:
                content = strip_comments(f.read())
                mod_match = re.search(r'^\s*module\s+(\w+)', content, re.MULTILINE)
                if mod_match:
                    modules[mod_match.group(1)] = vfile
        
        # Check all instantiations
        missing_modules = []
        for vfile in os.listdir(RTL_DIR):
            if not vfile.endswith('.v'):
                continue
            with open(f"{RTL_DIR}/{vfile}") as f:
                content = f.read()
                instantiations = extract_module_instantiations(content)
                for inst in instantiations:
                    if inst not in modules and inst not in EXTERNAL_MODULES:
                        missing_modules.append(f"{vfile}: {inst}")
        
        if missing_modules:
            print("\n❌ Missing modules found:")
            for mm in missing_modules:
                print(f"   - {mm}")
            pytest.fail(f"Missing modules: {len(missing_modules)} found")


if __name__ == "__main__":
    print("=" * 60)
    print("RTL VERIFICATION v5 - Correct instantiation extraction")
    print("=" * 60)
    pytest.main([__file__, "-v", "-s"])
