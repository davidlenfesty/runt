from nmigen import *

class CycleCounter(Elaboratable):
    # Simple clock cycle counter
    def __init__(self):
        self.cnt = Signal(unsigned(64))

    def ports(self) -> tuple:
        return (self.cnt)

    def elaborate(self, platform):
        m = Module()

        # Update count
        m.d.sync += self.cnt.eq(self.cnt + 1)

        return m

class TimeCounter(Elaboratable):
    def __init__(self):
        self.overflow = Signal(unsigned(32))
        self.cnt = Signal(unsigned(64))

    def ports(self) -> tuple:
        return (self.cnt)

    def elaborate(self, platform):
        m = Module()

        # TODO figure out how to extract clock frequency
        with m.If(self.overflow < 8_000_000):
            m.d.sync += self.overflow.eq(self.overflow + 1)
        with m.Else():
            m.d.sync += self.overflow.eq(0)
            m.d.sync += self.cnt.eq(self.cnt + 1)

        return m
