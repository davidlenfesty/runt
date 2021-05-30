# runt

A small, underperforming RV32I core, written in nMigen.

I want to get it to the point where I could actually use it in a design, but I doubt it will have
any practical use, especially when compared to a VexRiscV or picorv32 core.

This is my first CPU, and I also somewhat intentionally didn't look at any resources,
so it will likely be full of questionable design decisions that anyone with any experience
would have avoided.

## Milestones

- [ ] Full RV32I implementation, able to run code in simulation (not verified working correctly at
      this point)
- [ ] Full coverage with riscv-tests, verified working.
- [ ] Integrated with some hardware to make an """SoC""", running on my Arty A7
- [ ] Full coverage with riscv-formal
- [ ] (Maybe...) work on improving performance, add caching/prefetch, pipeline it, etc.
