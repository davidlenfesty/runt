from nmigen import *
from dataclasses import dataclass
from enum import enum

@dataclass
class MachineConfig:
    vendor_id: int
    arch_id: int
    impid: int
    hartid: int

@dataclass
class MachineCounters:
    cycle: Signal
    instret: Signal
    time: Signal

@enum
class Priv:
    # Machine-level
    MRO = 1
    MRW = 2
    # Supervisor-level
    SRO = 3
    SRW = 4
    # Hypervisor-level
    HRO = 5
    HRW = 6
    # User-level
    URO = 7
    URW = 8

# I only need to support M-level CSRs, everything else is not necessary

class CSR:
    def __init__(self, address: int, priv: Priv = Priv.MRW, sig: Signal = None):
        if sig is None:
            self.sig = Signal(32)
        else:
            self.sig = sig
        self.address = address
        self.privilege = priv


# Really the way to go here is to make an extra CSR class or something which hides stuff
class CSRTable(Elaboratable):
    def __init__(self, machine_config: MachineConfig, machine_counters: MachineCounters):
        #### Machine CSRs
        # Machine Information Registers
        self.mvendorid  = CSR(0xF11, Priv.MRO, Const(machine_config.vendor_id))
        self.marchid    = CSR(0xF12, Priv.MRO, Const(machine_config.arch_id))
        self.impid      = CSR(0xF13, Priv.MRO, Const(machine_config.impid))
        self.mhartid    = CSR(0xF14, Priv.MRO, Const(machine_config.hartid))

        # Machine Trap Setup
        self.mstatus    = CSR(0x300)
        self.misa       = CSR(0x301)
        self.medeleg    = CSR(0x302)
        self.mideleg    = CSR(0x303)
        self.mie        = CSR(0x304)
        self.mtvec      = CSR(0x305)

        # Machine Trap Handling
        self.mscratch   = CSR(0x340)
        self.mepc       = CSR(0x341)
        self.mcause     = CSR(0x342)
        self.mtval      = CSR(0x343)
        self.mip        = CSR(0x344)

        # Machine Counter/Timers
        self.mcycle     = CSR(0xB00, machine_counters.cycle)
        self.minstret   = CSR(0xB02, machine_counters.instret)

        # Machine Counter Setup
        self.mcountinhibit  = CSR(0x320)
