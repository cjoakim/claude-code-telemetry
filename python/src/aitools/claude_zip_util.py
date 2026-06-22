# Zip selected contents of a Claude Code .claude directory into python/tmp/.
# Includes agents/, commands/, hooks/, skills/ subdirs and settings*.json files.
# Chris Joakim, 2026

import glob
import os
import traceback
import zipfile

from pathlib import Path


class ClaudeZipUtil:
    """Package a .claude directory's configuration files into a zip archive."""

    INCLUDE_DIRS = ("agents", "commands", "hooks", "skills")

    def __init__(self):
        """Initialize a ClaudeZipUtil instance."""
        pass

    def zip_claude_directory(self, fq_source_dir: str) -> str | None:
        """
        Zip configuration subdirs and settings files from a .claude directory.

        Walks INCLUDE_DIRS under the source directory and adds any settings*.json
        files at the top level. The archive is written to tmp/<basename>.zip
        relative to the current working directory (typically python/).

        Args:
            fq_source_dir: Absolute or user-expandable path to the .claude directory.

        Returns:
            The path to the created zip file, or None if the source is missing
            or an error occurs.
        """
        try:
            source_dir = os.path.abspath(os.path.expanduser(fq_source_dir))
            print(f"ClaudeZipUtil#zip_claude_directory - source_dir -> {source_dir}")
            if not os.path.isdir(source_dir):
                print(f"Source directory does not exist: {source_dir}")
                return None

            target_dir = "tmp"
            base_filename = os.path.basename(source_dir.rstrip(os.sep))
            zip_filename = f"{target_dir}/{base_filename}.zip"
            Path(target_dir).mkdir(parents=True, exist_ok=True)

            file_count = 0
            with zipfile.ZipFile(zip_filename, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for dir_name in self.INCLUDE_DIRS:
                    dir_path = os.path.join(source_dir, dir_name)
                    if not os.path.isdir(dir_path):
                        continue
                    for root, _, files in os.walk(dir_path):
                        for file in files:
                            full_path = os.path.join(root, file)
                            print("including file: ", full_path)
                            arcname = os.path.relpath(full_path, source_dir).replace(os.sep, "/")
                            zf.write(full_path, arcname)
                            file_count += 1

                for settings_file in glob.glob(os.path.join(source_dir, "settings*.json")):
                    arcname = os.path.basename(settings_file)
                    print("including file: ", settings_file)
                    zf.write(settings_file, arcname)
                    file_count += 1

            print(
                f"ClaudeZipUtil#zip_claude_directory - included {file_count} files to {zip_filename}"
            )
            return zip_filename
        except Exception as e:
            print(f"Exception in ClaudeZipUtil#zip_claude_directory: {e}")
            print(traceback.format_exc())
            return None
