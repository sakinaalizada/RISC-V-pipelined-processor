import os
import argparse

MemSize = 1000 # memory size, in reality, the memory size should be 2^32, but for this lab, for the space resaon, we keep it as this large number, but the memory is still 32-bit addressable.

class InsMem(object):
    def __init__(self, name, ioDir):
        self.id = name
        
        with open(os.path.join(ioDir, "imem.txt")) as im:
            self.IMem = [data.replace("\n", "") for data in im.readlines()]

    def readInstr(self, ReadAddress):
        idx = (ReadAddress // 4) * 4
        res = ""
        for i in range(idx,idx+4):
            res = res + self.IMem[i]
        return res
          
class DataMem(object):
    def __init__(self, name, ioDir, outDir):
        self.id = name
        self.ioDir = ioDir
        self.outDir = outDir
        with open(os.path.join(ioDir, "dmem.txt")) as dm:
            self.DMem = [data.replace("\n", "") for data in dm.readlines()]
            self.DMem = (self.DMem + 1000*['00000000'])[:1000]

    def readInstr(self, ReadAddress):
        idx = (ReadAddress // 4) * 4
        res = ""
        for i in range(idx,idx+4):
            res = res + self.DMem[i]
        return res
        
    def writeDataMem(self, Address, WriteData):
        data = [WriteData[:8], WriteData[8:16], WriteData[16:24], WriteData[24:]]
        for i in range(4):
            self.DMem[Address + i] = data[i]
                     
    def outputDataMem(self):
        resPath =  os.path.join(self.outDir, self.id  + "_DMEMResult.txt")
        with open(resPath, "w") as rp:
            rp.writelines([str(data) + "\n" for data in self.DMem])

class RegisterFile(object):
    def __init__(self, outDir):
        self.outputFile = outDir + "RFResult.txt" 
        self.Registers = [0x0 for i in range(32)]

    
    def readRF(self, Reg_addr):
        return self.Registers[Reg_addr]
    
    def writeRF(self, Reg_addr, Wrt_reg_data):
        if Reg_addr != 0:
            self.Registers[Reg_addr] = Wrt_reg_data
         
    def outputRF(self, cycle):
        op = ["-"*70+"\n", "State of RF after executing cycle:" + str(cycle) + "\n"]
        op.extend([f"{'0' * 32}\n" if val == 0 else str(val)+"\n" for val in self.Registers])
        if(cycle == 0): perm = "w"
        else: perm = "a"
        with open(self.outputFile, perm) as file:
            file.writelines(op)

class State(object):
    def __init__(self):
        self.IF = {"nop": False, "PC": 0}
        self.ID = {"nop": False, "Instr": 0}
        self.EX = {"nop": False, "Read_data1": 0, "Read_data2": 0, "Imm": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "is_I_type": False, "rd_mem": 0, 
                   "wrt_mem": 0, "alu_op": 0, "wrt_enable": 0}
        self.MEM = {"nop": False, "ALUresult": 0, "Store_data": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "rd_mem": 0, 
                   "wrt_mem": 0, "wrt_enable": 0}
        self.WB = {"nop": False, "Wrt_data": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "wrt_enable": 0}

class Core(object):
    def __init__(self, ioDir, outDir, imem, dmem):
        self.myRF = RegisterFile(outDir)
        self.cycle = 0
        self.halted = False
        self.ioDir = ioDir
        self.state = State()
        self.nextState = State()
        self.ext_imem = imem
        self.ext_dmem = dmem
    def bin_to_dec(self ,bin, digit): 
        while len(bin)<digit: 
            bin = '0'+bin 
        if bin[0] == '0': 
            return int(bin, 2) 
        else: 
            return -1 * (int(''.join('1' if x == '0' else '0' for x in bin), 2) + 1) 
    def dec_to_bin(self, dec, digit): 
        if dec>=0: 
            bin_temp = bin(dec).split("0b")[1] 
            while len(bin_temp)<digit: 
                bin_temp = '0'+bin_temp 
            return bin_temp 
        else: 
            bin_temp = -1*dec 
            return bin(bin_temp-pow(2,digit)).split("0b")[1] 

class SingleStageCore(Core):
    def __init__(self, ioDir, outDir, imem, dmem):
        super(SingleStageCore, self).__init__(ioDir + "/SS_", outDir + "/SS_", imem, dmem)
        self.opFilePath = outDir + "/StateResult_SS.txt"
        self.PerformanceMetricsFilePath = outDir + "/PerformanceMetrics_Result.txt"

    def step(self):
        instruction = imem.readInstr(self.state.IF['PC'])
        opcode=instruction[-7:]
        
        # R-type
        if opcode == '0110011':
            funct3=instruction[-15:-12] 
            funct7=instruction[-32:-25]
            rs1 = int(instruction[-20:-15],2)
            rs2 = int(instruction[-25:-20],2)
            rd = int(instruction[-12:-7],2)
            rs1_data = self.bin_to_dec(str(self.myRF.readRF(rs1)),32)
            rs2_data = self.bin_to_dec(str(self.myRF.readRF(rs2)),32)

            #sub         
            if funct7 == '0100000':
                alu_result = rs1_data - rs2_data
            elif funct7 == '0000000': 
                # add
                if funct3 == '000': 
                    alu_result = rs1_data + rs2_data
                # xor
                elif funct3 == '100': 
                    alu_result = rs1_data ^ rs2_data
                # or
                elif funct3 == '110':
                    alu_result = rs1_data | rs2_data 
                # and
                elif funct3 == '111':
                    alu_result = rs1_data & rs2_data

            self.myRF.writeRF(rd, self.dec_to_bin(alu_result,32))

        # I-type
        elif opcode == '0010011':

            rs1 = int(instruction[-20:-15],2)
            rd = int(instruction[-12:-7],2)
            funct3=instruction[-15:-12]
            rs1_data = self.bin_to_dec(str(self.myRF.readRF(rs1)),32)
            imm = self.bin_to_dec(instruction[-32:-20],12)

            # addi
            if funct3 == '000':
                alu_result = rs1_data + imm
            # xori
            elif funct3 == '100':
                alu_result = rs1_data ^ imm
            # ori
            elif funct3 == '110':  
                alu_result = rs1_data | imm
            # andi
            elif funct3 == '111':
                alu_result = rs1_data & imm

            self.myRF.writeRF(rd, self.dec_to_bin(alu_result,32))

        # J-type
        # jal
        elif opcode == '1101111':
            imm = self.bin_to_dec(instruction[-32]+instruction[-20:-12]+instruction[-21]+instruction[-31:-21]+'0',21)
            rd = int(instruction[-12:-7],2)
            alu_result = self.state.IF['PC'] + 4
            self.nextState.IF['PC'] = self.state.IF['PC'] -4 + imm
            self.myRF.writeRF(rd, self.dec_to_bin(alu_result,32))

        # B-type
        elif opcode == '1100011':
            funct3=instruction[-15:-12] 
            rs1 = int(instruction[-20:-15],2)
            rs2 = int(instruction[-25:-20],2)
            rs1_data = self.bin_to_dec(str(self.myRF.readRF(rs1)),32)
            rs2_data = self.bin_to_dec(str(self.myRF.readRF(rs2)),32)
            imm = self.bin_to_dec(instruction[-32]+instruction[-8]+instruction[-31:- 25]+instruction[-12:-8]+'0',13)
            # beq
            if funct3 == '000':
                if rs1_data-rs2_data == 0:
                    self.nextState.IF['PC'] = self.state.IF['PC'] - 4 + imm
            # bne
            elif funct3 == '001':
                if rs1_data-rs2_data != 0:
                    self.nextState.IF['PC'] = self.state.IF['PC'] - 4 + imm
            

        # I-type - lw
        elif opcode == '0000011':
            rs1 = int(instruction[-20:-15],2)
            rd = int(instruction[-12:-7],2)
            funct3=instruction[-15:-12]
            rs1_data = self.bin_to_dec(str(self.myRF.readRF(rs1)),32)
            imm = self.bin_to_dec(instruction[-32:-20],12)
            alu_result = rs1_data + imm
            self.myRF.writeRF(rd, dmem_ss.readInstr(alu_result))

        # S-type - sw
        elif opcode == "0100011":
            funct3=instruction[-15:-12] 
            rs1 = int(instruction[-20:-15],2)
            rs2 = int(instruction[-25:-20],2)
            rs1_data = self.bin_to_dec(str(self.myRF.readRF(rs1)),32)
            rs2_data = self.bin_to_dec(str(self.myRF.readRF(rs2)),32)
            imm=self.bin_to_dec(instruction[-32:-25]+instruction[-12:-7],12) 
            alu_result = rs1_data + imm
            data_wrt=str(self.dec_to_bin(rs2_data,32)) 
            dmem_ss.writeDataMem(alu_result, data_wrt)

    
        elif opcode == "1111111": 
            
            self.nextState.IF["nop"]=True 
            self.nextState.IF["PC"]=self.state.IF["PC"]

        if not self.state.IF["nop"]:
            self.nextState.IF["PC"]=self.state.IF["PC"] + 4

        if self.state.IF["nop"]:
            self.halted = True

        self.myRF.outputRF(self.cycle) # dump RF
        self.printState(self.nextState, self.cycle) # print states after executing cycle 0, cycle 1, cycle 2 ... 

        
        self.state = self.nextState #The end of the cycle and updates the current state with the values calculated in this cycle
        self.cycle += 1


    def printState(self, state, cycle):
        printstate = ["-"*70+"\n", "State after executing cycle: " + str(cycle) + "\n"]
        printstate.append("IF.PC: " + str(state.IF["PC"]) + "\n")
        printstate.append("IF.nop: " + str(state.IF["nop"]) + "\n")
        
        if(cycle == 0): perm = "w"
        else: perm = "a"
        with open(self.opFilePath, perm) as wf:
            wf.writelines(printstate)

    def printPerformanceMetrics(self):
        ssCore.step()
        printstate = ["-"*29 + "Single Stage Core Performance Metrics" + "-"*29 + "\n"]
        printstate.append("Number of cycles taken: " + str(self.cycle) + "\n")
        printstate.append("Total Number of Instructions: " + str(self.cycle - 1) + "\n")
        printstate.append("Cycles per instruction: " + str(round(self.cycle/(self.cycle - 1),5))+ "\n")
        printstate.append("Instructions per cycle: " + str(round((self.cycle - 1)/self.cycle,6)) + "\n")


        with open(self.PerformanceMetricsFilePath, "w") as wf:
            wf.writelines(printstate)

class FiveStageCore(Core):
    def __init__(self, ioDir, imem, dmem):
        super(FiveStageCore, self).__init__(ioDir + "\\FS_", imem, dmem)
        self.opFilePath = ioDir + "\\StateResult_FS.txt"

    def step(self):
        # Your implementation
        # --------------------- WB stage ---------------------

        if not self.state.WB["nop"]:
            self.myRF.writeRF(self.state.WB["Wrt_reg_addr"], self.state.WB["Wrt_data"])
        
        # --------------------- MEM stage --------------------
        
        if not self.state.MEM["nop"]:
            if self.state.MEM["rd_mem"]:
                self.nextState.WB["Wrt_data"] = self.ext_dmem.readInstr(self.state.MEM["ALUresult"])
            elif self.state.MEM["wrt_mem"]:
                self.ext_dmem.writeDataMem(self.state.MEM["ALUresult"], self.state.MEM["Store_data"])
            # Pass remaining signals to WB
            self.nextState.WB["Wrt_reg_addr"] = self.state.MEM["Wrt_reg_addr"]
            self.nextState.WB["wrt_enable"] = self.state.MEM["wrt_enable"]
            self.nextState.WB["Rs"] = self.state.MEM["Rs"]
            self.nextState.WB["Rt"] = self.state.MEM["Rt"]
        
        # --------------------- EX stage ---------------------

        if not self.state.EX["nop"]:
            # ALU operations
            if self.state.EX["alu_op"] == '':
                self.nextState.MEM["ALUresult"] = perform_ALU_operation(...)
            # Pass remaining signals to MEM
                self.nextState.MEM["wrt_mem"] = self.state.EX["wrt_mem"]
                self.nextState.MEM["rd_mem"] = self.state.EX["rd_mem"]
        
        
        # --------------------- ID stage ---------------------
        
        if not self.state.ID["nop"]:
            instruction = self.state.ID["Instr"]
            # self.EX = {"is_I_type": False, "rd_mem": 0, "wrt_mem": 0, "alu_op": 0, "wrt_enable": 0}
            self.state.EX["Rs"]=int(instruction[-20:-15],2) 
            self.state.EX["Read_data1"]=self.bin_to_dec(str(self.myRF.readRF(self.state.EX["Rs" ])),32) 
            self.state.EX["Rt"]=int(instruction[-25:-20],2) 
            self.state.EX["Read_data2"]=self.bin_to_dec(str(self.myRF.readRF(self.state.EX["Rt" ])),32) 
            self.state.EX["Wrt_reg_addr"]=int(instruction[-12:-7],2) 
            funct3=instruction[-15:-12] 
            funct7=instruction[-32:-25] 
            immIL=self.bin_to_dec(instruction[-32:-20],12) 
            immS=self.bin_to_dec(instruction[-32:-25]+instruction[-12:-7],12) 
            immJ=self.bin_to_dec(instruction[-32]+instruction[-20:-12]+instruction[- 21]+instruction[-31:-21]+'0',21) 
            immB=self.bin_to_dec(instruction[-32]+instruction[-8]+instruction[-31:- 25]+instruction[-12:-8]+'0',13) 
            opcode=instruction[-7:] 
            imm=0 
            if opcode == '0110011': # R-type example
                pass
                # Set up EX stage signals for R-type
            elif opcode == '0010011': # I-type example
                pass
                # Set up EX stage signals for I-type

            if opcode == '0110011': 
                self.state.EX["is_I_type"]=False 
                if funct7 == '0100000': # -
                    self.state.EX["alu_op"] = '0010'
                elif funct7 == '0000000': 
                    if funct3 == '000':
                        self.state.EX["alu_op"] = '0010'
                    elif funct3 == '100': 
                        self.state.EX["alu_op"] = '0010'
                    elif funct3 == '110': 
                        self.state.EX["alu_op"] = '0010'
                        
        
        # --------------------- IF stage ---------------------
        
        if not self.state.IF["nop"]:
            instruction = imem.readInstr(self.state.IF["PC"])
            self.nextState.ID["Instr"] = instruction
            self.nextState.IF["PC"] = self.state.IF["PC"] + 4


        self.halted = True
        if self.state.IF["nop"] and self.state.ID["nop"] and self.state.EX["nop"] and self.state.MEM["nop"] and self.state.WB["nop"]:
            self.halted = True
        
        self.myRF.outputRF(self.cycle) # dump RF
        self.printState(self.nextState, self.cycle) # print states after executing cycle 0, cycle 1, cycle 2 ... 
        
        self.state = self.nextState #The end of the cycle and updates the current state with the values calculated in this cycle
        self.cycle += 1

        
        self.halted = True
        if self.state.IF["nop"] and self.state.ID["nop"] and self.state.EX["nop"] and self.state.MEM["nop"] and self.state.WB["nop"]:
            self.halted = True
        
        # self.myRF.outputRF(self.cycle) # dump RF
        # self.printState(self.nextState, self.cycle) # print states after executing cycle 0, cycle 1, cycle 2 ... 
        
        self.state = self.nextState #The end of the cycle and updates the current state with the values calculated in this cycle
        self.cycle += 1

    def printState(self, state, cycle):
        printstate = ["-"*70+"\n", "State after executing cycle: " + str(cycle) + "\n"]
        printstate.extend(["IF." + key + ": " + str(val) + "\n" for key, val in state.IF.items()])
        printstate.extend(["ID." + key + ": " + str(val) + "\n" for key, val in state.ID.items()])
        printstate.extend(["EX." + key + ": " + str(val) + "\n" for key, val in state.EX.items()])
        printstate.extend(["MEM." + key + ": " + str(val) + "\n" for key, val in state.MEM.items()])
        printstate.extend(["WB." + key + ": " + str(val) + "\n" for key, val in state.WB.items()])

        if(cycle == 0): perm = "w"
        else: perm = "a"
        with open(self.opFilePath, perm) as wf:
            wf.writelines(printstate)

if __name__ == "__main__":
     
    #parse arguments for input file location
    parser = argparse.ArgumentParser(description='RV32I processor')
    parser.add_argument('--iodir', default="input", type=str, help='Directory containing the input files.')
    parser.add_argument('--outdir', default="submissions", type=str, help='Directory for saving output files.')
    args = parser.parse_args()

    ioDir = os.path.abspath(args.iodir)
    outDir = os.path.abspath(args.outdir)

    print("IO Directory:", ioDir)
    
    for test_case in os.listdir(ioDir):
        test_case_path = os.path.join(ioDir, test_case)
        
        if os.path.isdir(test_case_path):            
            test_output_dir = os.path.join(outDir, test_case)
            os.makedirs(test_output_dir, exist_ok=True)

            imem = InsMem("Imem", test_case_path)
            dmem_ss = DataMem("SS", test_case_path, test_output_dir)
            dmem_fs = DataMem("FS", test_case_path, test_output_dir)

                
            ssCore = SingleStageCore(test_case_path, test_output_dir, imem, dmem_ss)
            fsCore = FiveStageCore(test_case_path, imem, dmem_fs)
            
        
            while(True):
                if not ssCore.halted:
                    ssCore.step()
        
                if not fsCore.halted:
                    fsCore.step()

                if ssCore.halted and fsCore.halted:
                    break

            # dump SS and FS data mem.
            dmem_ss.outputDataMem()
            ssCore.printPerformanceMetrics()
            # dmem_fs.outputDataMem()

