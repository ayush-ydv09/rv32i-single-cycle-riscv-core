// ============================================================
// imm_gen.v -- Immediate Generator
// Extracts and sign-extends the immediate field from the
// instruction, depending on the instruction format (I/S/B/U/J).
// ============================================================
module imm_gen (
    input  wire [31:0] instr,
    output reg  [31:0] imm_out
);
    wire [6:0] opcode = instr[6:0];

    always @(*) begin
        case (opcode)
            // I-type: loads, ALU-immediate, jalr
            7'b0000011,
            7'b0010011,
            7'b1100111:
                imm_out = {{20{instr[31]}}, instr[31:20]};

            // S-type: store
            7'b0100011:
                imm_out = {{20{instr[31]}}, instr[31:25], instr[11:7]};

            // B-type: branch (note bit0 is always 0, offset is x2)
            7'b1100011:
                imm_out = {{19{instr[31]}}, instr[31], instr[7],
                           instr[30:25], instr[11:8], 1'b0};

            // U-type: lui, auipc (imm already in upper 20 bits)
            7'b0110111,
            7'b0010111:
                imm_out = {instr[31:12], 12'b0};

            // J-type: jal
            7'b1101111:
                imm_out = {{11{instr[31]}}, instr[31], instr[19:12],
                           instr[20], instr[30:21], 1'b0};

            default:
                imm_out = 32'b0;
        endcase
    end
endmodule
