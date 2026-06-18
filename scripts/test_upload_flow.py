from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from core.utils import expand_uploaded_inputs, process_files  # noqa: E402


def main():
    generated = ROOT / "tmp_generated_upload"
    bundle = ROOT / "tmp_upload_bundle.zip"

    generated.mkdir(exist_ok=True)

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_master_data.py")],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "generate_pos_data.py"),
            "--small",
            "--out",
            str(generated),
        ],
        check=True,
    )

    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in os.listdir(generated):
            path = generated / name
            if path.is_file():
                zf.write(path, arcname=name)

    with open(bundle, "rb") as f:
        expanded = expand_uploaded_inputs([("upload_bundle.zip", f.read())])
    result = process_files(expanded)
    fact = result["fact"]
    dq = result["dq"]

    print("Expanded files:", len(expanded))
    print("Processed files:", len(result.get("files_processed", [])))
    print("Fact rows:", len(fact))
    print("DQ score:", dq.get("dq_score"))
    print("Source formats:", sorted(fact["source_format"].dropna().unique().tolist()))

    bundle.unlink(missing_ok=True)
    shutil.rmtree(generated, ignore_errors=True)


if __name__ == "__main__":
    main()
