#!/usr/bin/python

import sys, string

context = [
	0x0000, 0x0000, 0x0000, 0x0000,		# r0 - r3
	0x0000, 0x0000, 0x0000, 0x0000,		# r4 - r7
	0x0000, 0x0000				# pc, stack limit
]

memory = []

def tohex(n):
	return "%s" % ("0000%x" % (n & 0xffff))[-4:]

def check(program) :
	for lin in program :
		flds = string.split(lin)
		if len(flds) != 2 :
			return 1
		for f in flds :
			if f == '****' :
				return 1
	return 0

def load(program) :
	lines = 0
	# load program into memory
	for lin in program :
		flds = string.split(lin)
		data = int(flds[1], 16)
		memory.append(data)
		lines += 1
	print ("[program (code + data): %d bytes]" % (len(memory) * 2))
	
	# set the stack limit to the end of program section
	context[9] = (len(memory) * 2) + 2
	# fill the rest of memory with zeroes
	for i in range(lines, 28672) :
		memory.append(0)
	# set the stack pointer to the last memory position
	context[7] = len(memory) * 2 - 2
	print ("[memory size: %d]" % (len(memory) * 2))

def cycle() :
	pc = context[8]
	# fetch an instruction from memory
	instruction = memory[pc >> 1]
	
	# predecode the instruction (extract opcode fields)
	opc = (instruction & 0xf000) >> 12
	imm = (instruction & 0x0800) >> 11
	rst = (instruction & 0x0700) >> 8
	rs1 = (instruction & 0x00e0) >> 5
	rs2 = (instruction & 0x001c) >> 2
	op2 = instruction & 0x0003
	immediate = instruction & 0x00ff

	# it's halt and catch fire, halt the simulator
	if instruction == 0x0003 : return 0
	
	# decode and execute
	if imm == 0 :
		if context[rs1] > 0x7fff : rs1 = context[rs1] - 0x10000
		else : rs1 = context[rs1]
		if context[rs2] > 0x7fff : rs2 = context[rs2] - 0x10000
		else : rs2 = context[rs2]
	else :
		if context[rst] > 0x7fff : rs1 = context[rst] - 0x10000
		else : rs1 = context[rst]
		if immediate > 0x7f : immediate -= 0x100
		rs2 = immediate

	if ((imm == 0 and (op2 == 0 or op2 == 3)) or imm == 1) :
		if opc == 0 :		
					if (imm == 1) : rs2 &= 0xff
					context[rst] = rs1 & rs2
		elif opc == 1 :		
					if (imm == 1) : rs2 &= 0xff
					context[rst] = rs1 | rs2
		elif opc == 2 :		context[rst] = rs1 ^ rs2
		elif opc == 3 :
					if rs1 < rs2 : context[rst] = 1
					else : context[rst] = 0
		elif opc == 4 :
					if (rs1 & 0xffff) < (rs2 & 0xffff) : context[rst] = 1
					else : context[rst] = 0
		elif opc == 5 :		context[rst] = (rs1 & 0xffff) + (rs2 & 0xffff)
		elif opc == 6 :		context[rst] = (rs1 & 0xffff) - (rs2 & 0xffff)
		elif opc == 8 :		context[rst] = rs2
		elif opc == 9 :		context[rst] = (context[rst] << 8) | (rs2 & 0xff)
		elif opc == 10 :
					if (imm == 1) :
						if rs1 == 0 : pc = pc + rs2;
					else :
						if rs1 == 0 : pc = rs2 - 2
		elif opc == 11 :
					if (imm == 1) :
						if rs1 != 0 : pc = pc + rs2;
					else :
						if rs1 != 0 : pc = rs2 - 2
		else :			print ("[error (invalid computation / branch instruction)]")
	elif (imm == 0 and op2 == 1) :
		if opc == 0 :		context[rst] = (rs1 & 0xffff) >> 1
		elif opc == 1 :		context[rst] = rs1 >> 1
		else :			print ("[error (invalid shift instruction)]")
	elif (imm == 0 and op2 == 2) :
		if opc == 0 :
					if (rs2 & 0x1) :
						byte = memory[(rs2 & 0xffff) >> 1] & 0xff
					else :
						byte = memory[(rs2 & 0xffff) >> 1] >> 8
						
					if byte > 0x7f : context[rst] = byte - 0x100
					else : context[rst] = byte
		elif opc == 1 :
					if (rs2 & 0x1) :
						memory[(rs2 & 0xffff) >> 1] = (memory[(rs2 & 0xffff) >> 1] & 0xff00) | (rs1 & 0xff)
					else :
						memory[(rs2 & 0xffff) >> 1] = (memory[(rs2 & 0xffff) >> 1] & 0x00ff) | ((rs1 & 0xff) << 8)
		elif opc == 4 :
					if (rs2 & 0xffff) == 0xf004 :			# emulate an input character device (address: 61444)
						context[rst] = chr(raw_input('char? '));
					elif (rs2 & 0xffff) == 0xf006 :			# emulate an input integer device (address: 61446)
						context[rst] = int(raw_input('int? '));
					else :
						context[rst] = memory[(rs2 & 0xffff) >> 1]
		elif opc == 5 :		
					if (rs2 & 0xffff) == 0xf000 :			# emulate an output character device (address: 61440)
						sys.stdout.write(chr(rs1 & 0xff))
					elif (rs2 & 0xffff) == 0xf002 :			# emulate an output integer device (address: 61442)
						sys.stdout.write(str(rs1))
					else :
						memory[(rs2 & 0xffff) >> 1] = rs1
		else :			print ("[error (invalid load/store instruction)]")
	else :				print ("[error (invalid instruction)]")

	# increment the program counter
	pc = pc + 2
	context[8] = pc
	# fix the stored word to the matching hardware size
	context[rst] &= 0xffff
	
	return 1

def run(program) :
	codes = {
		0x0000:"and", 0x1000:"or", 0x2000:"xor", 0x3000:"slt",
		0x4000:"sltu", 0x5000:"add", 0x6000:"sub", 0x8000:"ldr",
		0x9000:"ldc", 0x0001:"lsr", 0x1001:"asr",
		0x0002:"ldb", 0x1002:"stb", 0x4002:"ldw", 0x5002:"stw",
		0xa000:"bez", 0xb000:"bnz"
	}
	cycles = 0;
	args = sys.argv[1:]
	
	while True : 
		inst = memory[context[8] >> 1]
		last_pc = context[8]
		
		if not cycle() : break
		cycles += 1
		
		if context[7] < context[9] :
			print ("stack overflow detected!")
			break;
			
		if args :
			if (inst & 0x0800) :
				print ("pc: %04x instruction: %s r%d,%d" % (last_pc, codes[inst & 0xf000], (inst & 0x0700) >> 8, (inst & 0x00ff)))
			else :
				print ("pc: %04x instruction: %s r%d,r%d,r%d" % (last_pc, codes[inst & 0xf003], (inst & 0x0700) >> 8, (inst & 0x00e0) >> 5, (inst & 0x001c) >> 2))
			print ("r0: [%04x] r1: [%04x] r2: [%04x] r3: [%04x]" % (context[0], context[1], context[2], context[3]))
			print ("r4: [%04x] r5: [%04x] r6: [%04x] r7: [%04x]\n" % (context[4], context[5], context[6], context[7]))
			a = raw_input()
	print ("\n[ok]")
	print ("%d cycles" % cycles)
	


def main() :
	program = sys.stdin.readlines()
	if (check(program)) :
		print ("[program has errors]")
	else :
		load(program)
		sys.stdin = open('/dev/tty')
		run(program)

if __name__ == "__main__" : main()
