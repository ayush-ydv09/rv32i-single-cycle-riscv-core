#!/usr/bin/env python3
"""
Minimal RV32I assembler for the single-cycle core testbench.
Two-pass: first pass records label -> byte address, second pass
encodes instructions, resolving branch/jump immediates from
labels automatically.

Supports all 31 instructions implemented in RTL:
  R-type : ADD SUB SLL SRL SRA SLT SLTU AND OR XOR
  I-type : ADDI SLTI SLTIU XORI ORI ANDI SLLI SRLI SRAI
  Load   : LW
  Store  : SW
  Branch : BEQ BNE BLT BGE BLTU BGEU
  Jump   : JAL JALR
  Upper  : LUI AUIPC
"""

import sys
import re

REG = {f"x{i}": i for i in range(32)}
# Add standard ABI names for convenience
ABI_MAP = {
    "zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4,
    "t0": 5, "t1": 6, "t2": 7, "s0": 8, "fp": 8, "s1": 9,
    "a0": 10, "a1": 11, "a2": 12, "a3": 13, "a4": 14, "a5": 15,
    "a6": 16, "a7": 17, "s2": 18, "s3": 19, "s4": 20, "s5": 21,
    "s6": 22, "s7": 23, "s8": 24, "s9": 25, "s10": 26, "s11": 27,
    "t3": 28, "t4": 29, "t5": 30, "t6": 31,
}
for name, idx in ABI_MAP.items():
    REG[name] = idx


def r(u):
    return u & 0xFFFFFFFF


def rtype(funct7, rs2, rs1, funct3, rd, opcode):
    return r((funct7 << 25) | (rs2 << 20) | (rs1 << 15) |
             (funct3 << 12) | (rd << 7) | opcode)


