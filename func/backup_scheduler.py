#!/usr/bin/env python3

import sqlite3
import argparse
import datetime
import os
import shutil
import tarfile
import tempfile
import sys


def backup_one(src, dest):
    conn_src = sqlite3.connect(src)
    conn_dest = sqlite3.connect(dest)
    try:
        conn_src.backup(conn_dest, pages=0, progress=None)
        cur = conn_dest.cursor()
        cur.execute('PRAGMA integrity_check;')
        res = cur.fetchone()
        if not res or res[0] != 'ok':
            raise RuntimeError(f"Integrity check failed for {dest}: {res}")
    finally:
        conn_src.close()
        conn_dest.close()


def make_snapshot(db_dir, backup_dir, db_list=None):
    ts = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    snap_dir = os.path.join(backup_dir, ts)
    os.makedirs(snap_dir, exist_ok=True)

    if db_list is None:
        db_list = [os.path.join(db_dir, f) for f in os.listdir(db_dir) if f.endswith('.db')]

    copied = []
    for src in db_list:
        if not os.path.exists(src):
            print(f"Warning: DB not found: {src}")
            continue
        name = os.path.basename(src)
        dest = os.path.join(snap_dir, name)
        print(f"Backing up {src} -> {dest}")
        backup_one(src, dest)
        copied.append(dest)

    return snap_dir, copied


def archive_snapshot(snap_dir, backup_dir, compress='gz'):
    base = os.path.basename(snap_dir.rstrip('/'))
    archive_name = os.path.join(backup_dir, f"backup_{base}.tar.{compress}")
    print(f"Creating archive: {archive_name}")
    with tarfile.open(archive_name, f"w:{compress}") as tar:
        tar.add(snap_dir, arcname=base)
    shutil.rmtree(snap_dir)
    return archive_name


def rotate_backups(backup_dir, keep_days=30):
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=keep_days)
    removed = []
    for fname in os.listdir(backup_dir):
        if not fname.startswith('backup_') or (not fname.endswith('.tar.gz') and not fname.endswith('.tar')):
            continue
        full = os.path.join(backup_dir, fname)
        mtime = datetime.datetime.utcfromtimestamp(os.path.getmtime(full))
        if mtime < cutoff:
            print(f"Removing old backup: {full}")
            os.remove(full)
            removed.append(full)
    return removed


def run_backup(db_dir=None, backup_dir=None, keep_days=14, db_list=None):
    db_dir = os.path.abspath(db_dir or os.environ.get('DB_DIR', './'))
    backup_dir = os.path.abspath(backup_dir or os.environ.get('BACKUP_DIR', './backups'))
    os.makedirs(backup_dir, exist_ok=True)

    if db_list:
        db_list = [os.path.abspath(p) for p in db_list]

    snap_dir, copied = make_snapshot(db_dir, backup_dir, db_list=db_list)
    archive = archive_snapshot(snap_dir, backup_dir, compress='gz')
    rotate_backups(backup_dir, keep_days=keep_days)
    return archive


def main():
    parser = argparse.ArgumentParser(description='Backup SQLite DBs (safe online backup)')
    parser.add_argument('--db-dir', default=os.environ.get('DB_DIR', './'), help='Directory containing .db files')
    parser.add_argument('--backup-dir', default=os.environ.get('BACKUP_DIR', './backups'), help='Directory to store backups')
    parser.add_argument('--keep-days', type=int, default=int(os.environ.get('KEEP_DAYS', '14')),
                        help='Number of days to keep backup archives')
    parser.add_argument('--db', action='append', help='Specific DB file(s) to backup (path). Can be passed multiple times')
    args = parser.parse_args()

    try:
        archive = run_backup(db_dir=args.db_dir, backup_dir=args.backup_dir, keep_days=args.keep_days, db_list=args.db)
        print("Archive created:", archive)
        print("Backup completed successfully")
    except Exception as e:
        print("Backup failed:", str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
