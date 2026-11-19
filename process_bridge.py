"""
Process Bridge for Steam Presence
Creates and runs a zero-resource local dummy process matching the active Steam game.
This allows Discord's desktop client on macOS/Linux/Windows to detect the game locally,
enabling native playtime tracking, 30-day Recent Activity history, and Discord Game Time Badges.
"""

import atexit
import os
import re
import shutil
import signal
import subprocess
import sys

def sanitize_game_name(name: str) -> str:
    """Sanitizes game name for use as a filesystem executable name."""
    if not name:
        return "SteamGame"
    # Replace illegal filesystem characters with safe alternatives
    safe = re.sub(r'[/\\:*?"<>|]', ' - ', name)
    # Collapse multiple spaces
    safe = re.sub(r'\s+', ' ', safe).strip()
    return safe[:120] if safe else "SteamGame"


class ProcessBridge:
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "bridges")
        self.base_dir = base_dir
        self.active_proc = None
        self.current_game = None
        self.pid_file = os.path.join(self.base_dir, "bridge.pid")

        try:
            os.makedirs(self.base_dir, exist_ok=True)
        except Exception:
            pass

        # Cleanup any orphan from a previous run
        self._cleanup_orphans()

        # Register exit hook to ensure dummy process is killed on script shutdown
        atexit.register(self.stop)
        try:
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
        except Exception:
            pass

    def _signal_handler(self, signum, frame):
        self.stop()
        sys.exit(0)

    def _cleanup_orphans(self):
        """Kills any orphaned bridge process from previous runs."""
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, "r") as f:
                    old_pid = int(f.read().strip())
                os.kill(old_pid, signal.SIGTERM)
            except Exception:
                pass
            try:
                os.remove(self.pid_file)
            except Exception:
                pass

    def start(self, game_name: str):
        """Starts a zero-resource dummy process matching the game name."""
        if not game_name:
            self.stop()
            return

        if self.current_game == game_name and self.active_proc and self.active_proc.poll() is None:
            return  # Already running for this game

        # Stop previous game bridge if running
        self.stop()

        safe_name = sanitize_game_name(game_name)
        bridge_bin = os.path.join(self.base_dir, safe_name)

        try:
            # On macOS and Linux, copy /bin/sleep to create a zero-resource executable named after the game
            sleep_source = None
            for candidate in ["/bin/sleep", "/usr/bin/sleep"]:
                if os.path.exists(candidate):
                    sleep_source = candidate
                    break

            if sleep_source:
                if not os.path.exists(bridge_bin):
                    shutil.copyfile(sleep_source, bridge_bin)
                    os.chmod(bridge_bin, 0o755)
                    # On macOS ARM64/Apple Silicon, ad-hoc codesign the copied binary so gatekeeper allows it
                    if sys.platform == "darwin":
                        try:
                            subprocess.run(
                                ["codesign", "-s", "-", "-f", bridge_bin],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                timeout=5
                            )
                        except Exception:
                            pass

                # Spawn sleeping dummy process (consumes 0% CPU and minimal memory)
                self.active_proc = subprocess.Popen(
                    [bridge_bin, "86400"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=os.setsid if hasattr(os, "setsid") else None
                )
            else:
                # Fallback for systems without /bin/sleep
                self.active_proc = subprocess.Popen(
                    [sys.executable, "-c", "import time; time.sleep(86400)"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            self.current_game = game_name

            # Save PID
            try:
                with open(self.pid_file, "w") as f:
                    f.write(str(self.active_proc.pid))
            except Exception:
                pass

            print(f"[Process Bridge] Started dummy game process: '{safe_name}' (PID: {self.active_proc.pid})")
            print(f"[Process Bridge] Discord can now track playtime, activity, and badges for '{game_name}'")
        except Exception as e:
            print(f"[Process Bridge] Warning: Failed to spawn dummy process for '{game_name}': {e}")

    def stop(self):
        """Terminates the active bridge process."""
        if self.active_proc is not None:
            try:
                if self.active_proc.poll() is None:
                    if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                        try:
                            os.killpg(os.getpgid(self.active_proc.pid), signal.SIGTERM)
                        except Exception:
                            self.active_proc.terminate()
                    else:
                        self.active_proc.terminate()
                    self.active_proc.wait(timeout=2)
            except Exception:
                try:
                    self.active_proc.kill()
                except Exception:
                    pass
            print(f"[Process Bridge] Stopped dummy process for '{self.current_game}'")
            self.active_proc = None
            self.current_game = None

        if os.path.exists(self.pid_file):
            try:
                os.remove(self.pid_file)
            except Exception:
                pass
