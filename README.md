# RISC-V Single-Cycle Processor

A modular single-cycle RISC-V processor implemented in synthesizable Verilog,
targeting the RV32I base integer instruction set. Designed for educational
clarity and as a portfolio project demonstrating RTL design, computer
architecture, and hardware verification skills.

> **Repository description:**
> Modular single-cycle RISC-V processor in Verilog with custom assembler,
> self-checking testbench, and GTKWave simulation.

## Overview

This processor executes one instruction per clock cycle through a classic
fetch → decode → execute → memory → write-back datapath. Each functional
unit (ALU, register file, control unit, etc.) is a separate Verilog module
with clean interfaces, making the design easy to understand, extend, and
potentially pipeline.

The project includes a self-checking testbench that verifies **all 31
implemented instructions** with 33 automated checks, a two-pass Python
assembler with label support, and full Make-based build automation for
Icarus Verilog.

## Features

- **31 RV32I instructions** implemented and verified (see table below)
- **Modular design** — 10 separate RTL modules with clear interfaces
- **Self-checking testbench** — 33 automated pass/fail checks covering every
  instruction, edge cases, and architectural invariants
- **Dedicated branch comparator** — all six branch types (BEQ/BNE/BLT/BGE/
  BLTU/BGEU) with correct signed and unsigned comparison semantics
- **Python assembler** — two-pass assembler with automatic label resolution
  for branch and jump offsets
- **VCD waveform output** — inspect any signal cycle-by-cycle in GTKWave
- **Clean separation** — source RTL, testbench, and simulation output in
  distinct directories

## Architecture

```
                         ┌────────────────┐
                ┌───────►│ Instruction    │
                │        │ Memory (IMEM)  │
                │        └───────┬────────┘
                │                │ instruction [31:0]
         ┌──────┴──────┐        │
         │   Program   │        ▼
         │   Counter   │  ┌───────────────────────────────────────────┐
         │    (PC)     │  │            Instruction Decode             │
         └──────┬──────┘  │  opcode · funct3 · funct7 · rs1/rs2/rd   │
                │         │  immediate fields                         │
         pc_next│         └──┬──────────┬──────────┬─────────────┬────┘
                │            │          │          │             │
                │            ▼          ▼          ▼             ▼
                │     ┌──────────┐ ┌─────────┐ ┌────────┐ ┌──────────┐
                │     │ Control  │ │  ALU    │ │ Imm    │ │ Register │
                │     │  Unit    │ │ Control │ │ Gen    │ │  File    │
                │     └────┬─────┘ └────┬────┘ └───┬────┘ └──┬───┬──┘
                │          │            │          │       rd1│   │rd2
                │   control│       alu_ │     imm_ │          │   │
                │   signals│       ctrl │     out  │          │   │
                │          │            │          │          ▼   ▼
                │          │            │          │     ┌──────────┐
                │          │            └──────────┼────►│   ALU    │
                │          │                       │     └────┬─────┘
                │          │                       │          │ result
                │          ▼                       │          ▼
                │   ┌──────────────┐               │   ┌──────────┐
                │   │    Branch    │               │   │   Data   │
                │   │  Comparator │               │   │  Memory  │
                │   └──────┬──────┘               │   └────┬─────┘
                │          │ branch_taken          │        │
                │          ▼                       ▼        ▼
                │   ┌──────────────────────────────────────────────┐
                └───┤              Write-back MUX                  │
                    │  ALU result / mem data / PC+4 / imm / AUIPC  │
                    └──────────────────────────────────────────────┘
```

## Repository Structure