def itype(imm, rs1, funct3, rd, opcode):
    imm &= 0xFFF
    return r((imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode)


def stype(imm, rs2, rs1, funct3, opcode):
    imm &= 0xFFF
    imm11_5 = (imm >> 5) & 0x7F
    imm4_0 = imm & 0x1F
    return r((imm11_5 << 25) | (rs2 << 20) | (rs1 << 15) |
             (funct3 << 12) | (imm4_0 << 7) | opcode)


def btype(imm, rs2, rs1, funct3, opcode):
    imm &= 0x1FFF
    b12 = (imm >> 12) & 0x1
    b10_5 = (imm >> 5) & 0x3F
    b4_1 = (imm >> 1) & 0xF
    b11 = (imm >> 11) & 0x1
    return r((b12 << 31) | (b10_5 << 25) | (rs2 << 20) | (rs1 << 15) |
             (funct3 << 12) | (b4_1 << 8) | (b11 << 7) | opcode)


def utype(imm20, rd, opcode):
    return r((imm20 << 12) | (rd << 7) | opcode)


def jtype(imm, rd, opcode):
    imm &= 0x1FFFFF
    b20 = (imm >> 20) & 0x1
    b10_1 = (imm >> 1) & 0x3FF
    b11 = (imm >> 11) & 0x1
    b19_12 = (imm >> 12) & 0xFF
    return r((b20 << 31) | (b19_12 << 12) | (b11 << 20) |
             (b10_1 << 21) | (rd << 7) | opcode)


# Built-in verification test program
DEFAULT_PROGRAM = [
    # ---- Setup ----
    ("ADDI",  "x1",  "x0", 5),          # x1  = 5
    ("ADDI",  "x2",  "x0", 10),         # x2  = 10
    ("ADDI",  "x10", "x0", 1),          # x10 = 1
    ("ADDI",  "x12", "x0", -1),         # x12 = 0xFFFFFFFF

    # ---- R-type ALU ----
    ("ADD",   "x3",  "x1", "x2"),       # x3  = 15
    ("SUB",   "x4",  "x2", "x1"),       # x4  = 5
    ("AND",   "x5",  "x3", "x4"),       # x5  = 15 & 5  = 5
    ("OR",    "x6",  "x3", "x4"),       # x6  = 15 | 5  = 15
    ("XOR",   "x7",  "x3", "x4"),       # x7  = 15 ^ 5  = 10
    ("SLT",   "x8",  "x12","x1"),       # x8  = (-1 < 5 signed)  = 1
    ("SLTU",  "x9",  "x12","x1"),       # x9  = (0xFFFFFFFF <u 5) = 0
    ("SLL",   "x11", "x10","x1"),       # x11 = 1 << 5  = 32
    ("SRL",   "x13", "x12","x1"),       # x13 = 0xFFFFFFFF >> 5  = 0x07FFFFFF
    ("SRA",   "x14", "x12","x1"),       # x14 = 0xFFFFFFFF >>> 5 = 0xFFFFFFFF

    # ---- I-type ALU ----
    ("XORI",  "x15", "x3", 0xFF),       # x15 = 15 ^ 255 = 240
    ("ORI",   "x16", "x0", 0x1F),       # x16 = 31
    ("ANDI",  "x17", "x3", 7),          # x17 = 15 & 7  = 7
    ("SLTI",  "x18", "x12", 5),         # x18 = (-1 < 5 signed)  = 1
    ("SLTIU", "x19", "x1", 10),         # x19 = (5 <u 10) = 1
    ("SLLI",  "x20", "x10", 3),         # x20 = 1 << 3  = 8
    ("SRLI",  "x21", "x12", 4),         # x21 = 0xFFFFFFFF >> 4  = 0x0FFFFFFF
    ("SRAI",  "x22", "x12", 4),         # x22 = 0xFFFFFFFF >>> 4 = 0xFFFFFFFF

    # ---- Upper Immediate ----
    ("LUI",   "x23", 0x12345),          # x23 = 0x12345000
    ("AUIPC", "x24", 1),               # x24 = PC + 0x1000 = 0x5C + 0x1000 = 0x105C

    # ---- Memory ----
    ("SW",    "x3",  0, "x0"),          # mem[0] = 15
    ("LW",    "x25", 0, "x0"),          # x25 = 15

    # ---- x0 immutability test ----
    ("ADDI",  "x0",  "x0", 100),        # must not modify x0

    # ---- Branch: BEQ taken ----
    ("BEQ",   "x3",  "x25", "T_BEQ"),  # 15 == 15 -> taken
    ("ADDI",  "x26", "x0",  0),        # skipped
    "T_BEQ:",
    ("ADDI",  "x26", "x0",  1),        # x26 = 1 (branch marker)

    # ---- Branch: BNE taken ----
    ("BNE",   "x1",  "x2",  "T_BNE"),  # 5 != 10 -> taken
    ("ADDI",  "x26", "x0",  0),        # skipped
    "T_BNE:",

    # ---- Branch: BLT taken (signed) ----
    ("BLT",   "x12", "x1",  "T_BLT"),  # -1 < 5 (signed) -> taken
    ("ADDI",  "x26", "x0",  0),        # skipped
    "T_BLT:",

    # ---- Branch: BGE taken (signed) ----
    ("BGE",   "x1",  "x1",  "T_BGE"),  # 5 >= 5 (signed) -> taken
    ("ADDI",  "x26", "x0",  0),        # skipped
    "T_BGE:",

    # ---- Branch: BLTU taken (unsigned) ----
    ("BLTU",  "x1",  "x12", "T_BLTU"), # 5 <u 0xFFFFFFFF -> taken
    ("ADDI",  "x26", "x0",  0),        # skipped
    "T_BLTU:",

    # ---- Branch: BGEU taken (unsigned) ----
    ("BGEU",  "x12", "x1",  "T_BGEU"), # 0xFFFFFFFF >=u 5 -> taken
    ("ADDI",  "x26", "x0",  0),        # skipped
    "T_BGEU:",

    # ---- JAL ----
    ("JAL",   "x27", "T_JAL"),          # x27 = PC+4 = 0xA4
    ("ADDI",  "x28", "x0",  0),        # skipped
    "T_JAL:",
    ("ADDI",  "x28", "x0",  42),       # x28 = 42

    # ---- JALR (with bit-0 clearing test) ----
    # x29 = 0xB9 (odd), JALR target = (0xB9 + 0) & ~1 = 0xB8
    ("ADDI",  "x29", "x0",  185),      # x29 = 0xB9
    ("JALR",  "x30", "x29", 0),        # x30 = PC+4 = 0xB4, jump to 0xB8
    ("ADDI",  "x28", "x0",  0),        # skipped
    "T_JALR:",
    ("ADDI",  "x31", "x0",  1),        # x31 = 1 (final marker)

    # ---- NOP padding ----
    ("ADDI",  "x0",  "x0",  0),
    ("ADDI",  "x0",  "x0",  0),
    ("ADDI",  "x0",  "x0",  0),
]


def parse_asm_text(text):
    """Parses text assembly into program items (labels and tuples)."""
    items = []
    lines = text.splitlines()
    for line_num, line in enumerate(lines, 1):
        # Strip comments
        line = re.sub(r'(#|//|;).*$', '', line).strip()
        if not line:
            continue

        # Check for label definition
        while ":" in line:
            parts = line.split(":", 1)
            lbl = parts[0].strip()
            if not lbl:
                break
            items.append(f"{lbl}:")
            line = parts[1].strip()
            if not line:
                break

        if not line:
            continue

        # Parse instruction mnemonic and operands
        tokens = re.split(r'[\s,]+', line.strip())
        mnemonic = tokens[0].upper()
        args = tokens[1:]

        # Handle offset(reg) syntax for loads, stores, jalr
        processed_args = []
        for arg in args:
            match = re.match(r'^([+-]?(?:0x[0-9a-fA-F]+|\d+))\(([^)]+)\)$', arg)
            if match:
                offset_val = int(match.group(1), 0)
                reg_val = match.group(2).strip()
                processed_args.extend([offset_val, reg_val])
            else:
                try:
                    processed_args.append(int(arg, 0))
                except ValueError:
                    processed_args.append(arg)

        # Normalize ordering for LW: mnemonic, rd, imm, rs1
        if mnemonic == "LW" and len(processed_args) == 3:
            if isinstance(processed_args[1], int) and isinstance(processed_args[2], str):
                items.append((mnemonic, processed_args[0], processed_args[1], processed_args[2]))
            else:
                items.append((mnemonic, *processed_args))
        # Normalize ordering for SW: mnemonic, rs2, imm, rs1
        elif mnemonic == "SW" and len(processed_args) == 3:
            if isinstance(processed_args[1], int) and isinstance(processed_args[2], str):
                items.append((mnemonic, processed_args[0], processed_args[1], processed_args[2]))
            else:
                items.append((mnemonic, *processed_args))
        # Normalize ordering for JALR: mnemonic, rd, rs1, imm
        elif mnemonic == "JALR" and len(processed_args) == 3:
            if isinstance(processed_args[1], int) and isinstance(processed_args[2], str):
                items.append((mnemonic, processed_args[0], processed_args[2], processed_args[1]))
            else:
                items.append((mnemonic, *processed_args))
        else:
            items.append((mnemonic, *processed_args))

    return items


def assemble(program_items):
    # Pass 1: collect label addresses
    labels = {}
    addr = 0
    for item in program_items:
        if isinstance(item, str) and item.endswith(":"):
            labels[item[:-1]] = addr
        else:
            addr += 4

    def resolve(operand, cur_addr):
        if isinstance(operand, str) and operand in labels:
            return labels[operand] - cur_addr
        if isinstance(operand, str):
            try:
                return int(operand, 0)
            except ValueError:
                raise ValueError(f"Unknown label or invalid integer: '{operand}'")
        return int(operand)

    # Pass 2: encode instructions
    words = []
    addr = 0
    for item in program_items:
        if isinstance(item, str) and item.endswith(":"):
            continue

        op = item[0].upper()
        args = item[1:]

        # --- R-type ---
        if op == "ADD":
            rd, rs1, rs2 = args
            words.append(rtype(0b0000000, REG[rs2], REG[rs1], 0b000, REG[rd], 0b0110011))
        elif op == "SUB":
            rd, rs1, rs2 = args
            words.append(rtype(0b0100000, REG[rs2], REG[rs1], 0b000, REG[rd], 0b0110011))
        elif op == "SLL":
            rd, rs1, rs2 = args
            words.append(rtype(0b0000000, REG[rs2], REG[rs1], 0b001, REG[rd], 0b0110011))
        elif op == "SLT":
            rd, rs1, rs2 = args
            words.append(rtype(0b0000000, REG[rs2], REG[rs1], 0b010, REG[rd], 0b0110011))
        elif op == "SLTU":
            rd, rs1, rs2 = args
            words.append(rtype(0b0000000, REG[rs2], REG[rs1], 0b011, REG[rd], 0b0110011))
        elif op == "XOR":
            rd, rs1, rs2 = args
            words.append(rtype(0b0000000, REG[rs2], REG[rs1], 0b100, REG[rd], 0b0110011))
        elif op == "SRL":
            rd, rs1, rs2 = args
            words.append(rtype(0b0000000, REG[rs2], REG[rs1], 0b101, REG[rd], 0b0110011))
        elif op == "SRA":
            rd, rs1, rs2 = args
            words.append(rtype(0b0100000, REG[rs2], REG[rs1], 0b101, REG[rd], 0b0110011))
        elif op == "OR":
            rd, rs1, rs2 = args
            words.append(rtype(0b0000000, REG[rs2], REG[rs1], 0b110, REG[rd], 0b0110011))
        elif op == "AND":
            rd, rs1, rs2 = args
            words.append(rtype(0b0000000, REG[rs2], REG[rs1], 0b111, REG[rd], 0b0110011))

        # --- I-type ALU ---
        elif op == "ADDI":
            rd, rs1, imm = args
            words.append(itype(resolve(imm, addr), REG[rs1], 0b000, REG[rd], 0b0010011))
        elif op == "SLTI":
            rd, rs1, imm = args
            words.append(itype(resolve(imm, addr), REG[rs1], 0b010, REG[rd], 0b0010011))
        elif op == "SLTIU":
            rd, rs1, imm = args
            words.append(itype(resolve(imm, addr), REG[rs1], 0b011, REG[rd], 0b0010011))
        elif op == "XORI":
            rd, rs1, imm = args
            words.append(itype(resolve(imm, addr), REG[rs1], 0b100, REG[rd], 0b0010011))
        elif op == "ORI":
            rd, rs1, imm = args
            words.append(itype(resolve(imm, addr), REG[rs1], 0b110, REG[rd], 0b0010011))
        elif op == "ANDI":
            rd, rs1, imm = args
            words.append(itype(resolve(imm, addr), REG[rs1], 0b111, REG[rd], 0b0010011))
        elif op == "SLLI":
            rd, rs1, shamt = args
            words.append(itype(int(shamt) & 0x1F, REG[rs1], 0b001, REG[rd], 0b0010011))
        elif op == "SRLI":
            rd, rs1, shamt = args
            words.append(itype(int(shamt) & 0x1F, REG[rs1], 0b101, REG[rd], 0b0010011))
        elif op == "SRAI":
            rd, rs1, shamt = args
            words.append(itype(0x400 | (int(shamt) & 0x1F), REG[rs1], 0b101, REG[rd], 0b0010011))

        # --- Load ---
        elif op == "LW":
            rd, imm, rs1 = args
            words.append(itype(resolve(imm, addr), REG[rs1], 0b010, REG[rd], 0b0000011))

        # --- Store ---
        elif op == "SW":
            rs2, imm, rs1 = args
            words.append(stype(resolve(imm, addr), REG[rs2], REG[rs1], 0b010, 0b0100011))

        # --- Branch ---
        elif op == "BEQ":
            rs1, rs2, tgt = args
            words.append(btype(resolve(tgt, addr), REG[rs2], REG[rs1], 0b000, 0b1100011))
        elif op == "BNE":
            rs1, rs2, tgt = args
            words.append(btype(resolve(tgt, addr), REG[rs2], REG[rs1], 0b001, 0b1100011))
        elif op == "BLT":
            rs1, rs2, tgt = args
            words.append(btype(resolve(tgt, addr), REG[rs2], REG[rs1], 0b100, 0b1100011))
        elif op == "BGE":
            rs1, rs2, tgt = args
            words.append(btype(resolve(tgt, addr), REG[rs2], REG[rs1], 0b101, 0b1100011))
        elif op == "BLTU":
            rs1, rs2, tgt = args
            words.append(btype(resolve(tgt, addr), REG[rs2], REG[rs1], 0b110, 0b1100011))
        elif op == "BGEU":
            rs1, rs2, tgt = args
            words.append(btype(resolve(tgt, addr), REG[rs2], REG[rs1], 0b111, 0b1100011))

        # --- Jump ---
        elif op == "JAL":
            rd, tgt = args
            words.append(jtype(resolve(tgt, addr), REG[rd], 0b1101111))
        elif op == "JALR":
            rd, rs1, imm = args
            words.append(itype(resolve(imm, addr), REG[rs1], 0b000, REG[rd], 0b1100111))

        # --- Upper Immediate ---
        elif op == "LUI":
            rd, imm20 = args
            words.append(utype(resolve(imm20, addr), REG[rd], 0b0110111))
        elif op == "AUIPC":
            rd, imm20 = args
            words.append(utype(resolve(imm20, addr), REG[rd], 0b0010111))

        else:
            raise ValueError(f"unsupported mnemonic '{op}' at address 0x{addr:08x}")

        addr += 4

    return words, labels


def print_help():
    help_text = """RISC-V (RV32I) Assembler for Single-Cycle Core
Usage:
  python asm.py                             Assemble embedded test program -> program.hex
  python asm.py [options] <output.hex>      Assemble embedded test program -> <output.hex>
  python asm.py -i <input.s> [-o <out.hex>] Assemble source assembly file -> output hex
  python asm.py <input.s> <output.hex>      Assemble source assembly file -> output hex
  python asm.py -h, --help                  Show this help message

Options:
  -i, --input  <file>    Input assembly text file
  -o, --output <file>    Output hex file (default: program.hex)
  -h, --help             Show this help message and exit

Supported Instructions (31 total):
  R-type:   ADD, SUB, SLL, SRL, SRA, SLT, SLTU, AND, OR, XOR
  I-type:   ADDI, SLTI, SLTIU, XORI, ORI, ANDI, SLLI, SRLI, SRAI
  Load:     LW
  Store:    SW
  Branch:   BEQ, BNE, BLT, BGE, BLTU, BGEU
  Jump:     JAL, JALR
  Upper:    LUI, AUIPC
"""
    print(help_text)


def main():
    args = sys.argv[1:]

    if "-h" in args or "--help" in args:
        print_help()
        sys.exit(0)

    input_file = None
    output_file = "program.hex"

    # Parse command line options
    i = 0
    pos_args = []
    while i < len(args):
        if args[i] in ("-i", "--input") and i + 1 < len(args):
            input_file = args[i + 1]
            i += 2
        elif args[i] in ("-o", "--output") and i + 1 < len(args):
            output_file = args[i + 1]
            i += 2
        else:
            pos_args.append(args[i])
            i += 1

    if not input_file:
        if len(pos_args) == 1:
            # If extension looks like assembly file, treat as input
            if pos_args[0].endswith(('.s', '.asm', '.txt')):
                input_file = pos_args[0]
            else:
                output_file = pos_args[0]
        elif len(pos_args) >= 2:
            input_file = pos_args[0]
            output_file = pos_args[1]

    if input_file:
        with open(input_file, "r") as f:
            content = f.read()
        program_items = parse_asm_text(content)
        print(f"Assembling from input file: {input_file}")
    else:
        program_items = DEFAULT_PROGRAM
        print("Assembling built-in test program")

    words, labels = assemble(program_items)

    with open(output_file, "w") as f:
        for w in words:
            f.write(f"{w:08x}\n")

    print(f"Wrote {len(words)} instructions to {output_file}")
    if labels:
        print(f"Labels: {labels}")


if __name__ == "__main__":
    main()
