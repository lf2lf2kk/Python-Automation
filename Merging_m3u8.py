"""
Batch merge HLS .m3u8 playlists into complete videos (one output per playlist).

Requirements:
  - FFmpeg must be installed and on PATH.
Works on Windows/macOS/Linux (Python 3.8+).

Usage:
  python merge_m3u8.py                   # use current folder, writes MP4s to ./out
  python merge_m3u8.py -i /path/to/m3u8s -o /path/to/out
  python merge_m3u8.py -p "??.m3u8"      # custom glob (e.g., 01..99.m3u8)
  python merge_m3u8.py --reencode        # fall back to re-encode if stream copy fails
  python merge_m3u8.py --headers "Cookie: a=b\r\nUser-Agent: MyUA"  # HTTP headers
"""
import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional

def pretty(cmd: list[str]) -> str:
    # For display only
    import shlex
    return " ".join(shlex.quote(x) for x in cmd)

def run(cmd: list[str]):
    print(f"\n>>> {pretty(cmd)}\n", flush=True)
    try:
        return subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        return e

def build_output_name(m3u8_path: Path, out_dir: Path, container: str = "mp4") -> Path:
    return out_dir / f"{m3u8_path.stem}.{container}"

def try_stream_copy(m3u8_path: Path, out_path: Path, headers: Optional[str]):
    # Stream copy: fast, lossless
    cmd = [
        "ffmpeg",
        "-y",
        "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
        "-allowed_extensions", "ALL",
    ]
    if headers:
        cmd += ["-headers", headers]
    cmd += ["-i", str(m3u8_path), "-c", "copy"]

    # Only add MP4-specific bits when writing MP4
    if out_path.suffix.lower() == ".mp4":
        cmd += ["-bsf:a", "aac_adtstoasc", "-movflags", "+faststart"]

    cmd += [str(out_path)]
    return run(cmd)

def try_reencode(m3u8_path: Path, out_path: Path, headers: Optional[str]):
    # Re-encode: handles discontinuities/mixed codecs
    cmd = [
        "ffmpeg",
        "-y",
        "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
        "-allowed_extensions", "ALL",
    ]
    if headers:
        cmd += ["-headers", headers]
    cmd += [
        "-i", str(m3u8_path),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(out_path),
    ]
    return run(cmd)

def main():
    ap = argparse.ArgumentParser(description="Merge .m3u8 playlists into complete videos (one per playlist).")
    ap.add_argument("-i", "--input_dir", type=Path, default=Path("."), help="Directory to scan for .m3u8 files (default: current).")
    ap.add_argument("-o", "--output_dir", type=Path, default=Path("./out"), help="Directory for outputs (default: ./out).")
    ap.add_argument("-p", "--pattern", default="*.m3u8", help='Glob pattern for playlists (default: "*.m3u8").')
    ap.add_argument("--reencode", action="store_true", help="If stream copy fails, fall back to re-encode.")
    ap.add_argument("--mp4", dest="mp4", action="store_true", help="Force MP4 container for outputs (default).")
    ap.add_argument("--ts", dest="mp4", action="store_false", help="Use MPEG-TS container (output .ts).")
    ap.add_argument("--headers", default=None, help=r"Optional raw HTTP headers to pass to ffmpeg (use \r\n between lines).")
    ap.set_defaults(mp4=True)  # default to MP4 outputs

    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    m3u8s = sorted(args.input_dir.glob(args.pattern))
    if not m3u8s:
        print(f"No playlists found in {args.input_dir} matching {args.pattern}", file=sys.stderr)
        sys.exit(1)

    failures = 0
    for m3u8 in m3u8s:
        container = "mp4" if args.mp4 else "ts"
        out_path = build_output_name(m3u8, args.output_dir, container=container)
        print(f"\n=== Processing: {m3u8} -> {out_path} ===")
        res = try_stream_copy(m3u8, out_path, args.headers)

        if isinstance(res, subprocess.CalledProcessError):
            print(f"Stream copy failed for {m3u8} (exit {res.returncode}).", file=sys.stderr)

            # If MP4 was requested, try a TS container without re-encode first
            if args.mp4:
                ts_out = build_output_name(m3u8, args.output_dir, container="ts")
                print("Trying MPEG-TS container without re-encode...")
                res2 = run([
                    "ffmpeg", "-y",
                    "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
                    "-allowed_extensions", "ALL",
                    *(["-headers", args.headers] if args.headers else []),
                    "-i", str(m3u8),
                    "-c", "copy",
                    str(ts_out),
                ])
                if not isinstance(res2, subprocess.CalledProcessError):
                    print(f"OK: wrote {ts_out}")
                    continue  # success with TS

            if args.reencode:
                print("Falling back to re-encode (libx264/aac)...")
                final_out = build_output_name(m3u8, args.output_dir, container="mp4")
                res3 = try_reencode(m3u8, final_out, args.headers)
                if isinstance(res3, subprocess.CalledProcessError):
                    print(f"Re-encode also failed for {m3u8} (exit {res3.returncode}).", file=sys.stderr)
                    failures += 1
                else:
                    print(f"OK (re-encoded): wrote {final_out}")
            else:
                failures += 1
        else:
            print(f"OK: wrote {out_path}")

    if failures:
        print(f"\nCompleted with {failures} failure(s).", file=sys.stderr)
        sys.exit(2)
    else:
        print("\nAll playlists processed successfully.")

if __name__ == "__main__":
    main()
