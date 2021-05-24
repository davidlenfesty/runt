from nmigen import *
from opcodes import Opcodes

class InstructionDecoder(Elaboratable):
    def __init__(self):
        #### Input
        self.instr = Signal(unsigned(32))

        #### Output
        self.opcode = Signal(Opcodes)
        self.funct = Signal(unsigned(3))
        self.imm = Signal(32)
        self.immu = Signal(unsigned(32))
        # Register selection
        self.src = Signal(unsigned(5))
        self.dest = Signal(unsigned(5))
        self.base = Signal(unsigned(5))

    def ports(self) -> tuple:
        return (self.instr, self.opcode, self.funct, self.imm, self.immu, self.src, self.dest, self.base)

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.opcode.eq(self.instr[0:6])

        # TODO do actual sign extension

        with m.Switch(self.opcode):
            with m.Case(Opcodes.OP_IMM):
                m.d.comb += self.imm[0:10].eq(self.instr[20:30])
                for i in range(11, 32):
                    m.d.comb += self.imm[i].eq(self.instr[31])

                m.d.comb += self.immu[0:11].eq(self.instr[20:31])
                m.d.comb += self.immu[12:31].eq(0)

                m.d.comb += self.funct.eq(self.instr[12:14])
                m.d.comb += self.src.eq(self.instr[15:19])
                m.d.comb += self.dest.eq(self.instr[7:11])

        return m
