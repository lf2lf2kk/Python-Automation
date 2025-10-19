#!/usr/bin/env python3
"""
Remove permission restrictions from a PDF on Windows.

Usage:
    python remove_pdf_permissions.py "C:\\path\\to\\input.pdf" "C:\\path\\to\\output.pdf" [owner_password]

If owner_password is provided, the script will try it when opening the PDF.
"""

import sys
import os
import subprocess
import shutil

def try_pikepdf(infile, outfile, owner_password=None):
    try:
        import pikepdf
    except Exception as e:
        print("pikepdf not installed or failed to import:", e)
        return False, "pikepdf_not_available"

    try:
        if owner_password:
            pdf = pikepdf.open(infile, password=owner_password)
        else:
            pdf = pikepdf.open(infile)  # works for non-encrypted or permission-only PDFs
        # Save a copy — this will remove encryption/permission flags
        pdf.save(outfile)
        pdf.close()
        return True, "pikepdf_ok"
    except pikepdf._qpdf.PasswordError:
        return False, "wrong_password"
    except Exception as e:
        return False, f"pikepdf_error: {e}"

def try_ghostscript(infile, outfile, gs_path=None):
    # Default typical Ghostscript executable name for Windows 64-bit
    if gs_path:
        gs_exec = gs_path
    else:
        gs_exec = r"C:\Program Files\gs\gs9.###\bin\gswin64c.exe"  # user to replace if needed

    # Build the command — using PDFWRITE to rewrite and drop permissions
    cmd = [
        gs_exec,
        "-q",
        "-dNOPAUSE",
        "-dBATCH",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-sOutputFile=" + outfile,
        infile
    ]

    try:
        # Run command
        print("Running Ghostscript to rewrite PDF...")
        subprocess.check_call(cmd, shell=False)
        return True, "ghostscript_ok"
    except FileNotFoundError:
        return False, "ghostscript_not_found"
    except subprocess.CalledProcessError as e:
        return False, f"ghostscript_error: returncode={e.returncode}"
    except Exception as e:
        return False, f"ghostscript_exception: {e}"

def main():
    if not (3 <= len(sys.argv) <= 4):
        print("Usage: python remove_pdf_permissions.py <input.pdf> <output.pdf> [owner_password]")
        sys.exit(2)

    infile = sys.argv[1]
    outfile = sys.argv[2]
    owner_password = sys.argv[3] if len(sys.argv) == 4 else None

    if not os.path.isfile(infile):
        print("Input file not found:", infile)
        sys.exit(1)

    # Make sure output directory exists
    outdir = os.path.dirname(os.path.abspath(outfile)) or "."
    os.makedirs(outdir, exist_ok=True)

    # First attempt: pikepdf (recommended)
    print("Trying pikepdf...")
    ok, msg = try_pikepdf(infile, outfile, owner_password)
    if ok:
        print("Success with pikepdf — saved to:", outfile)
        sys.exit(0)
    else:
        print("pikepdf failed:", msg)

    # Second attempt: Ghostscript rewrite (try common locations if needed)
    print("Attempting Ghostscript fallback...")
    # Try default common paths for Ghostscript on Windows
    common_paths = [
        r"C:\Program Files\gs\gs9.56.1\bin\gswin64c.exe",  # example version
        r"C:\Program Files\gs\gs9.55.0\bin\gswin64c.exe",
        r"C:\Program Files\gs\gs9.54.0\bin\gswin64c.exe",
        r"C:\Program Files\gs\gs9.53.3\bin\gswin64c.exe",
        r"C:\Program Files\gs\gs9.###\bin\gswin64c.exe"
    ]

    for path in common_paths:
        if os.path.isfile(path):
            ok, msg = try_ghostscript(infile, outfile, gs_path=path)
            if ok:
                print("Success with Ghostscript (path:", path, ") — saved to:", outfile)
                sys.exit(0)
            else:
                print(f"Ghostscript at {path} failed:", msg)

    # As a last resort, try calling gs without path (if it's on PATH)
    ok, msg = try_ghostscript(infile, outfile, gs_path=None)
    if ok:
        print("Success with Ghostscript (on PATH) — saved to:", outfile)
        sys.exit(0)
    else:
        print("Ghostscript fallback failed:", msg)

    print("All methods failed. If the PDF requires an owner password, supply it as the third argument.")
    sys.exit(3)

if __name__ == "__main__":
    main()
