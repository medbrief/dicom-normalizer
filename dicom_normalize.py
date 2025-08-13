#!/usr/bin/env python3
"""
Normalize DICOMs to valid Part-10 files.

- Reads Part-10 or raw (non-Part-10) datasets (force=True)
- Attempts to decompress pixel data using available handlers (GDCM, pylibjpeg, etc.)
- Writes Part-10 with proper file meta
- If decompressed: writes Explicit VR Little Endian (1.2.840.10008.1.2.1)
- If not decompressed: keeps the original transfer syntax
- Optionally strips private tags
- Preserves SOP Class/Instance UIDs (generates SOP Instance if missing)
- Emits a CSV log with per-file status

Usage:
  python dicom_normalize.py /path/to/input /path/to/output [--strip-private] [--only-ge]
"""

import os
import csv
import argparse
from pathlib import Path
from typing import Optional

import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import (
    UID,
    ExplicitVRLittleEndian,
    ImplicitVRLittleEndian,
    generate_uid,
)

def is_part10(ds: pydicom.dataset.Dataset) -> bool:
    return hasattr(ds, "file_meta") and bool(getattr(ds, "file_meta", None)) and \
           getattr(ds.file_meta, "TransferSyntaxUID", None) is not None

def ts_of(ds: pydicom.dataset.Dataset) -> Optional[UID]:
    if is_part10(ds):
        try:
            return UID(str(ds.file_meta.TransferSyntaxUID))
        except Exception:
            return None
    return None

def is_compressed(ts: Optional[UID]) -> bool:
    if not ts:
        return False
    try:
        return UID(ts).is_compressed
    except Exception:
        return False

def try_decompress(ds: pydicom.dataset.Dataset) -> bool:
    """Attempt to decompress using any installed pixel data handler."""
    if "PixelData" not in ds:
        return False
    ts = ts_of(ds)
    # If we know it's compressed, try to decompress
    if is_compressed(ts):
        # Prefer Dataset.decompress() if present
        if hasattr(ds, "decompress"):
            try:
                ds.decompress()  # type: ignore[attr-defined]
                return True
            except Exception:
                pass
        # Fallback: accessing pixel_array triggers handlers
        try:
            _ = ds.pixel_array  # noqa: F841
            return True
        except Exception:
            return False
    # If TS is unknown (non-Part-10), we can still try pixel_array;
    # handlers may resolve it implicitly (e.g., GDCM).
    if ts is None:
        try:
            _ = ds.pixel_array  # noqa: F841
            return True
        except Exception:
            return False
    return False

def build_file_meta(src: pydicom.dataset.Dataset, target_ts: UID) -> Dataset:
    sop_class = UID(str(src.get("SOPClassUID", src.get((0x0008,0x0016), "1.2.840.10008.5.1.4.1.1.2"))))
    sop_inst  = UID(str(src.get("SOPInstanceUID", src.get((0x0008,0x0018), generate_uid()))))
    fm = Dataset()
    fm.FileMetaInformationVersion = b"\x00\x01"
    fm.MediaStorageSOPClassUID = sop_class
    fm.MediaStorageSOPInstanceUID = sop_inst
    fm.TransferSyntaxUID = target_ts
    # ImplementationClassUID: use your org's private root if you have one
    fm.ImplementationClassUID = UID("1.2.826.0.1.3680043.10.743")
    return fm

def looks_like_ge(ds: pydicom.dataset.Dataset) -> bool:
    manu = (str(ds.get("Manufacturer", "")) or "").lower()
    impl = str(ds.file_meta.get("ImplementationClassUID", "")) if is_part10(ds) else ""
    # GE roots often start with 1.2.840.113619
    return ("ge" in manu) or impl.startswith("1.2.840.113619")

def normalise_one(src_path: Path, dst_path: Path, strip_private: bool=False, only_ge: bool=False) -> dict:
    row = {
        "input": str(src_path),
        "output": str(dst_path),
        "status": "FAIL",
        "part10_in": "",
        "ts_in": "",
        "decompressed": "",
        "ts_out": "",
        "manufacturer": "",
        "modality": "",
        "sop_class": "",
        "error": "",
    }
    try:
        # Read as flexibly as possible
        ds = pydicom.dcmread(str(src_path), force=True, stop_before_pixels=False)

        if only_ge and not looks_like_ge(ds):
            row["status"] = "SKIP"
            return row

        row["part10_in"] = "yes" if is_part10(ds) else "no"
        ts_in = ts_of(ds)
        row["ts_in"] = str(ts_in) if ts_in else ""
        row["manufacturer"] = str(ds.get("Manufacturer", ""))
        row["modality"] = str(ds.get("Modality", ""))
        row["sop_class"] = str(ds.get("SOPClassUID", ds.get((0x0008,0x0016), "")))

        decompressed = try_decompress(ds)
        row["decompressed"] = "yes" if decompressed else "no"

        if decompressed:
            target_ts = ExplicitVRLittleEndian
            ds.is_little_endian = True
            ds.is_implicit_VR = False
        else:
            # Keep original TS if known; if unknown, fallback to Implicit VR LE
            target_ts = ts_in or ImplicitVRLittleEndian

        file_meta = build_file_meta(ds, target_ts)
        fds = FileDataset(str(dst_path), {}, file_meta=file_meta, preamble=b"\x00"*128)

        # Set container flags consistently with chosen TS
        fds.is_little_endian = (target_ts in (ExplicitVRLittleEndian, ImplicitVRLittleEndian))
        fds.is_implicit_VR = (target_ts == ImplicitVRLittleEndian)

        # Copy all non-meta elements (skip any residual 0002 group)
        for elem in ds.iterall():
            if elem.tag.group != 0x0002:
                fds.add(elem)

        if strip_private:
            fds.remove_private_tags()

        # Save as proper Part-10
        fds.save_as(str(dst_path), write_like_original=False)

        # Confirm final TS
        try:
            ds2 = pydicom.dcmread(str(dst_path), stop_before_pixels=True)
            row["ts_out"] = str(ds2.file_meta.get("TransferSyntaxUID", ""))
        except Exception:
            row["ts_out"] = ""

        row["status"] = "OK"
        return row

    except Exception as e:
        row["error"] = str(e)
        return row

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_dir", type=Path, help="Folder containing DICOM files")
    ap.add_argument("output_dir", type=Path, help="Folder to write normalized DICOMs")
    ap.add_argument("--strip-private", action="store_true", help="Remove vendor private tags")
    ap.add_argument("--only-ge", action="store_true", help="Process only GE-sourced files")
    args = ap.parse_args()

    inp: Path = args.input_dir
    out: Path = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    log_path = out / "normalize_log.csv"

    rows = []
    for root, _, files in os.walk(inp):
        for name in files:
            src = Path(root) / name
            rel = src.relative_to(inp)
            dst = out / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            res = normalise_one(src, dst, strip_private=args.strip_private, only_ge=args.only_ge)
            rows.append(res)
            print(f"[{res['status']}] {rel}  inTS={res['ts_in'] or '-'}  outTS={res['ts_out'] or '-'}  dec={res['decompressed'] or '-'}")

    if rows:
        with open(log_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\nLog written to: {log_path}")

if __name__ == "__main__":
    main()

