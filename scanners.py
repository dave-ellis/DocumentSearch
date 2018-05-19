# import traceback
import os


class FileScanner:
    def __init__(self, settings):
        self.show_warning_on_open_fail = settings.get('find_in_project_show_warning_on_open_failure', False)
        self.encodings = settings.get('find_in_project_encodings', ["utf-8"])
        self.skip_binary = settings.get('find_in_project_skip_binary_files', True)
        self.show_warning_binary_skip = settings.get('find_in_project_show_warning_on_binary_skip', False)
        self.max_file_size = settings.get('find_in_project_max_file_size_mb', 20)*1000000
        self.show_warning_size_skip = settings.get('find_in_project_show_warning_on_size_skip', False)

        exts_to_ignore = settings.get('find_in_project_ignore_extensions', [])
        self.exts_to_ignore = [x.lower() for x in exts_to_ignore]

        self.warnings = []

    def read_lines(self, filename):
        if self._should_include_file(filename):
            for enc in self.encodings:
                try:
                    # Read file line by line
                    with open(filename, "r", encoding=enc) as f:
                        line_no = 0
                        while True:
                            line_no += 1
                            line = f.readline()
                            if not line:
                                break

                            if self.skip_binary and '\0' in line:
                                if self.show_warning_binary_skip:
                                    self.warnings.append(
                                        "Skipped binary file.")
                                    return
                            else:
                                yield (line_no, line)

                        return

                except UnicodeDecodeError:
                    # Probably using wrong encoding
                    # traceback.print_exc()
                    continue

            print("Unable to read file:", filename)
            if self.show_warning_on_open_fail:
                self.warnings.append(
                    "Failed to open file. This could be due to unknown/unspecified encoding.")

    def _should_include_file(self, filename):
        file_extension = os.path.splitext(filename)[1][1:]
        if file_extension.lower() in self.exts_to_ignore:
            print('Skipping file with ignored extension: ', filename)
            return False

        file_size = os.path.getsize(filename)
        if file_size > self.max_file_size:
            if self.show_warning_size_skip:
                self.warnings.append(
                    "Skipped file due to size (%.2f MB)." % (file_size / 1000000.,))
            print('Skipping file with size larger than maximum: ', filename)
            return False

        return True


class DirScanner:
    def __init__(self, settings):
        self.follow_symlinks = settings.get('find_in_project_follow_sym_links', False)

        dirs_to_ignore = settings.get('find_in_project_ignore_dirs', [])
        self.dirs_to_ignore = [x.lower() for x in dirs_to_ignore]

    def list_tree(self, directory):
        for root, dirs, files in os.walk(directory, followlinks=self.follow_symlinks):
            dirs[:] = [d for d in dirs if self._should_include_dir(d)]
            yield root, dirs, files

    def _should_include_dir(self, directory):
        return directory.lower() not in self.dirs_to_ignore
