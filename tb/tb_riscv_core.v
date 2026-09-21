// ============================================================
// tb_riscv_core.v -- Self-checking testbench
// Instantiates the core, runs the assembled test program, and
// checks the final register file contents against expected
// values. Prints PASS/FAIL per check plus a waveform dump.
//
// Tests all 31 implemented RV32I instructions:
//   R-type : ADD SUB SLL SRL SRA SLT SLTU AND OR XOR
//   I-type : ADDI SLTI SLTIU XORI ORI ANDI SLLI SRLI SRAI
//   Load   : LW
//   Store  : SW
//   Branch : BEQ BNE BLT BGE BLTU BGEU
//   Jump   : JAL JALR
//   Upper  : LUI AUIPC
// ============================================================
`timescale 1ns/1ps

module tb_riscv_core;
    reg clk;
    reg rst;

    riscv_core dut (
        .clk(clk),
        .rst(rst)
    );

    // 10 ns clock period
    initial clk = 0;
    always #5 clk = ~clk;

    integer errors;
    integer test_num;

    // --------------------------------------------------------
    // check -- compare a register against an expected value
    // --------------------------------------------------------
    task check(input [255:0] name, input [4:0] regnum, input [31:0] expected);
        reg [31:0] actual;
        begin
            actual = dut.u_regfile.regs[regnum];
            test_num = test_num + 1;
            if (actual !== expected) begin
                $display("  FAIL #%0d [%0s]: x%0d = 0x%08h, expected 0x%08h",
                          test_num, name, regnum, actual, expected);
                errors = errors + 1;
            end else begin
                $display("  PASS #%0d [%0s]: x%0d = 0x%08h",
                          test_num, name, regnum, actual);
            end
        end
    endtask

    // --------------------------------------------------------
    // check_mem -- compare a data-memory word against expected
    // --------------------------------------------------------
    task check_mem(input [255:0] name, input [31:0] word_addr, input [31:0] expected);
        reg [31:0] actual;
        begin
            actual = dut.u_dmem.mem[word_addr];
            test_num = test_num + 1;
            if (actual !== expected) begin
                $display("  FAIL #%0d [%0s]: dmem[%0d] = 0x%08h, expected 0x%08h",
                          test_num, name, word_addr, actual, expected);
                errors = errors + 1;
            end else begin
                $display("  PASS #%0d [%0s]: dmem[%0d] = 0x%08h",
                          test_num, name, word_addr, actual);
            end
        end
    endtask

    initial begin
        $dumpfile("wave.vcd");
        $dumpvars(0, tb_riscv_core);

        errors   = 0;
        test_num = 0;
        rst = 1;
        repeat (2) @(posedge clk);
        rst = 0;

        // 50 instructions in the test program; run well past that.
        repeat (60) @(posedge clk);

        $display("");
        $display("========================================");
        $display("  RISC-V CORE TEST");
        $display("========================================");

        // ---- R-type ----
        $display("--- R-type ---");
        check("ADD",   3,  32'd15);                  // x3  = x1+x2 = 15
        check("SUB",   4,  32'd5);                   // x4  = x2-x1 = 5
        check("AND",   5,  32'd5);                   // x5  = 15 & 5 = 5
        check("OR",    6,  32'd15);                  // x6  = 15 | 5 = 15
        check("XOR",   7,  32'd10);                  // x7  = 15 ^ 5 = 10
        check("SLT",   8,  32'd1);                   // x8  = (-1 <s 5)  = 1
        check("SLTU",  9,  32'd0);                   // x9  = (FFFFFFFF <u 5) = 0
        check("SLL",  11,  32'd32);                  // x11 = 1 << 5 = 32
        check("SRL",  13,  32'h07FFFFFF);             // x13 = FFFFFFFF >> 5
        check("SRA",  14,  32'hFFFFFFFF);             // x14 = FFFFFFFF >>> 5

        // ---- I-type ALU ----
        $display("--- I-type ALU ---");
        check("ADDI",  1,  32'd5);                   // x1  = 5
        check("ADDI",  2,  32'd10);                  // x2  = 10
        check("ADDI", 10,  32'd1);                   // x10 = 1
        check("ADDI", 12,  32'hFFFFFFFF);             // x12 = -1 (negative imm)
        check("XORI", 15,  32'd240);                 // x15 = 15 ^ 0xFF = 240
        check("ORI",  16,  32'd31);                  // x16 = 0 | 0x1F = 31
        check("ANDI", 17,  32'd7);                   // x17 = 15 & 7 = 7
        check("SLTI", 18,  32'd1);                   // x18 = (-1 <s 5) = 1
        check("SLTIU",19,  32'd1);                   // x19 = (5 <u 10) = 1
        check("SLLI", 20,  32'd8);                   // x20 = 1 << 3 = 8
        check("SRLI", 21,  32'h0FFFFFFF);             // x21 = FFFFFFFF >> 4
        check("SRAI", 22,  32'hFFFFFFFF);             // x22 = FFFFFFFF >>> 4

        // ---- Upper Immediate ----
        $display("--- Upper Immediate ---");
        check("LUI",  23,  32'h12345000);             // x23 = 0x12345 << 12
        check("AUIPC",24,  32'h0000105C);             // x24 = 0x5C + 0x1000

        // ---- Memory ----
        $display("--- Load/Store ---");
        check("LW",   25,  32'd15);                  // x25 = mem[0] = 15
        check_mem("SW", 0,  32'd15);                  // mem[0] = x3 = 15

        // ---- x0 immutability ----
        $display("--- x0 immutability ---");
        check("x0_imm", 0,  32'd0);                  // x0 must remain 0

        // ---- Branches ----
        // All taken branches skip an ADDI that would set x26=0.
        // x26 is set to 1 at T_BEQ and must survive all subsequent branches.
        $display("--- Branches ---");
        check("BEQ/BNE/BLT/BGE/BLTU/BGEU", 26, 32'd1); // branch marker

        // ---- JAL ----
        $display("--- JAL ---");
        check("JAL_rd",  27, 32'h000000A4);           // x27 = PC+4 of JAL = 0xA4
        check("JAL_skip",28, 32'd42);                 // x28 = 42 (skip instr was skipped)

        // ---- JALR ----
        $display("--- JALR ---");
        check("JALR_tgt",29, 32'd185);                // x29 = 0xB9 (odd target setup)
        check("JALR_rd", 30, 32'h000000B4);           // x30 = PC+4 of JALR = 0xB4
        check("JALR_bit0",31, 32'd1);                 // x31 = 1 (bit-0 clearing worked)

        $display("========================================");
        if (errors == 0)
            $display("  ALL %0d TESTS PASSED", test_num);
        else
            $display("  %0d of %0d TEST(S) FAILED", errors, test_num);
        $display("========================================");

        $finish;
    end
endmodule
