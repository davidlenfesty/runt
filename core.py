from nmigen import *
from nmigen.hdl.rec import Layout, Record
from enum import Enum


from opcodes import Opcodes
from instruction_decoder import InstructionDecoder
from regfile import RegisterFile
import nmigen_soc.wishbone as wishbone
from nmigen_soc.memory import *

# TODO replace this with a proper wishbone bus
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
    def __init__(self, mem_bus: wishbone.Interface):

        self.decoder = InstructionDecoder()
        self.mem = mem_bus

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

        # Default memory bus to inactive
        m.d.sync += self.mem.stb.eq(0)
        m.d.sync += self.mem.cyc.eq(0)

        # Load/store variables
        load_dest = Signal(unsigned(5))
        load_unsigned = Signal()
        ls_width = Signal(LSWidth)

        with m.FSM():
            with m.State("READ_PC"):
                # Issue memory read to PC
                # TODO there may be some issues with this naive WB implementation,
                #      specifically around slave ACK response, too tired atm to deal with it though
                m.d.sync += self.mem.cyc.eq(1)  # Valid bus cycle - begin wishbone bus operation
                m.d.sync += self.mem.stb.eq(1)  # Start data transfer cycle
                m.d.sync += self.mem.we.eq(0)   # Read data
                m.d.sync += self.mem.adr.eq(pc)
                # TODO do I need to set sel? what should granularity of bus be?

                with m.If(self.mem.ack):
                    # De-assert bus
                    m.d.sync += self.mem.cyc.eq(0)
                    m.d.sync += self.mem.stb.eq(0)
                    m.d.sync += instr.eq(self.mem.dat_r)
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

                    #with m.Case(Opcodes.LOAD):
                    #    m.d.comb += regfile.raddr1.eq(self.decoder.src1)
                    #    m.d.sync += load_dest.eq(self.decoder.dest)

                    #    with m.If(~self.mem.o_ready):
                    #        m.next = "LOAD"
                    #        m.d.sync += self.mem.rw.eq(0)
                    #        m.d.sync += self.mem.addr.eq(regfile.rdata1 + self.decoder.imm)
                    #        m.d.sync += self.mem.i_valid.eq(1)
                    #        m.d.sync += ls_width.eq(self.decoder.funct3[0:1])
                    #        m.d.sync += load_unsigned.eq(self.decoder.funct3[2])

                    #with m.Case(Opcodes.STORE):
                    #    m.d.comb += regfile.raddr1.eq(self.decoder.src1)
                    #    m.d.comb += regfile.raddr2.eq(self.decoder.base)

                    #    with m.If(~self.mem.o_ready):
                    #        m.next = "STORE"
                    #        m.d.sync += self.mem.rw.eq(1)
                    #        m.d.sync += self.mem.addr.eq(regfile.rdata2 + self.decoder.imm)
                    #        m.d.sync += self.mem.data.eq(regfile.rdata1)
                    #        m.d.sync += self.mem.i_valid.eq(1)
                    #        m.d.sync += ls_width.eq(self.decoder.funct3[0:1])

                    with m.Case(Opcodes.MISC_MEM):
                        with m.If(self.decoder.funct3 == 0):
                            # TODO impl NOP
                            pass
                        with m.Else():
                            # TODO raise invalid instruction
                            pass

                    with m.Case(Opcodes.SYSTEM):
                        # TODO need to impl privileged stuff before I can do this
                        # Do I????
                        pass

                    # TODO raise invalid instruction
                    with m.Default():
                        pass


            #with m.State("LOAD"):
            #    # TODO convert to wishbone properly
            #    m.d.comb += regfile.waddr.eq(load_dest)
            #    m.d.sync += regfile.wdata.eq(self.mem.dat_r)

            #    with m.If(self.mem.ack):
            #        m.d.sync += regfile.wen.eq(1)
            #        m.next = "READ_PC"

            with m.State("STORE"):
                # TODO this shouldn't be necessary, just temp until memory is handled properly
                m.next = "READ_PC"

        return m

# TODO care about endianness in core
class SimulationMemory(Elaboratable):
    def __init__(self, mem_file: str, bus: wishbone.Interface):

        # Open memory file
        data = open(mem_file, "rb").read()

        self.bus = bus

        self.memory = Memory(width=32, depth=0x1000, init=data)
        self.r_port = self.memory.read_port()


    def elaborate(self, platform):
        m = Module()

        # TODO what are submodules again?
        #      do they just have to be defined to elaborate properly?
        m.submodules.r_port = self.r_port

        # Wait an extra cycle after getting address for memory latency
        cyc_latch = Signal(1)
        m.d.sync += cyc_latch.eq(self.bus.cyc)
        # The AND here is needed to respond immediately to CYC deassertion
        m.d.sync += self.bus.ack.eq(cyc_latch & self.bus.cyc)

        # Operate on words
        m.d.comb += self.r_port.addr.eq(self.bus.adr >> 2)

        # Write data out to bus
        m.d.sync += self.bus.dat_w.eq(self.r_port.data)

        return m

class SimTop(Elaboratable):
    def __init__(self):
        master_wb = wishbone.Interface(addr_width=32, data_width=32)
        memory_wb = wishbone.Interface(addr_width=32, data_width=32)
        master_wb.connect(memory_wb)

        self.cpu = RV32ICore(master_wb)
        self.memory = SimulationMemory("test.bin", memory_wb)

    def elaborate(self, platform):
        m = Module()

        m.submodules.cpu = self.cpu
        m.submodules.memory = self.memory

        return m

if __name__ == "__main__":
    from nmigen.cli import main
    #top = RV32ICore(wishbone.Interface(addr_width=32, data_width=32))
    top = SimTop()

    main(top)