```
riscv_core/
├── rtl/                    Synthesizable RTL modules
│   ├── alu.v               Arithmetic/logic unit (10 operations)
│   ├── alu_control.v       Secondary decoder: alu_op + funct3/7 → ALU op
│   ├── branch_comp.v       Dedicated branch comparator (6 conditions)
│   ├── control_unit.v      Main decoder: opcode → control signals
│   ├── dmem.v              Data memory — 256×32 RAM
│   ├── imem.v              Instruction memory — 256×32 ROM
│   ├── imm_gen.v           Immediate generator (I/S/B/U/J formats)
│   ├── pc.v                Program counter register
│   ├── regfile.v           32×32-bit register file (x0 hardwired to 0)
│   └── riscv_core.v        Top-level module wiring all submodules
│
├── tb/                     Testbench and tools
│   ├── tb_riscv_core.v     Self-checking Verilog testbench (33 checks)
│   └── asm.py              Two-pass RV32I assembler (Python 3)
│
├── sim/                    Simulation output (generated, not tracked)
│   └── .gitkeep
│
├── Makefile                Build/run automation (Icarus Verilog)
├── README.md
└── .gitignore
```

## Supported Instructions

All 31 instructions below are implemented in RTL **and** verified by the
self-checking testbench. The assembler (`asm.py`) supports all of them.

| Type | Instructions | Count |
|------|-------------|-------|
| **R-type** | `ADD` `SUB` `SLL` `SRL` `SRA` `SLT` `SLTU` `AND` `OR` `XOR` | 10 |
| **I-type (ALU)** | `ADDI` `SLTI` `SLTIU` `XORI` `ORI` `ANDI` `SLLI` `SRLI` `SRAI` | 9 |
| **Load** | `LW` | 1 |
| **Store** | `SW` | 1 |
| **Branch** | `BEQ` `BNE` `BLT` `BGE` `BLTU` `BGEU` | 6 |
| **Jump** | `JAL` `JALR` | 2 |
| **Upper imm** | `LUI` `AUIPC` | 2 |
| | **Total** | **31** |

## Datapath

The single-cycle datapath processes each instruction in one clock cycle:

1. **Fetch** — PC addresses instruction memory; `pc_plus4 = PC + 4`
2. **Decode** — Instruction fields are extracted; control unit generates
   datapath signals; register file reads `rs1`/`rs2`; immediate generator
   sign-extends the constant
3. **Execute** — ALU performs the operation selected by the ALU control unit;
   branch comparator evaluates branch conditions independently
4. **Memory** — Data memory performs a read (LW) or write (SW) as directed
5. **Write-back** — A multiplexer selects from ALU result, memory data,
   `PC+4` (JAL/JALR), immediate (LUI), or `PC + immediate` (AUIPC)

PC is updated to `PC+4`, `PC + offset` (branch/JAL), or
`(rs1 + imm) & ~1` (JALR).

## Control Path

- **Main decoder** (`control_unit.v`) — Decodes the 7-bit opcode into
  control signals: `reg_write`, `mem_read`, `mem_write`, `mem_to_reg`,
  `alu_src`, `branch`, `jump`, `jalr`, `lui`, `auipc`, and `alu_op[1:0]`
- **ALU control** (`alu_control.v`) — Combines `alu_op` with `funct3`
  and `funct7[5]` to produce the 4-bit ALU operation select
- **Branch comparator** (`branch_comp.v`) — Dedicated unit that evaluates
  BEQ/BNE/BLT/BGE/BLTU/BGEU using `funct3`; signed comparisons use
  `$signed()`, unsigned comparisons use default unsigned comparison

## Memory Model

| Memory | Size | Addressing | Behavior |
|--------|------|------------|----------|
| **IMEM** | 256 words (1 KB) | Word-addressed (`addr[31:2]`) | ROM loaded from `program.hex` via `$readmemh` |
| **DMEM** | 256 words (1 KB) | Word-addressed (`addr[31:2]`) | Combinational read, synchronous write |

Both memories are word-aligned only — no sub-word or misaligned access
support.

## Assembler

The assembler (`tb/asm.py`) is a minimal two-pass RV32I assembler:
- **Pass 1** — Collects label → byte address mappings
- **Pass 2** — Encodes instructions, automatically resolving branch/jump
  offsets from labels

### Usage

The test program is defined directly in the `program` list inside `asm.py`.
Edit this list, then run:

