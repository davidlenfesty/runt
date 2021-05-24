from nmigen import *

class RegisterFile(Elaboratable):
    def __init__(self):
        self.regs = Array([Signal(32) for _ in range(32)])

        self.wen = Signal()
        self.waddr = Signal(unsigned(5))
        self.raddr1 = Signal(unsigned(5))
        self.raddr2 = Signal(unsigned(5))
        self.wdata = Signal(unsigned(32))
        self.rdata1 = Signal(unsigned(32))
        self.rdata2 = Signal(unsigned(32))

    def elaborate(self, platform):
        m = Module()

        with m.If(self.wen):
            m.d.sync += self.regs[self.waddr].eq(self.wdata)

        with m.If(self.raddr1 == 0):
            m.d.comb += self.rdata1.eq(0)
        with m.Else():
            m.d.comb += self.rdata1.eq(self.regs[self.raddr1])

        with m.If(self.raddr2 == 0):
            m.d.comb += self.rdata2.eq(0)
        with m.Else():
            m.d.comb += self.rdata2.eq(self.regs[self.raddr2])

        return m
