import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import java.io.FileWriter;
import java.io.PrintWriter;

// Focused re-run for UNIFOR only, with a generous per-function decompiler
// timeout (600s) — the default 90s timed out on this huge dispatcher.
public class DecompileUnifor extends GhidraScript {
    public void run() throws Exception {
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);
        String out = "C:\\IRBIS64\\_re_tools\\decompiled_unifor.c";
        PrintWriter w = new PrintWriter(new FileWriter(out));
        w.println("/* Ghidra pseudo-C of UNIFOR @ IRBIS64.dll (600s timeout) */");
        FunctionManager fm = currentProgram.getFunctionManager();
        int done = 0;
        for (Function f : fm.getFunctions(true)) {
            if (f.getName().equalsIgnoreCase("UNIFOR")) {
                w.println("\n/* ===== " + f.getName() + " @ " + f.getEntryPoint() + " ===== */");
                DecompileResults r = dec.decompileFunction(f, 600, monitor);
                if (r != null && r.decompileCompleted() && r.getDecompiledFunction() != null) {
                    w.println(r.getDecompiledFunction().getC());
                    done++;
                } else {
                    w.println("// decompile failed: " + (r == null ? "null" : r.getErrorMessage()));
                }
            }
        }
        w.close();
        println("DecompileUnifor: wrote " + done + " functions to " + out);
    }
}
