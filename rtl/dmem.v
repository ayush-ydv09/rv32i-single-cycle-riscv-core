// ============================================================
// dmem.v -- Data Memory
// 256 words x 32 bits = 1 KB. Combinational read, clocked write.
// Word-addressed (byte addr >> 2) -- no misaligned access support.
// ============================================================
module dmem (
    input  wire        clk,
    input  wire        mem_write,
    input  wire        mem_read,
    input  wire [31:0] addr,
    input  wire [31:0] write_data,
    output wire [31:0] read_data
);
    reg [31:0] mem [0:255];
    integer i;

    initial begin
        for (i = 0; i < 256; i = i + 1)
            mem[i] = 32'b0;
    end

    assign read_data = mem[addr[31:2]];

    always @(posedge clk) begin
        if (mem_write)
            mem[addr[31:2]] <= write_data;
    end
endmodule
