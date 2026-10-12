#!/usr/bin/env python3
"""Write ``_metadata`` / ``_common_metadata`` for a folder of parquet files.

With these two files a folder of per-input parquet files (one per nanoML ROOT
file, see condor/submit_parquet.sh) reads as a single dataset::

    ak.from_parquet("/path/to/folder")            # awkward: uses _metadata
    pq.ParquetDataset("/path/to/folder")           # pyarrow

The folder may be a local directory or an XRootD URL (root://host//path, e.g.
the CMU T3). Row groups can only be merged across identical schemas, so every
file is compared with the first one; files that differ are listed and the run
fails (``--skip-bad`` writes the metadata for the matching files only). Files
are ordered naturally (rep0, rep1, ..., rep10) so the row order is stable.

    python3 parquet_folder_metadata.py root://cmsdata.phys.cmu.edu//store/group/.../dataset
    python3 parquet_folder_metadata.py /local/dir --check-only

Needs pyarrow and, for root:// folders, the XRootD python bindings plus
fsspec-xrootd (both in the LCG_109 view) and a valid VOMS proxy.
"""
import argparse
import fnmatch
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import pyarrow.parquet as pq

XROOTD_PREFIX = "root://"
META, COMMON = "_metadata", "_common_metadata"


def natural_key(name):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name)]


class LocalFolder:
    def __init__(self, path):
        self.path = pathlib.Path(path)
        if not self.path.is_dir():
            raise NotADirectoryError(str(self.path))
        self.url = str(self.path)

    def list_parquet(self, pattern):
        files = [(p.name, p.stat().st_size) for p in self.path.iterdir()
                 if p.is_file() and fnmatch.fnmatch(p.name, pattern)
                 and p.name not in (META, COMMON)]
        return sorted(files, key=lambda t: natural_key(t[0]))

    def read_metadata(self, name):
        return pq.read_metadata(self.path / name)

    def put(self, local_file, name):
        shutil.copyfile(local_file, self.path / name)


class XRootDFolder:
    def __init__(self, url):
        from XRootD import client
        host, sep, path = url[len(XROOTD_PREFIX):].partition("/")
        if not host or not sep or not path.strip("/"):
            raise ValueError(f"malformed XRootD URL {url!r}: expected root://host//path")
        self.host = XROOTD_PREFIX + host
        self.path = "/" + path.strip("/")
        self.url = f"{self.host}/{self.path}"
        self._fs = client.FileSystem(self.host)

    def list_parquet(self, pattern):
        from XRootD.client.flags import DirListFlags
        status, listing = self._fs.dirlist(self.path, DirListFlags.STAT)
        if not status.ok:
            raise OSError(f"cannot list {self.url}: {status.message}")
        files = [(e.name, e.statinfo.size) for e in listing
                 if fnmatch.fnmatch(e.name, pattern) and e.name not in (META, COMMON)]
        return sorted(files, key=lambda t: natural_key(t[0]))

    def read_metadata(self, name):
        import fsspec  # fsspec-xrootd registers the root:// protocol
        with fsspec.open(f"{self.url}/{name}", "rb") as f:
            return pq.read_metadata(f)

    def put(self, local_file, name):
        subprocess.run(["xrdcp", "-f", str(local_file), f"{self.url}/{name}"], check=True)


def open_folder(path):
    return XRootDFolder(path) if path.startswith(XROOTD_PREFIX) else LocalFolder(path)


def schema_diff(ref, other):
    """Human-readable differences between two arrow schemas."""
    ref_fields = {f.name: f.type for f in ref}
    oth_fields = {f.name: f.type for f in other}
    out = []
    for name in ref_fields.keys() - oth_fields.keys():
        out.append(f"missing column {name}")
    for name in oth_fields.keys() - ref_fields.keys():
        out.append(f"extra column {name}")
    for name in ref_fields.keys() & oth_fields.keys():
        if ref_fields[name] != oth_fields[name]:
            out.append(f"{name}: {oth_fields[name]} != {ref_fields[name]}")
    return out or ["same columns, different parquet schema details"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n".join(__doc__.split("\n\n")[1:]))
    ap.add_argument("folder", help="local directory or root://host//path")
    ap.add_argument("--pattern", default="*.parquet", help="files to include (default: *.parquet)")
    ap.add_argument("--check-only", action="store_true", help="only list files and compare schemas")
    ap.add_argument("--skip-bad", action="store_true",
                    help="write the metadata for the files matching the first file's schema, "
                         "instead of failing when some file differs")
    args = ap.parse_args()

    folder = open_folder(args.folder)
    files = folder.list_parquet(args.pattern)
    if not files:
        sys.exit(f"no files matching {args.pattern!r} in {folder.url}")
    print(f"{len(files)} parquet files in {folder.url}")

    ref_md = ref_schema = ref_name = None
    collector, bad = [], []
    rows = row_groups = nbytes = 0
    for name, size in files:
        md = folder.read_metadata(name)
        if ref_md is None:
            ref_md, ref_name = md, name
            ref_schema = md.schema.to_arrow_schema()
        elif not md.schema.equals(ref_md.schema):
            bad.append((name, schema_diff(ref_schema, md.schema.to_arrow_schema())))
            continue
        md.set_file_path(name)  # relative to the folder, as _metadata readers expect
        collector.append(md)
        rows += md.num_rows
        row_groups += md.num_row_groups
        nbytes += size
        print(f"  {name}: {md.num_rows} rows, {md.num_row_groups} row group(s), {size / 1e6:.1f} MB")

    print(f"total: {len(collector)} files, {rows} rows, {row_groups} row groups, "
          f"{nbytes / 1e9:.2f} GB, {ref_md.num_columns} columns")
    if bad:
        print(f"\n{len(bad)} file(s) whose schema differs from {ref_name}:")
        for name, diff in bad:
            print(f"  {name}:")
            for line in diff[:20]:
                print(f"    {line}")
        if not args.skip_bad:
            sys.exit("schemas differ; fix or re-convert those files, or pass --skip-bad")
    if args.check_only:
        return

    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        pq.write_metadata(ref_schema, tmp / COMMON)
        pq.write_metadata(ref_schema, tmp / META, metadata_collector=collector)
        folder.put(tmp / COMMON, COMMON)
        folder.put(tmp / META, META)
    print(f"wrote {folder.url}/{META} ({len(collector)} files, {rows} rows) and {COMMON}")


if __name__ == "__main__":
    main()
