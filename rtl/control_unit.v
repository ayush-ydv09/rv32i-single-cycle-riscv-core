// ============================================================
// control_unit.v -- Main Decoder
// Decodes the opcode into the control signals that drive the
// rest of the datapath.
// ============================================================
module control_unit (
    input  wire [6:0] opcode,
    output reg         reg_write,
    output reg         mem_read,
    output reg         mem_write,
    output reg         mem_to_reg,
    output reg         alu_src,
    output reg         branch,
    output reg         jump,
    output reg         jalr,
    output reg         lui,
    output reg         auipc,
    output reg  [1:0]  alu_op
);
    // opcode map (RV32I base)
    localparam OP_RTYPE  = 7'b0110011;
    localparam OP_ITYPE  = 7'b0010011; // addi, andi, ori, ...
    localparam OP_LOAD   = 7'b0000011; // lw
    localparam OP_STORE  = 7'b0100011; // sw
    localparam OP_BRANCH = 7'b1100011; // beq, bne, ...
    localparam OP_JAL    = 7'b1101111;
    localparam OP_JALR   = 7'b1100111;
    localparam OP_LUI    = 7'b0110111;
    localparam OP_AUIPC  = 7'b0010111;

    always @(*) begin
        // safe defaults (NOP for unrecognised opcode)
        reg_write  = 1'b0;
        mem_read   = 1'b0;
        mem_write  = 1'b0;
        mem_to_reg = 1'b0;
        alu_src    = 1'b0;
        branch     = 1'b0;
        jump       = 1'b0;
        jalr       = 1'b0;
        lui        = 1'b0;
        auipc      = 1'b0;
        alu_op     = 2'b00;

        case (opcode)
            OP_RTYPE: begin
                reg_write = 1'b1;
                alu_op    = 2'b10;
            end

            OP_ITYPE: begin
                reg_write = 1'b1;
                alu_src   = 1'b1;
                alu_op    = 2'b11;
            end

            OP_LOAD: begin
                reg_write  = 1'b1;
                alu_src    = 1'b1;
                mem_read   = 1'b1;
                mem_to_reg = 1'b1;
                alu_op     = 2'b00; // ADD for address calc
            end

            OP_STORE: begin
                alu_src   = 1'b1;
                mem_write = 1'b1;
                alu_op    = 2'b00; // ADD for address calc
            end

            OP_BRANCH: begin
                branch = 1'b1;
                // comparison itself is done by a dedicated
                // branch comparator, not the ALU
            end

            OP_JAL: begin
                reg_write = 1'b1;
                jump      = 1'b1;
            end

            OP_JALR: begin
                reg_write = 1'b1;
                jump      = 1'b1;
                jalr      = 1'b1;
                alu_src   = 1'b1;
            end

            OP_LUI: begin
                reg_write = 1'b1;
                lui       = 1'b1;
            end

            OP_AUIPC: begin
                reg_write = 1'b1;
                auipc     = 1'b1;
            end

            default: ; // unsupported opcode -> NOP
        endcase
    end
endmodule