```bash
python3 tb/asm.py                   # outputs program.hex in current directory
python3 tb/asm.py sim/program.hex   # outputs to a specific path
```

### Assembly Syntax (in-file format)

```python
program = [
    ("ADDI",  "x1", "x0", 5),          # I-type: rd, rs1, imm
    ("ADD",   "x3", "x1", "x2"),       # R-type: rd, rs1, rs2
    ("SW",    "x3", 0,    "x0"),       # Store:  rs2, offset, rs1
    ("LW",    "x5", 0,    "x0"),       # Load:   rd, offset, rs1
    ("BEQ",   "x3", "x5", "LABEL"),    # Branch: rs1, rs2, label
    ("ADDI",  "x6", "x0", 111),       # (skipped if branch taken)
    "LABEL:",                           # label definition
    ("JAL",   "x7", "TARGET"),         # Jump:   rd, label
    ("JALR",  "x8", "x7", 0),         # JALR:   rd, rs1, imm
    ("LUI",   "x9", 0x12345),         # Upper:  rd, imm20
    ("AUIPC", "x10", 1),              # Upper:  rd, imm20
]
```

## Simulation

### Prerequisites

- [Icarus Verilog](https://steveicarus.github.io/iverilog/) (`iverilog`, `vvp`)
- [Python 3](https://www.python.org/) (for the assembler)
- [GTKWave](https://gtkwave.sourceforge.net/) (optional, for waveform viewing)

### Quick Start

```bash
# Assemble, compile, and run simulation
make run

# View waveforms (requires GTKWave)
make wave

# Clean generated files
make clean
```

### Manual Steps

```bash
# 1. Generate machine code from the test program
python3 tb/asm.py sim/program.hex

# 2. Compile RTL and testbench
cd sim && iverilog -g2012 -s tb_riscv_core -o sim.out \
    ../rtl/*.v ../tb/tb_riscv_core.v

# 3. Run simulation
vvp sim.out

# 4. View waveforms (optional)
gtkwave wave.vcd
```

## Verification

The self-checking testbench (`tb/tb_riscv_core.v`) runs a comprehensive
test program that exercises every implemented instruction and verifies
register/memory state at the end.

### Test Coverage

| Category | What is tested |
|----------|---------------|
| R-type ALU | ADD, SUB, AND, OR, XOR, SLT, SLTU, SLL, SRL, SRA |
| I-type ALU | ADDI (positive & negative imm), XORI, ORI, ANDI, SLTI, SLTIU, SLLI, SRLI, SRAI |
| Upper imm | LUI (upper 20-bit load), AUIPC (PC-relative) |
| Load/Store | SW followed by LW; data memory content verified |
| Branches | BEQ, BNE, BLT, BGE, BLTU, BGEU — all taken paths; branch-skip correctness |
| Jumps | JAL (rd = PC+4, skip verification), JALR (rd = PC+4, bit-0 clearing) |
| Signed vs unsigned | SLT vs SLTU with -1 and 5 (different results); BLT vs BLTU |
| x0 hardwire | ADDI x0,x0,100 must not modify x0 |

### Verified Simulation Output

```
========================================
  RISC-V CORE TEST
========================================
--- R-type ---
  PASS #1 [ADD]: x3 = 0x0000000f
  PASS #2 [SUB]: x4 = 0x00000005
  PASS #3 [AND]: x5 = 0x00000005
  PASS #4 [OR]: x6 = 0x0000000f
  PASS #5 [XOR]: x7 = 0x0000000a
  PASS #6 [SLT]: x8 = 0x00000001
  PASS #7 [SLTU]: x9 = 0x00000000
  PASS #8 [SLL]: x11 = 0x00000020
  PASS #9 [SRL]: x13 = 0x07ffffff
  PASS #10 [SRA]: x14 = 0xffffffff
--- I-type ALU ---
  PASS #11 [ADDI]: x1 = 0x00000005
  PASS #12 [ADDI]: x2 = 0x0000000a
  PASS #13 [ADDI]: x10 = 0x00000001
  PASS #14 [ADDI]: x12 = 0xffffffff
  PASS #15 [XORI]: x15 = 0x000000f0
  PASS #16 [ORI]: x16 = 0x0000001f
  PASS #17 [ANDI]: x17 = 0x00000007
  PASS #18 [SLTI]: x18 = 0x00000001
  PASS #19 [SLTIU]: x19 = 0x00000001
  PASS #20 [SLLI]: x20 = 0x00000008
  PASS #21 [SRLI]: x21 = 0x0fffffff
  PASS #22 [SRAI]: x22 = 0xffffffff
--- Upper Immediate ---
  PASS #23 [LUI]: x23 = 0x12345000
  PASS #24 [AUIPC]: x24 = 0x0000105c
--- Load/Store ---
  PASS #25 [LW]: x25 = 0x0000000f
  PASS #26 [SW]: dmem[0] = 0x0000000f
--- x0 immutability ---
  PASS #27 [x0_imm]: x0 = 0x00000000
--- Branches ---
  PASS #28 [BEQ/BNE/BLT/BGE/BLTU/BGEU]: x26 = 0x00000001
--- JAL ---
  PASS #29 [JAL_rd]: x27 = 0x000000a4
  PASS #30 [JAL_skip]: x28 = 0x0000002a
--- JALR ---
  PASS #31 [JALR_tgt]: x29 = 0x000000b9
  PASS #32 [JALR_rd]: x30 = 0x000000b4
  PASS #33 [JALR_bit0]: x31 = 0x00000001
========================================
  ALL 33 TESTS PASSED
========================================
```

> **Note:** Icarus Verilog prints a harmless warning at load time:
> `$readmemh(program.hex): Not enough words in the file for the requested range [0:255]`
> — this is expected because the 256-word memory is larger than the test program.

## Limitations

- **Simulation only** — no FPGA synthesis constraints or timing closure
- **Word-aligned memory only** — no sub-word loads (`LB`/`LH`/`LBU`/`LHU`)
  or stores (`SB`/`SH`); no misaligned access support
- **No byte-level memory operations** — `LW`/`SW` only
- **No CSR instructions** — `CSRRW`/`CSRRS`/`CSRRC`/`CSRRWI`/`CSRRSI`/`CSRRCI`
  not implemented
- **No `ECALL`/`EBREAK`/`FENCE`** — system and synchronization instructions
  not implemented
- **No M/A/F/D extensions** — multiply, atomic, floating-point not supported
- **1 KB instruction and data memory** — sufficient for testing, easily
  resizable in `imem.v`/`dmem.v`

The following **8 RV32I base instructions** are not implemented:
`LB`, `LH`, `LBU`, `LHU`, `SB`, `SH`, `FENCE`, `ECALL`/`EBREAK`.

## Future Work

- **Pipelined architecture** — 5-stage IF/ID/EX/MEM/WB pipeline; the modular
  boundaries map directly onto pipeline stages
- **Forwarding and hazard detection** — data forwarding unit and pipeline
  stall logic
- **Byte/half-word memory access** — `LB`/`LH`/`LBU`/`LHU`/`SB`/`SH`
  support for full RV32I compliance
- **CSR support and interrupts** — machine-mode CSRs and trap handling
- **M-extension** — hardware multiply/divide unit
- **Larger memory model** — parameterized memory depth
- **FPGA implementation** — synthesis targeting Xilinx/Intel FPGAs with
  timing analysis
- **Formal verification** — property checking with SymbiYosys

## Skills Demonstrated

- Verilog HDL / RTL Design
- Computer Architecture (single-cycle datapath)
- RISC-V ISA (RV32I base integer)
- Digital Logic Design
- Control Unit / FSM Design
- Hardware Verification & Self-Checking Testbenches
- Python Scripting (assembler tooling)
- Simulation (Icarus Verilog, GTKWave)
- Build Automation (Make)

## Author

**Ayush Yadav**

