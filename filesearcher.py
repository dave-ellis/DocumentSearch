import os
import threading
import collections
import time

import sublime


class FileSearcherThread(threading.Thread):
   """
   Search directories recursively in separate thread and push results onto a
   queue.
   """
   def __init__(self, paths, target_string, result_queue):
      super().__init__()
      self._stop_thread = threading.Event()
      self.paths = paths
      self.target_string = target_string
      self.result_queue = result_queue

      settings = sublime.load_settings('FindInProject.sublime-settings')
      self.exts_to_ignore = settings.get('find_in_project_ignore_extensions', [])
      self.exts_to_ignore = [x.lower() for x in self.exts_to_ignore]
      self.dirs_to_ignore = settings.get('find_in_project_ignore_dirs', [])
      self.dirs_to_ignore = [x.lower() for x in self.dirs_to_ignore]
      self.encodings = settings.get('find_in_project_encodings', ["utf-8"])
      self.skip_binary = settings.get('find_in_project_skip_binary_files', True)
      self.max_file_size = settings.get('find_in_project_max_file_size_mb', 20)*1000000
      self.follow_symlinks = settings.get('find_in_project_follow_sym_links', False)
      self.max_line_len = settings.get('find_in_project_max_line_len', 100)
      self.show_warning_on_open_fail = settings.get('find_in_project_show_warning_on_open_failure', False)
      self.show_warning_size_skip = settings.get('find_in_project_show_warning_on_size_skip', False)

   def stop(self):
      """
      Stop the thread after it is done searching the current file. The thread
      waits until the result queue is empty, then it terminates.
      """
      self._stop_thread.set()

   def run(self):
      """
      Override the run method from threading.Thread to do a search then the
      thread is tarted. This should not be called directly obviously.
      """
      for path in self.paths:
         for root, dirs, files in os.walk(path, followlinks=self.follow_symlinks):
            # Remove the excluded dirs in-place so os.walk() won't recurse into them
            dirs[:] = [d for d in dirs if d.lower() not in self.dirs_to_ignore]
            for file in files:
               if self._stop_requested():
                  self.result_queue.join()
                  return

               file_ext = os.path.splitext(file)[1][1:]
               if file_ext.lower() in self.exts_to_ignore:
                  continue

               filepath = os.path.join(root, file)
               file_size = os.path.getsize(filepath)
               if file_size > self.max_file_size:
                  result = collections.OrderedDict()
                  if self.show_warning_size_skip:
                     result[0] = "Skipped file due to size (%.2f MB)" % (file_size/1000000., )
               else:
                  result = self._search_file(filepath)

               if len(result):
                  ret = {"filepath": filepath, "result": result}
                  self.result_queue.put(ret)

      # Wait until all results have been read from the queue - then terminate
      self.result_queue.join()

   def _stop_requested(self):
      """
      Check if stop has been requested.
      """
      flag = self._stop_thread.wait(0)
      return flag

   def _search_file(self, path):
      """
      Search a file for the target file. Skip binaries if configured.
      """
      ret = collections.OrderedDict()
      target_len = len(self.target_string)
      for enc in self.encodings:
         try:
            with open(path, "r", encoding=enc) as target_file:
               for line_num, line_content in enumerate(target_file, start=1):
                  # Check for binary file
                  if self.skip_binary and '\0' in line_content:
                     return collections.OrderedDict()

                  # Search line for target string
                  if self.target_string.lower() in line_content.lower():
                     if len(line_content) > (self.max_line_len + target_len):
                        line_content = self._limit_line(line_content)
                     ret[line_num] = line_content
         except:
            # Probably using wrong encoding
            continue
         else:
            return ret

      if self.show_warning_on_open_fail:
         ret[0] = "Failed to open file. This could be due to unknown/unspecified encoding."

      return ret

   def _limit_line(self, line):
      """
      Limit the provided line according to the settings.
      """
      single_side_len = int(self.max_line_len/2)
      loc = line.lower().find(self.target_string)

      start = loc - single_side_len
      if start < 0:
         start = 0

      end = loc + len(self.target_string)
      end = end + single_side_len
      if (end >= len(line)):
         end = len(line)-1

      limited_line = ""
      if start != 0:
         limited_line = limited_line + "[…]"

      limited_line = limited_line + line[start:end]
      if end != len(line)-1:
         limited_line = limited_line + "[…]"

      return limited_line
