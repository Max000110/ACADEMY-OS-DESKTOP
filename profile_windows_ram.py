# Windows Memory Benchmark & Profiling Utility for AcademyOS
# This script monitors RAM allocation (Working Set / Private Bytes) of AcademyOS.exe on Windows.

import os
import sys
import time
import subprocess

try:
    import psutil
except ImportError:
    print("Installing required library 'psutil' to measure RAM allocations...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil

def benchmark_process(exe_path: str, duration_sec: float = 5.0):
    if not os.path.exists(exe_path):
        print(f"Error: Target executable not found at: {exe_path}")
        print("Please build the package first using PyInstaller: pyinstaller --name=AcademyOS --onefile src/main.py")
        return
        
    print(f"Launching target process: {exe_path}...")
    # Launch program in offscreen mode if desired, but standard GUI window test is preferred
    # Since we want to profile GUI boot memory, we launch normally.
    try:
        p = subprocess.Popen([exe_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        print(f"Failed to execute process: {e}")
        return
        
    pid = p.pid
    print(f"Process spawned successfully (PID: {pid}). Gathering RAM memory frames...")
    
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        print("Process exited immediately. Unable to monitor memory.")
        return
        
    samples = []
    start_time = time.time()
    
    # Collect memory frames
    while time.time() - start_time < duration_sec:
        try:
            if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                break
            # Query Working Set (Physical RAM) and Virtual Memory Size
            mem_info = proc.memory_info()
            rss_mb = mem_info.rss / (1024 * 1024)
            vms_mb = mem_info.vms / (1024 * 1024)
            samples.append((time.time() - start_time, rss_mb, vms_mb))
            time.sleep(0.05)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            break
            
    # Terminate process after profiling window
    try:
        proc.terminate()
        proc.wait(timeout=2.0)
        print("Target process successfully terminated after benchmark profiling.")
    except Exception:
        pass
        
    if not samples:
        print("Failed to capture any memory samples.")
        return
        
    # Process results
    rss_values = [s[1] for s in samples]
    vms_values = [s[2] for s in samples]
    
    peak_rss = max(rss_values)
    avg_rss = sum(rss_values) / len(rss_values)
    startup_rss = rss_values[0]
    
    peak_vms = max(vms_values)
    avg_vms = sum(vms_values) / len(vms_values)
    
    report_content = f"""AcademyOS Windows Memory Benchmark Report
Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') if 'datetime' in globals() else time.strftime('%Y-%m-%d %H:%M:%S')}
Target Executable: {exe_path}

PHYSICAL MEMORY BENCHMARK (Resident Working Set):
  - Startup RAM (first frame): {startup_rss:.2f} MB
  - Peak RAM Allocation:       {peak_rss:.2f} MB  (Target < 300MB)
  - Average RAM Allocation:    {avg_rss:.2f} MB

VIRTUAL MEMORY BENCHMARK:
  - Peak Virtual Size:         {peak_vms:.2f} MB
  - Average Virtual Size:      {avg_vms:.2f} MB

Profiling Samples: {len(samples)} frames at 50ms sampling rate.
Status: {"PASS (Peak RAM < 300MB)" if peak_rss < 300 else "WARNING (Peak RAM exceeds 300MB)"}
"""
    
    print("\n" + report_content)
    
    report_path = "windows_memory_benchmark.txt"
    with open(report_path, "w", encoding="utf-8") as rf:
        rf.write(report_content)
    print(f"Benchmark results successfully written to file: {os.path.abspath(report_path)}")

if __name__ == "__main__":
    # Expects target binary to be passed, or defaults to build folder
    target_bin = sys.argv[1] if len(sys.argv) > 1 else r"dist\AcademyOS.exe"
    benchmark_process(target_bin)
