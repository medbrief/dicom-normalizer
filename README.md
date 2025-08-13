# DICOM Normalization Script for Orthanc and PACS systems

This project provides a Python 3 utility to **normalize vendor-specific DICOM files** (e.g., GE Healthcare JPEG Lossless) into valid DICOM Part-10 files that are fully compatible with [Orthanc](https://www.orthanc-server.com/).

Some vendor systems produce DICOMs that:
- Use uncommon or proprietary transfer syntaxes
- Lack required DICOM File Meta Information
- Contain private tags or manufacturer-specific quirks
- Fail to load in Orthanc without conversion

This script automatically:
- Detects and decodes compressed pixel data (JPEG Lossless, JPEG-LS, JPEG2000, RLE)
- Adds missing File Meta Information (DICOM Part-10 header)
- Optionally strips private vendor tags
- Saves clean, standards-compliant DICOMs to a chosen output directory

---

## Features

- ✅ Supports **GE Healthcare** and other vendor-specific DICOMs
- ✅ Decodes using `pylibjpeg` and `python-gdcm` pixel data handlers
- ✅ Outputs clean, explicit VR little-endian DICOMs
- ✅ Compatible with Orthanc, PACS, and most DICOM viewers
- ✅ CSV log file for processing results

---

## Example

**Before:**  
GE JPEG Lossless DICOM without Part-10 header → Orthanc import fails

**After:**  
Standard DICOM Part-10 (Explicit VR Little Endian) with valid meta header → Orthanc import succeeds

---

## Quick Start

1. **Install dependencies**  
   See [`INSTALL.md`](INSTALL.md) for full step-by-step setup instructions.

2. **Run the script**  

```bash
python dicom_normalize.py "/path/to/input" "/path/to/output"
````

**Optional flags:**

* `--strip-private` → remove vendor private tags
* `--only-ge` → process only GE-sourced files

Example:

```bash
python dicom_normalize.py "/path/to/GE_disc/IMAGES" "/tmp/orthanc-ready" --strip-private --only-ge
```

---

## Requirements

* Python 3.9+
* macOS or Linux
* See [`requirements.txt`](requirements.txt) for exact Python packages

---

## How It Works

1. **Reads the DICOM** using `pydicom`
2. **Decodes compressed pixel data** via:

   * `pylibjpeg-libjpeg` (JPEG)
   * `pylibjpeg-openjpeg` (JPEG2000)
   * `pylibjpeg-rle` (RLE)
   * `python-gdcm` (fallback for unusual encodings)
3. **Creates a new dataset** with:

   * Required `(0002,xxxx)` File Meta Information
   * Standard Transfer Syntax UID: `1.2.840.10008.1.2.1` (Explicit VR Little Endian)
4. **Writes to output directory**
5. **Logs the outcome** in `normalize_log.csv`

---

## Why This Exists

Orthanc and some PACS systems are strict about DICOM compliance.
Many GE Healthcare and other vendor discs include images in proprietary or incomplete formats that cause ingestion errors.

Rather than manually fixing them with DCMTK/GDCM commands, this script automates the process in Python.

---

## License

MIT — use at your own risk.
Not affiliated with GE Healthcare or Orthanc.

