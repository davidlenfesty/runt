from nmigen import *
from nmigen.hdl.rec import Layout, Record
from enum import Enum


from opcodes import Opcodes
from instruction_decoder import InstructionDecoder
from regfile import RegisterFile

# TODO replace this with a proper wishbone bus
class DumbMemoryBus(Record):
    def __init__(self):
        super().__init__(Layout([
            ("rw", 1),
            ("addr", unsigned(32)),
            ("data", unsigned(32)),
            ("i_valid", 1),
            ("o_ready", 1),
        ]))

class IntImmediate(Enum):
    # Integer opperations on immediates, as defined by funct3 field
    ADDI  = 0b000
    SLTI  = 0b010
    SLTIU = 0b011
    XORI  = 0b100
    ORI   = 0b110
    ANDI  = 0b111

    SLLI  = 0b001
    SRxI  = 0b101

class IntRegReg(Enum):
    # Integer register-register operations, as defined by funct3 field
    ADD  = 0b000 # Also SUB
    SLL  = 0b001
    SLT  = 0b010
    SLTU = 0b011
    XOR  = 0b100
    SRx  = 0b101 # SRL/SRA
    OR   = 0b110
    AND  = 0b111

class BranchCondition(Enum):
    # Different BRANCH conditions, as defined by funct3 field
    BEQ  = 0b000
    BNE  = 0b001
    BLT  = 0b100
    BGE  = 0b101
    BLTU = 0b110
    BGEU = 0b111

class LSWidth(Enum):
    B = 0b00
    H = 0b01
    W = 0b10

