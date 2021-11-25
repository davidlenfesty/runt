OUTPUT_ARCH("riscv")
ENTRY(_start)

MEMORY
{
    ROM (rx)    : ORIGIN = 0x00000000, LENGTH = 4K
}

SECTIONS
{
    .text :
    {
        . = ALIGN(4);
        KEEP(*(.init))
        *(.text)
        . = ALIGN(4);
    } >ROM
}