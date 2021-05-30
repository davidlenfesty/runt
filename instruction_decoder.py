from nmigen import *
from opcodes import Opcodes

class InstructionDecoder(Elaboratable):
    def __init__(self):
        #### Input
        self.instr = Signal(unsigned(32))

        #### Output
        self.opcode = Signal(Opcodes)
        self.funct3 = Signal(unsigned(3))
        self.funct7 = Signal(unsigned(7))
        self.imm = Signal(32)
        self.immu = Signal(unsigned(32))
        # Register selection
        self.src1 = Signal(unsigned(5))
        self.src2 = Signal(unsigned(5))
        self.dest = Signal(unsigned(5))
        self.base = Signal(unsigned(5))

    def ports(self) -> tuple:
        return (self.instr, self.opcode, self.funct3, self.imm, self.immu, self.src1, self.dest, self.base)

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.opcode.eq(self.instr[0:6])
        # Default immediate to 0 whenever we can
        m.d.comb += self.imm.eq(0)
        m.d.comb += self.immu.eq(0)
        m.d.comb += self.dest.eq(self.instr[7:11]) # TODO will likely move back into the switch

        with m.Switch(self.opcode):
            # I-Type Instructions
            with m.Case(Opcodes.OP_IMM, Opcodes.JALR, Opcodes.LOAD, Opcodes.MISC_MEM):
                # TODO does this sign-extend?
                m.d.comb += self.imm.eq(self.instr[20:31].as_signed())
                m.d.comb += self.immu.eq(self.instr[20:31])

                m.d.comb += self.funct3.eq(self.instr[12:14])
                m.d.comb += self.src1.eq(self.instr[15:19])

            # U-Type Instructions
            with m.Case(Opcodes.LUI, Opcodes.AUIPC):
                m.d.comb += self.imm[12:31].eq(self.instr[12:31].as_signed())
                m.d.comb += self.immu[12:31].eq(self.instr[12:31])

            # R-Type Instructions
            with m.Case(Opcodes.OP):
                m.d.comb += self.funct3.eq(self.instr[12:14])
                m.d.comb += self.funct7.eq(self.instr[25:31])
                m.d.comb += self.src1.eq(self.instr[15:19])
                m.d.comb += self.src2.eq(self.instr[20:24])

            # J-Type Instructions
            with m.Case(Opcodes.JAL):
                imm = Cat(Const(0, shape=1), self.instr[21:30], self.instr[20], self.instr[12:19], self.instr[31])
                m.d.comb += self.imm.eq(imm.as_signed())
                m.d.comb += self.immu.eq(imm.as_unsigned())

            # B-Type Instructions
            with m.Case(Opcodes.BRANCH):
                imm = Cat(Const(0, shape=1), self.instr[8:11], self.instr[25:30], self.instr[7], self.instr[31])
                m.d.comb += self.imm.eq(imm.as_signed())
                m.d.comb += self.immu.eq(imm.as_unsigned())
                m.d.comb += self.funct3.eq(self.instr[12:14])
                m.d.comb += self.src1.eq(self.instr[15:19])
                m.d.comb += self.src2.eq(self.instr[20:24])

            # S-Type Instructions
            with m.Case(Opcodes.STORE):
                m.d.comb += self.funct3.eq(self.instr[12:14])
                m.d.comb += self.base.eq(self.instr[15:19])
                m.d.comb += self.src1.eq(self.instr[20:24])
                m.d.comb += self.imm.eq(Cat(self.instr[7:11], self.instr[25:31]).as_signed())
                m.d.comb += self.immu.eq(Cat(self.instr[7:11], self.instr[25:31]).as_unsigned())

        return m