class RV32ICore(Elaboratable):
    """Basic RV32-I core."""
    def __init__(self):

        self.mem = DumbMemoryBus()
        self.decoder = InstructionDecoder()

    def elaborate(self, platform):
        m = Module()
        m.submodules.decoder = self.decoder
        m.submodules.regfile = RegisterFile()

        regfile = m.submodules.regfile

        pc = Signal(unsigned(32))
        instr = Signal(unsigned(32)) # Internal reg to hold instrunction data

        decoder_ports = self.decoder.ports()
        funct3 = decoder_ports[2]
        imm = decoder_ports[3]
        immu = decoder_ports[4]
        src = decoder_ports[5]
        dest = decoder_ports[6]

        m.d.comb += self.decoder.instr.eq(instr)

        m.d.sync += regfile.wen.eq(0)
        m.d.sync += self.mem.i_valid.eq(0)


        # Load/store variables
        load_dest = Signal(unsigned(5))
        load_unsigned = Signal()
        ls_width = Signal(LSWidth)

        with m.FSM():
            with m.State("READ_PC"):
                # Issue memory read to PC
                m.d.sync += self.mem.rw.eq(0)
                m.d.sync += self.mem.addr.eq(pc)
                m.d.sync += self.mem.i_valid.eq(1)
                m.next = "LOAD_PC"

            with m.State("LOAD_PC"):
                m.d.sync += self.mem.i_valid.eq(0)

                with m.If(self.mem.o_ready):
                    m.d.sync += instr.eq(self.mem.data)
                    m.next = "DECODE"

            with m.State("DECODE"):
                # TODO likely integer ops should be deferred and split into a seperate ALU,
                # Where instead of doing everything here, I load all the values into the ALU
                # and pull from the results.

                # TODO should I pull the src1/src2/dest assignments out to all the time?
                with m.Switch(self.decoder.opcode):
                    with m.Case(Opcodes.OP_IMM):
                        m.next = "READ_PC"

                        m.d.comb += regfile.raddr1.eq(src)
                        m.d.comb += regfile.waddr.eq(dest)
                        m.d.sync += regfile.wen.eq(1)

                        with m.Switch(funct3):
                            with m.Case(IntImmediate.ADDI):
                                m.d.sync += regfile.wdata.eq(regfile.rdata1 + imm)

                            with m.Case(IntImmediate.SLTI):
                                m.d.sync += regfile.wdata.eq(regfile.rdata1 < imm)

                            with m.Case(IntImmediate.SLTIU):
                                # TODO evaluate if this casts correctly and does what I want
                                m.d.sync += regfile.wdata.eq(regfile.rdata1.as_unsigned() < immu)

                            with m.Case(IntImmediate.ANDI):
                                m.d.sync += regfile.wdata.eq(regfile.rdata1 & immu)

                            with m.Case(IntImmediate.ORI):
                                m.d.sync += regfile.wdata.eq(regfile.rdata1 | immu)

                            with m.Case(IntImmediate.XORI):
                                m.d.sync += regfile.wdata.eq(regfile.rdata1 ^ immu)

                            with m.Case(IntImmediate.SLLI):
                                m.d.sync += regfile.wdata.eq(regfile.rdata1.as_unsigned() << immu[0:4])

                            with m.Case(IntImmediate.SRxI):
                                with m.If(immu[10]):
                                    # SRAI
                                    m.d.sync += regfile.wdata.eq(regfile.rdata1.as_unsigned() >> immu[0:4])

                                with m.Else():
                                    # SRLI
                                    m.d.sync += regfile.wdata.eq(regfile.rdata1 >> immu[0:4])

                    with m.Case(Opcodes.LUI):
                        m.d.comb += regfile.waddr.eq(dest)
                        m.d.sync += regfile.wdata.eq(immu)
                        m.d.sync += regfile.wen.eq(1)

                    with m.Case(Opcodes.AUIPC):
                        m.d.comb += regfile.waddr.eq(dest)
                        m.d.sync += regfile.wdata.eq(pc + immu)

                    with m.Case(Opcodes.OP):
                        m.next = "READ_PC"

                        m.d.comb += regfile.raddr1.eq(self.decoder.src1)
                        m.d.comb += regfile.raddr2.eq(self.decoder.src2)
                        m.d.comb += regfile.waddr.eq(self.decoder.dest)
                        m.d.sync += regfile.wen.eq(1)

                        with m.Switch(self.decoder.funct7):
                            with m.Case(IntRegReg.ADD):
                                with m.If(self.decoder.funct7[5]):
                                    # SUB
                                    m.d.sync += regfile.wdata.eq(regfile.rdata1 - regfile.rdata2)
                                with m.Else():
                                    # ADD
                                    m.d.sync += regfile.wdata.eq(regfile.rdata1 + regfile.rdata2)
                            with m.Case(IntRegReg.SLL):
                                m.d.sync += regfile.wdata.eq(regfile.rdata1 << regfile.rdata2[0:4])
                            with m.Case(IntRegReg.SLT):
                                m.d.sync += regfile.wdata.eq(regfile.rdata1 < regfile.rdata2)
                            with m.Case(IntRegReg.SLTU):
                                rdata1 = regfile.rdata1.as_unsigned()
                                rdata2 = regfile.rdata2.as_unsigned()
                                m.d.sync += regfile.wdata.eq(rdata1 < rdata2)
                            with m.Case(IntRegReg.XOR):
                                m.d.sync += regfile.wdata.eq(regfile.rdata1 ^ regfile.rdata2)
                            with m.Case(IntRegReg.SRx):
                                with m.If(self.decoder.funct7[5]):
                                    # SRA
                                    m.d.sync += regfile.wdata.eq(regfile.rdata1 << regfile.rdata2[0:4])
                                with m.Else():
                                    # SRL
                                    m.d.sync += regfile.wdata.eq(regfile.rdata1.as_unsigned() << regfile.rdata2[0:4])
                            with m.Case(IntRegReg.OR):
                                m.d.sync += regfile.wdata.eq(regfile.rdata1 | regfile.rdata2)
                            with m.Case(IntRegReg.AND):
                                m.d.sync += regfile.wdata.eq(regfile.rdata1 & regfile.rdata2)

                    # TODO raise misalign exception
                    with m.Case(Opcodes.JAL):
                        m.d.comb += regfile.waddr.eq(self.decoder.dest)
                        m.d.sync += regfile.wdata.eq(pc + 4)
                        m.d.sync += regfile.wen.eq(1)
                        m.d.sync += pc.eq(pc + self.decoder.imm)

                    # TODO raise misalign exception
                    with m.Case(Opcodes.JALR):
                        m.d.comb += regfile.waddr.eq(self.decoder.dest)
                        m.d.comb += regfile.raddr1.eq(self.decoder.src1)
                        m.d.sync += regfile.wdata.eq(pc + 4)
                        m.d.sync += regfile.wen.eq(1)
                        m.d.sync += pc.eq(regfile.rdata1 + self.decoder.imm)

                    # TODO misalign exception
                    with m.Case(Opcodes.BRANCH):
                        m.d.comb += regfile.raddr1.eq(self.decoder.src1)
                        m.d.comb += regfile.raddr2.eq(self.decoder.src2)
                        branch_condition = Signal()

                        with m.Switch(self.decoder.funct3):
                            with m.Case(BranchCondition.BEQ):
                                m.d.comb += branch_condition.eq(regfile.rdata1 == regfile.rdata2)
                            with m.Case(BranchCondition.BNE):
                                m.d.comb += branch_condition.eq(regfile.rdata1 != regfile.rdata2)
                            with m.Case(BranchCondition.BLT):
                                m.d.comb += branch_condition.eq(regfile.rdata1 < regfile.rdata2)
                            with m.Case(BranchCondition.BGE):
                                m.d.comb += branch_condition.eq(regfile.rdata1 >= regfile.rdata2)
                            with m.Case(BranchCondition.BLTU):
                                m.d.comb += branch_condition.eq(regfile.rdata1.as_unsigned() < regfile.rdata2.as_unsigned())
                            with m.Case(BranchCondition.BGEU):
                                m.d.comb += branch_condition.eq(regfile.rdata1.as_unsigned() >= regfile.rdata2.as_unsigned())

                        with m.If(branch_condition):
                            m.d.sync += pc.eq(pc + self.decoder.imm)

                    with m.Case(Opcodes.LOAD):
                        m.d.comb += regfile.raddr1.eq(self.decoder.src1)
                        m.d.sync += load_dest.eq(self.decoder.dest)

                        with m.If(~self.mem.o_ready):
                            m.next = "LOAD"
                            m.d.sync += self.mem.rw.eq(0)
                            m.d.sync += self.mem.addr.eq(regfile.rdata1 + self.decoder.imm)
                            m.d.sync += self.mem.i_valid.eq(1)
                            m.d.sync += ls_width.eq(self.decoder.funct3[0:1])
                            m.d.sync += load_unsigned.eq(self.decoder.funct3[2])

                    with m.Case(Opcodes.STORE):
                        m.d.comb += regfile.raddr1.eq(self.decoder.src1)
                        m.d.comb += regfile.raddr2.eq(self.decoder.base)

                        with m.If(~self.mem.o_ready):
                            m.next = "STORE"
                            m.d.sync += self.mem.rw.eq(1)
                            m.d.sync += self.mem.addr.eq(regfile.rdata2 + self.decoder.imm)
                            m.d.sync += self.mem.data.eq(regfile.rdata1)
                            m.d.sync += self.mem.i_valid.eq(1)
                            m.d.sync += ls_width.eq(self.decoder.funct3[0:1])

                    with m.Case(Opcodes.MISC_MEM):
                        with m.If(self.decoder.funct3 == 0):
                            # TODO impl NOP
                            pass
                        with m.Else():
                            # TODO raise invalid instruction
                            pass

                    with m.Case(Opcodes.SYSTEM):
                        # TODO need to impl privileged stuff before I can do this
                        pass

                    # TODO raise invalid instruction
                    with m.Default():
                        pass


            with m.State("LOAD"):
                m.d.comb += regfile.waddr.eq(load_dest)
                m.d.sync += regfile.wdata.eq(self.mem.data)

                with m.If(self.mem.o_ready):
                    m.d.sync += regfile.wen.eq(1)
                    m.next = "READ_PC"

            with m.State("STORE"):
                # TODO this shouldn't be necessary, just temp until memory is handled properly
                m.next = "READ_PC"

        return m

if __name__ == "__main__":
    from nmigen.cli import main
    top = RV32ICore()

    main(top)
