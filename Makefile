RTL   = rtl/pc.v rtl/imem.v rtl/regfile.v rtl/imm_gen.v rtl/control_unit.v \
        rtl/alu_control.v rtl/alu.v rtl/branch_comp.v rtl/dmem.v rtl/riscv_core.v
TB    = tb/tb_riscv_core.v
SIMDIR = sim

.PHONY: all asm compile run wave clean

all: run

# Assemble the test program into sim/program.hex
# Tries python3 first, then python (works on both Linux/macOS and Windows).
asm:
	@cd $(SIMDIR) && ( \
		python3 ../tb/asm.py program.hex 2>/dev/null || \
		python  ../tb/asm.py program.hex 2>/dev/null || \
		echo "[INFO] Python not found; using existing program.hex" \
	)

# Compile RTL + testbench with Icarus Verilog
compile: asm
	cd $(SIMDIR) && iverilog -g2012 -s tb_riscv_core -o sim.out \
		$(addprefix ../,$(RTL)) $(addprefix ../,$(TB))

# Run the simulation
run: compile
	cd $(SIMDIR) && vvp sim.out

# Open waveform in GTKWave
wave:
	cd $(SIMDIR) && gtkwave wave.vcd

# Remove generated files
clean:
	rm -f $(SIMDIR)/sim.out $(SIMDIR)/wave.vcd $(SIMDIR)/program.hex
