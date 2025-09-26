import subprocess
import os
import signal
import time
import platform

def run_command(cmd, cwd=None, timeout=600):
    """
    Run a shell command with proper handling for Windows (npm.cmd) and Linux/Mac.
    Returns: (exit_code, stdout, stderr)
    """
    # If on Windows, force shell=True so npm.cmd is found
    use_shell = platform.system() == "Windows"

    proc = subprocess.run(
        " ".join(cmd) if use_shell else cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=use_shell,
        timeout=timeout
    )
    return proc.returncode, proc.stdout, proc.stderr


def start_dev_server(cwd, logfile_path):
    """
    Start `npm run dev` in the background, redirecting logs to a file.
    Returns: PID of the process.
    """
    f = open(logfile_path, "a", encoding="utf-8")
    use_shell = platform.system() == "Windows"

    popen = subprocess.Popen(
        "npm run dev" if use_shell else ["npm", "run", "dev"],
        cwd=cwd,
        stdout=f,
        stderr=f,
        shell=use_shell
    )
    return popen.pid


def stop_pid(pid: int):
    """
    Kill process by PID.
    """
    try:
        os.kill(pid, signal.SIGTERM)
    except Exception:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass


def wait_for_url_check(check_fn, timeout=15, interval=0.5):
    """
    Wait until a URL or service is available by repeatedly calling check_fn().
    """
    start = time.time()
    while time.time() - start < timeout:
        if check_fn():
            return True
        time.sleep(interval)
    return False
