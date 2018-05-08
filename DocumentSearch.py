import time
import queue
import threading
import os
import glob
import traceback
import re

import sublime_plugin
import sublime

from . import filesearcher
from . import resultbuffer
from . import tfidf_search

class DocumentSearch(sublime_plugin.WindowCommand):
    """Document Search - search in all files in project.

    * Executes the search in the background
    * Search results displayed in a scratch view
    """


    def __init__(self, view):
        sublime_plugin.TextCommand.__init__(self, view)
        settings = sublime.load_settings('DocumentSearch.sublime-settings')
        self.excessive_hits_count = settings.get('document_search_excessive_hits_count', 5000)

    def run(self):
        """Show search panel"""

        print("Running document search...")

        self.search_dirs = self.list_search_dirs()
        self.start_scan()

        # Initial search to selection...
        search_text = self.prepare_search_text()

        # Search panel
        win = sublime.active_window()
        win.show_input_panel("Search in documents:", search_text, self.run_search, None, None)

    def start_scan(self):
        """Start the document scan in the background"""

        self.scanning_thread = threading.Thread(target=self.scan_project, args=())
        self.scanning_thread.start()

    def scan_project(self):
        """Scan the documents"""

        self.table = tfidf_search.TfIdfTable()

        for folder in self.search_dirs:
            print("Scanning directory:", folder)
            for dirname, _, files in self.list_dir_tree(folder):
                for file in files:
                    try:
                        filename = os.path.join(dirname, file)
                        words = self.parse_document(filename)
                        self.table.append_document(filename, words)
                    except Exception as e:
                        print("Unable to parse file:", filename)
                        traceback.print_exc()

        print("Scanned", self.table.size(), "documents")

    def list_dir_tree(self, directory):
        for dir, dirnames, files in os.walk(directory):
            dirnames[:] = [dirname for dirname in dirnames]
            yield dir, dirnames, files

    def parse_document(self, file):
        words = []
        with open(file, "r") as f:
            for line in f:
                terms = self.extract_terms(line)
                words.extend(terms)

        return words

    def extract_terms(self, line):
        return [x.lower() for x in re.compile(r'\W+', re.UNICODE).split(line) if x != '']

    def prepare_search_text(self):
        """Prepare the initial search text"""

        view = sublime.active_window().active_view()
        for region in view.sel():
            if not region.empty():
                # Selected text
                txt = view.substr(region)
                if "\n" not in txt:
                    return txt

        if self.search_text:
            return self.search_text
        else:
            return ""

    def run_search(self, search_text):
        """Search in the project files for the specified text"""

        if len(search_text) == 0:
            return

        # Wait for scan to complete
        self.scanning_thread.join()

        print("Searching for:", search_text)
        self.search_text = search_text

        # Get active window and view
        win = sublime.active_window()
        view = win.active_view()


        # Init member vars for new search
        self.result_queue = queue.Queue()
        self.num_hits = 0
        self.num_file_hits = 0
        self.last_status_update = 0
        self.search_cancelled = False
        self.files_searched = 0
        self.search_start_time = time.time()

        # Initialize result buffer/view
        self.result_buffer = resultbuffer.ResultBuffer(win, search_text)

        # Start search thread
        matching_files = self.table.search(search_text)
        self.search_thread = filesearcher.FileSearcherThread(matching_files, search_text, self.result_queue)
        self.search_thread.start()

        # Display results asynchronously
        sublime.set_timeout_async(self.display_search_results, 1)

    def list_search_dirs(self):
        """Add all project dirs"""

        search_dirs = []

        win = sublime.active_window()
        for folder in win.folders():
            search_dirs.append(folder)

        return search_dirs

    def display_search_results(self):
        """Handle search results that the search thread places on the result queue"""
        
        while self.search_thread.isAlive() or (self.result_queue.empty() == False):
            self.update_status()

            # Check if result buffer has been closed - in this case we cancel the
            # search.
            if self.result_buffer.is_closed():
                self.search_thread.stop()
                self.search_cancelled = True
                break

            # If there are any results
            if not self.result_queue.empty():
                result = self.result_queue.get()

                # Update number of hits but ensure it does not include warning/error strings
                if "result" in result and len(result["result"]):
                    if 0 not in result["result"]:
                        self.num_hits = self.num_hits + len(result["result"])
                        self.num_file_hits = self.num_file_hits + 1

                # Update number of files searched
                if "files_searched" in result:
                    self.files_searched = result["files_searched"]

                # If we reach excessive limit start dropping results and stop search thread
                if (self.excessive_hits_count != 0) and (self.num_hits > self.excessive_hits_count):
                    self.search_thread.stop()
                    self.search_cancelled = True
                    break

                # Update result view
                if "result" in result:
                    self.result_buffer.insert_result(result)

                self.result_queue.task_done()

        # We are done searching
        self.set_final_status()

    def update_status(self):
        """
        Update text in status bar
        """
        cur_time = time.time()
        if cur_time > (self.last_status_update + 0.2):
            self.last_status_update = cur_time
            cur_search_time = cur_time - self.search_start_time
            win = sublime.active_window()
            status_msg = "DocumentSearch: Searching project"
            status_msg += " [%i hits across %i files so far]" % (self.num_hits, self.num_file_hits)
            status_msg += " [%i files searched in %.1f seconds]" % (self.files_searched, cur_search_time)
            win.status_message(status_msg)

    def set_final_status(self):
        """
        Set final text in status bar
        """
        win = sublime.active_window()
        if self.search_cancelled:
            win.status_message("DocumentSearch: Search cancelled (due to close or excessive number of hits)")
        else:
            cur_search_time = time.time() - self.search_start_time
            status_msg = "DocumentSearch: Search finished"
            status_msg += " [%i hits across %i files]" % (self.num_hits, self.num_file_hits)
            status_msg += " [%i files searched in %.1f seconds]" % (self.files_searched, cur_search_time)
            win.status_message(status_msg)
