.section .text
.global _start
_start:
	li	x0, 0xDEADBEEF
    li  x1, 0x30
    li  x2, 0x20

    sub x3, x1, x2
