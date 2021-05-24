from enum import Enum


class Opcodes(Enum):
    """List of all opcodes for RV32I instruction set"""
    LOAD = 0b00000
    LOAD_FP = 0b00001
    CUSTOM_0 = 0b00010
    MISC_MEM = 0b00011
    OP_IMM = 0b00100
    AUIPC = 0b00101
    OP_IMM_32 = 0b00110
    # 48b?

    STORE = 0b01000
    STORE_FP = 0b01001
    CUSTOM_1 = 0b01010
    AMO = 0b01011
    OP = 0b01100
    LUI = 0b01101
    OP_32  = 0b01110
    # 64b?

    MADD = 0b10000
    MSUB = 0b10001
    NMSUB = 0b10010
    NMADD = 0b10011
    OP_FP = 0b10100
    # reserved
    CUSTOM_2 = 0b10110
    # 48b?

    BRANCH = 0b11000
    JALR = 0b11001
    # reserved
    JAL = 0b11011
    SYSTEM = 0b11100
    # reserved
    CUSTOM_3 = 0b11110
    # >80b?
