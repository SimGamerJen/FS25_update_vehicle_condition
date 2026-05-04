"""
Windows GUI wrapper for update_vehicle_condition.py

Purpose:
- Provides a simple desktop front-end for the existing CLI script.
- Keeps XML parsing/update logic inside update_vehicle_condition.py.
- Separates LIST from APPLY so --list is never accidentally used when updating.
- Creates a timestamped backup of vehicles.xml before applying changes.

Expected layout:
    folder/
      update_vehicle_condition.py
      update_vehicle_condition_gui.py

Run:
    py update_vehicle_condition_gui.py

Optional packaging later:
    py -m pip install pyinstaller
    py -m PyInstaller --onefile --windowed update_vehicle_condition_gui.py
"""

from __future__ import annotations

import datetime as _dt
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Iterable, List, Optional


APP_TITLE = "FS25 Vehicle Condition Tool"
SCRIPT_NAME = "update_vehicle_condition.py"


class VehicleConditionGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("980x720")
        self.minsize(900, 620)

        self.output_queue: queue.Queue[str] = queue.Queue()
        self.current_process: Optional[subprocess.Popen[str]] = None

        self._build_vars()
        self._build_ui()
        self._refresh_command_preview()
        self._poll_output_queue()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _build_vars(self) -> None:
        script_default = Path(__file__).with_name(SCRIPT_NAME)

        self.script_path_var = tk.StringVar(value=str(script_default))
        self.vehicles_xml_var = tk.StringVar(value="")

        self.owned_only_var = tk.BooleanVar(value=True)
        self.create_backup_var = tk.BooleanVar(value=True)
        self.use_py_launcher_var = tk.BooleanVar(value=True)

        self.match_var = tk.StringVar(value="")
        self.age_var = tk.StringVar(value="")
        self.operating_time_var = tk.StringVar(value="")
        self.wear_var = tk.StringVar(value="")
        self.damage_var = tk.StringVar(value="")
        self.extra_args_var = tk.StringVar(value="")

        self.status_var = tk.StringVar(value="Ready")
        self.command_preview_var = tk.StringVar(value="")

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        header = ttk.Frame(self, padding=(14, 12, 14, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        ttk.Label(header, text=APP_TITLE, font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        ttk.Label(
            header,
            text="GUI wrapper for update_vehicle_condition.py. Use List to inspect matches, Apply to update the XML.",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))

        paths = ttk.LabelFrame(self, text="Files", padding=12)
        paths.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
        paths.columnconfigure(1, weight=1)

        ttk.Label(paths, text="Python script").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        script_entry = ttk.Entry(paths, textvariable=self.script_path_var)
        script_entry.grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(paths, text="Browse...", command=self._browse_script).grid(row=0, column=2, padx=(8, 0), pady=4)

        ttk.Label(paths, text="vehicles.xml").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        xml_entry = ttk.Entry(paths, textvariable=self.vehicles_xml_var)
        xml_entry.grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Button(paths, text="Browse...", command=self._browse_vehicles_xml).grid(row=1, column=2, padx=(8, 0), pady=4)

        options = ttk.LabelFrame(self, text="Update options", padding=12)
        options.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))
        for col in range(6):
            options.columnconfigure(col, weight=1 if col in (1, 3, 5) else 0)

        ttk.Label(options, text="Match text").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=5)
        ttk.Entry(options, textvariable=self.match_var).grid(row=0, column=1, sticky="ew", pady=5)

        ttk.Label(options, text="Age").grid(row=0, column=2, sticky="w", padx=(16, 8), pady=5)
        ttk.Entry(options, textvariable=self.age_var, width=16).grid(row=0, column=3, sticky="ew", pady=5)

        ttk.Label(options, text="Operating time").grid(row=0, column=4, sticky="w", padx=(16, 8), pady=5)
        ttk.Entry(options, textvariable=self.operating_time_var, width=18).grid(row=0, column=5, sticky="ew", pady=5)

        ttk.Label(options, text="Wear").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=5)
        ttk.Entry(options, textvariable=self.wear_var, width=16).grid(row=1, column=1, sticky="ew", pady=5)

        ttk.Label(options, text="Damage").grid(row=1, column=2, sticky="w", padx=(16, 8), pady=5)
        ttk.Entry(options, textvariable=self.damage_var, width=16).grid(row=1, column=3, sticky="ew", pady=5)

        ttk.Label(options, text="Extra CLI args").grid(row=1, column=4, sticky="w", padx=(16, 8), pady=5)
        ttk.Entry(options, textvariable=self.extra_args_var).grid(row=1, column=5, sticky="ew", pady=5)

        ttk.Checkbutton(options, text="Owned vehicles only", variable=self.owned_only_var).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        ttk.Checkbutton(options, text="Create backup before applying", variable=self.create_backup_var).grid(
            row=2, column=2, columnspan=2, sticky="w", pady=(8, 0)
        )
        ttk.Checkbutton(options, text="Use Windows py launcher", variable=self.use_py_launcher_var).grid(
            row=2, column=4, columnspan=2, sticky="w", pady=(8, 0)
        )

        actions = ttk.Frame(self, padding=(14, 0, 14, 10))
        actions.grid(row=3, column=0, sticky="nsew")
        actions.columnconfigure(0, weight=1)
        actions.rowconfigure(2, weight=1)

        command_frame = ttk.LabelFrame(actions, text="Command preview", padding=10)
        command_frame.grid(row=0, column=0, sticky="ew")
        command_frame.columnconfigure(0, weight=1)

        command_entry = ttk.Entry(command_frame, textvariable=self.command_preview_var, state="readonly")
        command_entry.grid(row=0, column=0, sticky="ew")
        ttk.Button(command_frame, text="Copy", command=self._copy_command_preview).grid(row=0, column=1, padx=(8, 0))

        button_frame = ttk.Frame(actions)
        button_frame.grid(row=1, column=0, sticky="ew", pady=(10, 10))
        button_frame.columnconfigure(5, weight=1)

        ttk.Button(button_frame, text="List matching vehicles", command=self._run_list).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(button_frame, text="Apply update", command=self._run_apply).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(button_frame, text="Open XML folder", command=self._open_xml_folder).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(button_frame, text="Clear output", command=self._clear_output).grid(row=0, column=3, padx=(0, 8))
        ttk.Button(button_frame, text="Stop", command=self._stop_process).grid(row=0, column=4, padx=(0, 8))
        ttk.Label(button_frame, textvariable=self.status_var).grid(row=0, column=5, sticky="e")

        output_frame = ttk.LabelFrame(actions, text="Output", padding=10)
        output_frame.grid(row=2, column=0, sticky="nsew")
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.output_text = tk.Text(output_frame, wrap="word", height=18, font=("Consolas", 10))
        self.output_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.output_text.configure(yscrollcommand=scroll.set)

        for var in (
            self.script_path_var,
            self.vehicles_xml_var,
            self.match_var,
            self.age_var,
            self.operating_time_var,
            self.wear_var,
            self.damage_var,
            self.extra_args_var,
        ):
            var.trace_add("write", lambda *_: self._refresh_command_preview())

        self.owned_only_var.trace_add("write", lambda *_: self._refresh_command_preview())
        self.use_py_launcher_var.trace_add("write", lambda *_: self._refresh_command_preview())

    # ------------------------------------------------------------------
    # Command construction
    # ------------------------------------------------------------------

    def _python_command(self) -> List[str]:
        if self.use_py_launcher_var.get():
            return ["py"]
        return [sys.executable]

    def _base_command(self, *, list_mode: bool) -> List[str]:
        script_path = self.script_path_var.get().strip()
        vehicles_xml = self.vehicles_xml_var.get().strip()

        cmd: List[str] = []
        cmd.extend(self._python_command())
        cmd.append(script_path)
        cmd.append(vehicles_xml)

        if list_mode:
            cmd.append("--list")

        if self.owned_only_var.get():
            cmd.append("--owned-only")

        match = self.match_var.get().strip()
        if match:
            cmd.extend(["--match", match])

        if not list_mode:
            self._append_optional_value(cmd, "--age", self.age_var.get())
            self._append_optional_value(cmd, "--operating-time", self.operating_time_var.get())
            self._append_optional_value(cmd, "--wear", self.wear_var.get())
            self._append_optional_value(cmd, "--damage", self.damage_var.get())

        extra = self.extra_args_var.get().strip()
        if extra:
            # Simple split is deliberate: this field is for short flags such as --verbose.
            # For quoted values, use the dedicated fields above or run the previewed command manually.
            cmd.extend(extra.split())

        return cmd

    @staticmethod
    def _append_optional_value(cmd: List[str], flag: str, raw_value: str) -> None:
        value = raw_value.strip()
        if value:
            cmd.extend([flag, value])

    @staticmethod
    def _format_command(cmd: Iterable[str]) -> str:
        parts = []
        for part in cmd:
            if not part:
                continue
            if any(ch.isspace() for ch in part) or any(ch in part for ch in "()[]{}&^"):
                parts.append(f'"{part}"')
            else:
                parts.append(part)
        return " ".join(parts)

    def _refresh_command_preview(self) -> None:
        try:
            cmd = self._base_command(list_mode=False)
            self.command_preview_var.set(self._format_command(cmd))
        except Exception:
            self.command_preview_var.set("")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _browse_script(self) -> None:
        path = filedialog.askopenfilename(
            title="Select update_vehicle_condition.py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
        )
        if path:
            self.script_path_var.set(path)

    def _browse_vehicles_xml(self) -> None:
        path = filedialog.askopenfilename(
            title="Select vehicles.xml",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
        )
        if path:
            self.vehicles_xml_var.set(path)

    def _copy_command_preview(self) -> None:
        command = self.command_preview_var.get()
        self.clipboard_clear()
        self.clipboard_append(command)
        self.status_var.set("Command copied")

    def _clear_output(self) -> None:
        self.output_text.delete("1.0", "end")
        self.status_var.set("Output cleared")

    def _open_xml_folder(self) -> None:
        xml_path = Path(self.vehicles_xml_var.get().strip())
        folder = xml_path.parent if xml_path.exists() else None
        if not folder:
            messagebox.showwarning("Folder not found", "Select a valid vehicles.xml file first.")
            return
        os.startfile(folder)  # type: ignore[attr-defined]

    def _run_list(self) -> None:
        if not self._validate_common_inputs():
            return
        cmd = self._base_command(list_mode=True)
        self._run_command(cmd, action_name="List")

    def _run_apply(self) -> None:
        if not self._validate_common_inputs():
            return
        if not self._validate_apply_inputs():
            return

        xml_path = Path(self.vehicles_xml_var.get().strip())

        answer = messagebox.askyesno(
            "Apply update?",
            "This will update the selected vehicles.xml file.\n\n"
            "Use 'List matching vehicles' first if you want to confirm the target vehicles.\n\n"
            "Continue?",
        )
        if not answer:
            self.status_var.set("Apply cancelled")
            return

        if self.create_backup_var.get():
            try:
                backup_path = self._create_backup(xml_path)
                self._append_output(f"Backup created: {backup_path}\n")
            except Exception as exc:
                messagebox.showerror("Backup failed", f"Could not create backup:\n{exc}")
                self.status_var.set("Backup failed")
                return

        cmd = self._base_command(list_mode=False)
        self._run_command(cmd, action_name="Apply")

    def _stop_process(self) -> None:
        if self.current_process and self.current_process.poll() is None:
            self.current_process.terminate()
            self.status_var.set("Stopping process...")
        else:
            self.status_var.set("No running process")

    # ------------------------------------------------------------------
    # Validation and backup
    # ------------------------------------------------------------------

    def _validate_common_inputs(self) -> bool:
        script_path = Path(self.script_path_var.get().strip())
        xml_path = Path(self.vehicles_xml_var.get().strip())

        if not script_path.exists():
            messagebox.showerror("Script not found", f"Could not find script:\n{script_path}")
            return False

        if not xml_path.exists():
            messagebox.showerror("vehicles.xml not found", f"Could not find XML file:\n{xml_path}")
            return False

        if xml_path.name.lower() != "vehicles.xml":
            answer = messagebox.askyesno(
                "Unexpected XML filename",
                f"The selected file is named '{xml_path.name}', not 'vehicles.xml'.\n\nContinue anyway?",
            )
            if not answer:
                return False

        return True

    def _validate_apply_inputs(self) -> bool:
        supplied = [
            self.age_var.get().strip(),
            self.operating_time_var.get().strip(),
            self.wear_var.get().strip(),
            self.damage_var.get().strip(),
            self.extra_args_var.get().strip(),
        ]

        if not any(supplied):
            messagebox.showwarning(
                "No update values",
                "No update values were entered. Add at least one condition value before applying.",
            )
            return False

        numeric_fields = [
            ("Age", self.age_var.get()),
            ("Operating time", self.operating_time_var.get()),
            ("Wear", self.wear_var.get()),
            ("Damage", self.damage_var.get()),
        ]
        for label, raw in numeric_fields:
            value = raw.strip()
            if not value:
                continue
            try:
                float(value)
            except ValueError:
                messagebox.showerror("Invalid number", f"{label} must be numeric. Current value: {value}")
                return False

        return True

    @staticmethod
    def _create_backup(xml_path: Path) -> Path:
        timestamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = xml_path.with_name(f"{xml_path.stem}.backup_{timestamp}{xml_path.suffix}")
        shutil.copy2(xml_path, backup_path)
        return backup_path

    # ------------------------------------------------------------------
    # Subprocess handling
    # ------------------------------------------------------------------

    def _run_command(self, cmd: List[str], *, action_name: str) -> None:
        if self.current_process and self.current_process.poll() is None:
            messagebox.showwarning("Process already running", "Wait for the current command to finish, or stop it first.")
            return

        self._append_output("\n" + "=" * 88 + "\n")
        self._append_output(f"{action_name} command:\n{self._format_command(cmd)}\n\n")
        self.status_var.set(f"{action_name} running...")

        thread = threading.Thread(target=self._worker_run_command, args=(cmd, action_name), daemon=True)
        thread.start()

    def _worker_run_command(self, cmd: List[str], action_name: str) -> None:
        try:
            script_path = Path(self.script_path_var.get().strip())
            cwd = str(script_path.parent) if script_path.exists() else None

            self.current_process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            assert self.current_process.stdout is not None
            for line in self.current_process.stdout:
                self.output_queue.put(line)

            rc = self.current_process.wait()
            self.output_queue.put(f"\n[{action_name} finished with exit code {rc}]\n")
            self.output_queue.put(f"__STATUS__:{action_name} finished" if rc == 0 else f"__STATUS__:{action_name} failed")

        except FileNotFoundError as exc:
            self.output_queue.put(f"ERROR: {exc}\n")
            self.output_queue.put("__STATUS__:Command failed")
        except Exception as exc:
            self.output_queue.put(f"ERROR: {exc}\n")
            self.output_queue.put("__STATUS__:Command failed")
        finally:
            self.current_process = None

    def _poll_output_queue(self) -> None:
        try:
            while True:
                item = self.output_queue.get_nowait()
                if item.startswith("__STATUS__:"):
                    self.status_var.set(item.replace("__STATUS__:", "", 1))
                else:
                    self._append_output(item)
        except queue.Empty:
            pass
        self.after(100, self._poll_output_queue)

    def _append_output(self, text: str) -> None:
        self.output_text.insert("end", text)
        self.output_text.see("end")


def main() -> None:
    app = VehicleConditionGui()
    app.mainloop()


if __name__ == "__main__":
    main()
