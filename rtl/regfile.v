// ============================================================
// regfile.v -- 32 x 32-bit Register File
// Two combinational read ports, one clocked write port.
// x0 is hard-wired to zero (reads return 0, writes are ignored).
// ============================================================
module regfile (
    input  wire        clk,
    input  wire        rst,
    input  wire        we,        // write enable
    input  wire [4:0]  rs1,
    input  wire [4:0]  rs2,
    input  wire [4:0]  rd,
    input  wire [31:0] wd,        // write data
    output wire [31:0] rd1,
    output wire [31:0] rd2
);
    reg [31:0] regs [0:31];
    integer i;

    assign rd1 = (rs1 == 5'd0) ? 32'b0 : regs[rs1];
    assign rd2 = (rs2 == 5'd0) ? 32'b0 : regs[rs2];

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            for (i = 0; i < 32; i = i + 1)
                regs[i] <= 32'b0;
        end else if (we && rd != 5'd0) begin
            regs[rd] <= wd;
        end
    end
endmodule
