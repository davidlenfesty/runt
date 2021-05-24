from nmigen import *
from enum import Enum


from opcodes import Opcodes
from instruction_decoder import InstructionDecoder
from regfile import RegisterFile

# TODO replace this with a proper wishbone bus
MemoryBus = Record([
    ("rw", 1),
    ("addr", 32),
    ("data", 32),
    ("i_valid", 1),
    ("o_ready", 1),
])

class IntImmediate(Enum):
    ADDI = 0b000
    SLTI = 0b010
    SLTIU = 0b011
    XORI = 0b100
    ORI = 0b110
    ANDI = 0b111

class RV32ICore(Elaboratable):
    """Basic RV32-I core."""
    def __init__(self):

        self.mem = MemoryBus
        self.decoder = InstructionDecoder()

    def elaborate(self, platform):
        m = Module()
        m.submodules.decoder = self.decoder
        m.submodules.regfile = RegisterFile()

        regfile = m.submodules.regfile

        pc = Signal(unsigned(32))
        instr = Signal(unsigned(32)) # Internal reg to hold instrunction data
        r = Array([Signal(32) for _ in range(32)])

        decoder_ports = self.decoder.ports()
        funct = decoder_ports[1]
        funct = decoder_ports[2]
        imm = decoder_ports[3]
        immu = decoder_ports[4]
        src = decoder_ports[5]
        dest = decoder_ports[6]

        m.d.comb += self.decoder.instr.eq(instr)

        m.d.sync += regfile.wen.eq(0)

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
                with m.Switch(self.decoder.opcode):
                    with m.Case(Opcodes.OP_IMM):
                        m.next = "READ_PC"

                        m.d.comb += regfile.raddr1.eq(imm)
                        m.d.comb += regfile.waddr.eq(imm)
                        m.d.sync += regfile.wen.eq(1)

                        with m.Switch(funct):
                            with m.Case(IntImmediate.ADDI):
                                m.d.sync += regfile.wdata.eq(regfile.raddr1 + imm)

                            with m.Case(IntImmediate.SLTI):
                                m.d.sync += regfile.wdata.eq(regfile.raddr1 + imm)

                            with m.Case(IntImmediate.SLTIU):
                                m.d.sync += regfile.wdata.eq(regfile.raddr1 + immu)

                            with m.Case(IntImmediate.ANDI):
                                m.d.sync += regfile.wdata.eq(regfile.raddr1 & immu)

                            with m.Case(IntImmediate.ORI):
                                m.d.sync += regfile.wdata.eq(regfile.raddr1 | immu)

                            with m.Case(IntImmediate.XORI):
                                m.d.sync += regfile.wdata.eq(regfile.raddr1 ^ immu)

        return m

if __name__ == "__main__":
    from nmigen.cli import main
    top = RV32ICore()

    main(top)
