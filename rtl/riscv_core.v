// ============================================================
// riscv_core.v -- Top-level Single-Cycle RV32I Core
// Wires together PC, instruction memory, register file,
// immediate generator, control unit, ALU, branch comparator
// and data memory into a complete single-cycle datapath.
// ============================================================
module riscv_core (
    input wire clk,
    input wire rst
);
    // ---- fetch ----
    wire [31:0] pc_out, pc_next, pc_plus4, pc_target, jalr_target;
    wire [31:0] instr;

    // ---- decode fields ----
    wire [6:0] opcode = instr[6:0];
    wire [2:0] funct3 = instr[14:12];
    wire       funct7_5 = instr[30];
    wire [4:0] rs1  = instr[19:15];
    wire [4:0] rs2  = instr[24:20];
    wire [4:0] rd   = instr[11:7];

    // ---- control signals ----
    wire reg_write, mem_read, mem_write, mem_to_reg, alu_src;
    wire branch, jump, jalr, lui, auipc;
    wire [1:0] alu_op;
    wire [3:0] alu_ctrl;

    // ---- datapath signals ----
    wire [31:0] rd1, rd2, imm_out;
    wire [31:0] alu_operand_b, alu_result, mem_read_data, write_back_data;
    wire        alu_zero, branch_taken;

    // ================= Fetch =================
    assign pc_plus4   = pc_out + 32'd4;
    assign pc_target  = pc_out + imm_out;                 // branch / jal target
    assign jalr_target = (rd1 + imm_out) & ~32'h1;         // jalr target, LSB cleared

    assign pc_next = jalr                       ? jalr_target :
                      (jump || (branch && branch_taken)) ? pc_target :
                                                   pc_plus4;

    pc u_pc (
        .clk(clk), .rst(rst),
        .pc_next(pc_next),
        .pc_out(pc_out)
    );

    imem u_imem (
        .addr(pc_out),
        .instr(instr)
    );

    // ================= Decode =================
    regfile u_regfile (
        .clk(clk), .rst(rst),
        .we(reg_write),
        .rs1(rs1), .rs2(rs2), .rd(rd),
        .wd(write_back_data),
        .rd1(rd1), .rd2(rd2)
    );

    imm_gen u_imm_gen (
        .instr(instr),
        .imm_out(imm_out)
    );

    control_unit u_control (
        .opcode(opcode),
        .reg_write(reg_write),
        .mem_read(mem_read),
        .mem_write(mem_write),
        .mem_to_reg(mem_to_reg),
        .alu_src(alu_src),
        .branch(branch),
        .jump(jump),
        .jalr(jalr),
        .lui(lui),
        .auipc(auipc),
        .alu_op(alu_op)
    );

    alu_control u_alu_control (
        .alu_op(alu_op),
        .funct3(funct3),
        .funct7_5(funct7_5),
        .alu_ctrl(alu_ctrl)
    );

    branch_comp u_branch_comp (
        .rs1_data(rd1),
        .rs2_data(rd2),
        .funct3(funct3),
        .branch_taken(branch_taken)
    );

    // ================= Execute =================
    assign alu_operand_b = alu_src ? imm_out : rd2;

    alu u_alu (
        .a(rd1),
        .b(alu_operand_b),
        .alu_ctrl(alu_ctrl),
        .result(alu_result),
        .zero(alu_zero)
    );

    // ================= Memory =================
    dmem u_dmem (
        .clk(clk),
        .mem_write(mem_write),
        .mem_read(mem_read),
        .addr(alu_result),
        .write_data(rd2),
        .read_data(mem_read_data)
    );

    // ================= Write-back =================
    assign write_back_data = jump       ? pc_plus4 :
                               lui       ? imm_out :
                               auipc     ? (pc_out + imm_out) :
                               mem_to_reg ? mem_read_data :
                                            alu_result;

endmodule
