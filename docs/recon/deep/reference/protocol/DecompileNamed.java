import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import java.io.FileWriter;
import java.io.PrintWriter;

public class DecompileNamed extends GhidraScript {
    public void run() throws Exception {
        String[] targets = {
            "Irbis_Format", "UNIFOR", "Irbis_InitPFT", "IrbisFindPosting",
            "Irbisfind", "IrbisSearch_Range", "InsertTerm", "UMARCI"
        };
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);
        String out = "C:\\IRBIS64\\_re_tools\\decompiled.c";
        PrintWriter w = new PrintWriter(new FileWriter(out));
        w.println("/* Ghidra pseudo-C of selected IRBIS64.dll engine functions */");
        FunctionManager fm = currentProgram.getFunctionManager();
        int done = 0;
        for (String name : targets) {
            boolean found = false;
            for (Function f : fm.getFunctions(true)) {
                if (f.getName().equalsIgnoreCase(name)) {
                    found = true;
                    w.println("\n/* ===== " + f.getName() + " @ " + f.getEntryPoint() + " ===== */");
                    DecompileResults r = dec.decompileFunction(f, 90, monitor);
                    if (r != null && r.decompileCompleted() && r.getDecompiledFunction() != null) {
                        w.println(r.getDecompiledFunction().getC());
                        done++;
                    } else {
                        w.println("// decompile failed: " + (r == null ? "null" : r.getErrorMessage()));
                    }
                }
            }
            if (!found) {
                w.println("\n/* ===== " + name + ": function not found ===== */");
            }
        }
        w.close();
        println("DecompileNamed: wrote " + done + " functions to " + out);
    }
}
