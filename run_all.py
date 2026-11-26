"""Run the complete workflow in order: Figure 2 -> worked example (Table 3, Figure 3) -> Figure 4 -> Tables S1-S2."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    ("figure1_framework", "make_figure1.py"),
    ("figure2_open_data", "make_figure2.py"),
    ("sids_worked_example", "make_sids_example.py"),
    ("figure4_value_chain", "make_figure4.py"),
    (".", "build_supplementary_tables.py"),
]
for folder, script in STEPS:
    print(f"\n=== {folder}/{script} ===", flush=True)
    subprocess.run([sys.executable, script], cwd=os.path.join(ROOT, folder), check=True)
print("\nAll steps completed.")
