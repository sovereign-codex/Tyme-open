#!/usr/bin/env python3
"""
sandbox_runner.py — Docker-based sandbox runner for Tyme Frontier (Phase 0 prototype)

Requirements:
 - Docker installed (>=20.10)
 - python3
 - optionally pip install pyyaml
"""

import subprocess
import json
import uuid
import os
import shlex
import time
from pathlib import Path

SANDBOX_IMAGE = "python:3.11-slim"   # minimal image; can be hardened later

def run_in_sandbox(command, repo_mount, timeout_sec=30, no_network=True, forbidden_cmds=None, env_vars=None):
    """
    Runs 'command' inside a docker container with repo_mount mounted read-write.
    Returns: dict with keys: status, stdout, stderr, exit_code, timed_out, duration, container_id
    """
    forbidden_cmds = forbidden_cmds or ["curl", "wget", "ssh", "nc", "scp"]
    # naive check for dangerous commands in provided command
    for token in forbidden_cmds:
        if token in command:
            return {"status": "forbidden", "reason": f"Detected forbidden token '{token}' in command", "command": command}

    # Create a deterministic container name
    container_name = f"tyme-sandbox-{uuid.uuid4().hex[:8]}"
    mount_src = Path(repo_mount).resolve()
    if not mount_src.exists():
        return {"status": "error", "reason": "repo mount path does not exist", "path": str(mount_src)}

    # Build docker run command
    docker_cmd = [
        "docker", "run", "--rm", "--name", container_name,
        "--network", "none" if no_network else "bridge",
        "-v", f"{str(mount_src)}:/workspace:rw",
        "-w", "/workspace",
        "--pids-limit", "64",           # limit number of processes
        "--memory", "512m",             # memory limit
        "--memory-swap", "512m",
        "--cpus", "0.5"
    ]

    # pass ephemeral env vars
    env_vars = env_vars or {}
    for k, v in env_vars.items():
        docker_cmd += ["-e", f"{k}={v}"]

    # Wrap the command in sh -c to preserve shell features safely
    docker_cmd += [SANDBOX_IMAGE, "sh", "-c", command]

    start = time.time()
    try:
        proc = subprocess.run(docker_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_sec, text=True)
        duration = time.time() - start
        return {
            "status": "ok" if proc.returncode == 0 else "error",
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
            "duration": duration,
            "container": container_name
        }
    except subprocess.TimeoutExpired as tex:
        # Best effort: attempt to remove container if still present
        subprocess.run(["docker", "rm", "-f", container_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return {"status": "timeout", "stdout": tex.stdout or "", "stderr": tex.stderr or "", "timed_out": True, "duration": timeout_sec}
    except Exception as e:
        return {"status": "exception", "reason": str(e)}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--cmd", required=True, help="Command to run in sandbox (quote carefully).")
    parser.add_argument("--repo", required=False, default=".", help="Path to repo to mount")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--no-network", action="store_true", default=True)
    args = parser.parse_args()

    result = run_in_sandbox(args.cmd, args.repo, timeout_sec=args.timeout, no_network=args.no_network)
    print(json.dumps(result, indent=2))
