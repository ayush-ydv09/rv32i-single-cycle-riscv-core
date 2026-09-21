// ============================================================
// imem.v -- Instruction Memory (ROM)
// 256 words x 32 bits = 1 KB. Loaded at simulation start from
// a hex file via $readmemh. Word-addressed (byte addr >> 2).
// ============================================================
module imem (
    input  wire [31:0] addr,
    output wire [31:0] instr
);
    reg [31:0] mem [0:255];

    initial begin
        $readmemh("program.hex", mem);
    end

    assign instr = mem[addr[31:2]];
endmodule
