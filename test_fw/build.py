#!/usr/bin/env python
from subprocess import run

prefix = "riscv32-unknown-elf"

run(f"{prefix}-as test.S -o test.o".split())
run(f"{prefix}-ld -T test_link.ld test.o -o test.elf".split())
run(f"{prefix}-objcopy -O binary test.elf test.bin".split())