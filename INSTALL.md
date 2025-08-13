# DICOM Normalization Script — Installation & Usage

This repository contains a Python 3 script that normalizes DICOM files
(e.g., GE JPEG Lossless) into valid Part-10 DICOMs suitable for Orthanc.

## 1. Prerequisites

- macOS or Linux
- Python 3.9+ (recommended: latest stable Python 3.x)
- `pip` (Python package manager)

Check your Python installation:

```bash
python3 --version
pip3 --version
````

If Python is not installed:

### macOS

```bash
brew install python
```

### Debian/Ubuntu

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

---

## 2. Setup

We strongly recommend running inside a **virtual environment** to keep dependencies isolated.

### Create and activate a virtual environment

```bash
python3 -m venv ~/venvs/dicom
source ~/venvs/dicom/bin/activate
```

### Upgrade packaging tools

```bash
pip install --upgrade pip setuptools wheel
```

### Install dependencies

From the project root (where `requirements.txt` is located):

```bash
pip install -r requirements.txt
```

---

## 3. Verify installation

Run:

```bash
python - <<'PY'
import pydicom
print("pydicom", pydicom.__version__)
print("handlers:", [h.__name__ for h in pydicom.config.pixel_data_handlers])
PY
```

Expected handlers should include:

* `gdcm_handler`
* `pylibjpeg_handler`
* `jpeg_ls_handler`
* `rle_handler`
* `numpy_handler`
* `pillow_handler`

---

## 4. Usage

Basic syntax:

```bash
python dicom_normalize.py /path/to/input /path/to/output
```

Optional flags:

* `--strip-private` → remove vendor private tags
* `--only-ge` → process only GE-sourced files

Example:

```bash
python dicom_normalize.py "/path/to/GE_disc/IMAGES" "/tmp/orthanc-ready" --strip-private --only-ge
```

---

## 5. Output

* Normalized DICOMs in the output folder
* `normalize_log.csv` in the output folder with per-file status

---

## 6. Common checks

Check that a file has a Part-10 header:

```bash
dcmdump +M +P "(0002,0000)" -q "/tmp/orthanc-ready/somefile.dcm"
```

Check transfer syntax:

```bash
gdcminfo "/tmp/orthanc-ready/somefile.dcm" | grep -i TransferSyntax
```

---

## 7. Troubleshooting

* If `python-gdcm` fails to install, ensure your Python version is 3.9+ and you are on a supported architecture (macOS arm64 or x86\_64, Linux x86\_64).
* If decompression fails for certain files, they may be corrupt or use a very rare transfer syntax. Check the script log for `status=FAIL`.

