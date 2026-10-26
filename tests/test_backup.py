import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from lab import validate_backup


class BackupTests(unittest.TestCase):
    def fixture(self, out, name="./filedir/example.txt", symlink=False):
        (out / "database.sql").write_text("SELECT 1;\n")
        with tarfile.open(out / "moodledata.tar.gz", "w:gz") as archive:
            member = tarfile.TarInfo(name)
            if symlink:
                member.type = tarfile.SYMTYPE
                member.linkname = "/etc/passwd"
                archive.addfile(member)
            else:
                member.size = 4
                archive.addfile(member, io.BytesIO(b"test"))
        manifest = {"format": 1, "sha256": {name: hashlib.sha256((out / name).read_bytes()).hexdigest()
                                             for name in ["database.sql", "moodledata.tar.gz"]}}
        (out / "manifest.json").write_text(json.dumps(manifest))

    def test_valid_backup_and_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            self.fixture(out)
            self.assertEqual(validate_backup(out)["format"], 1)
            (out / "database.sql").write_text("corrupted")
            with self.assertRaisesRegex(ValueError, "Checksum"):
                validate_backup(out)

    def test_unsafe_archive_is_rejected_before_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            for name, symlink in [("../escape", False), ("/absolute", False), ("link", True)]:
                out = Path(directory)
                self.fixture(out, name, symlink)
                with self.assertRaisesRegex(ValueError, "no permitida"):
                    validate_backup(out)
