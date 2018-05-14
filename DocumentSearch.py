import time
import queue
import threading
import os
import traceback
import re
import mimetypes

import sublime_plugin
import sublime

from . import filesearcher
from . import resultbuffer
from . import tfidf_search
from . import pagerank


# Split terms by non-word characters
TERM_SPLITTER = re.compile(r'\W+', re.UNICODE)

#  Page references are any word characters surrounded by double square brackets
DEFAULT_PAGE_REF_PATTERN = r'(?:\[\[)(\w+)(?:\]\])'


class DocumentSearch(sublime_plugin.WindowCommand):
    """Document Search - search in all files in project.

    * Executes the search in the background
    * Search results displayed in a scratch view
    """

    def __init__(self, view):
        sublime_plugin.TextCommand.__init__(self, view)
        settings = sublime.load_settings('DocumentSearch.sublime-settings')
        self.excessive_hits_count = settings.get('document_search_excessive_hits_count', 5000)

        exts_to_ignore = settings.get('document_search_ignore_extensions', [])
        self.exts_to_ignore = [x.lower() for x in exts_to_ignore]
        dirs_to_ignore = settings.get('document_search_ignore_dirs', [])
        self.dirs_to_ignore = [x.lower() for x in dirs_to_ignore]

        page_ref_pattern = settings.get("document_search_page_ref_pattern", DEFAULT_PAGE_REF_PATTERN)
        self.page_ref_matcher = re.compile(page_ref_pattern, re.UNICODE)

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

        self._idf_table = tfidf_search.TfIdfTable()
        self._graph = pagerank.Graph()

        for folder in self.search_dirs:
            print("Scanning directory:", folder)
            for dirname, _, files in self.list_dir_tree(folder):                
                if dirname.lower() in self.dirs_to_ignore:
                    continue

                for file in files:
                    file_ext = os.path.splitext(file)[1][1:]
                    if file_ext.lower() in self.exts_to_ignore:
                        continue

                    type, encoding = mimetypes.guess_type(file)
                    if type is not None and not type.startswith('text'):
                        continue

                    self.scan_file(dirname, file)

        print("Scanned", len(self._idf_table), "documents")

    def is_binary_string(self, file):
        textchars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})
        bytes = open(file, 'rb').read(1024)
        return  lambda bytes: bool(bytes.translate(None, textchars))

    def scan_file(self, dirname, file):
        filename = os.path.join(dirname, file)
        pagename = os.path.splitext(file)[0]
        try:
            # Scan contents
            terms = []
            page_refs = []
            with open(filename, "rt") as f:
                while True:
                    try:
                        line = f.readline()
                        if not line:
                            break

                        terms.extend(self._extract_terms(line))
                        page_refs.extend(self._extract_page_refs(line))
                    except UnicodeDecodeError:
                        print('Failed to read line in', filename)

            # Append to IDF
            self._idf_table.append_document(filename, terms)

            # Append to PageRank
            node = self._graph.add_node_with_refs(pagename, *page_refs)
            node.filename = filename

        except:
            print("Unable to scan file:", filename)
            traceback.print_exc()

    def list_dir_tree(self, directory):
        for dir, dirnames, files in os.walk(directory):
            dirnames[:] = [dirname for dirname in dirnames]
            yield dir, dirnames, files

    def _extract_terms(self, line):
        return [x.lower() for x in TERM_SPLITTER.split(line) if x != '']

    def _extract_page_refs(self, line):
        return self.page_ref_matcher.findall(line)

    def prepare_search_text(self):
        """Prepare the initial search text"""

        # If text is selected then return that
        view = sublime.active_window().active_view()
        for region in view.sel():
            if not region.empty():
                # Selected text
                txt = view.substr(region)
                if "\n" not in txt:
                    return txt

        # Else use previous search text
        try:
            return self.search_text
        except AttributeError:
            # Otherwise just use empty string
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

        # Calculate term scores
        term_scores = self._idf_table.search(search_text)
        sum_scores = sum(score for _, score in term_scores)
        # print('sum_scores:', sum_scores, 'term_scores:', term_scores)

        # Calculate rank scores
        page_rank = pagerank.PageRank(self._graph)
        rank_scores, iteration_count = page_rank.calculate()

        # Prepare mapping of matched filenames to rank value
        sum_ranks = 0.0
        rank_mappings = {}
        for pagename, rank in rank_scores:
            node = self._graph.get_node_by_id(pagename)
            if hasattr(node, 'filename'):
                sum_ranks += rank
                rank_mappings[node.filename] = rank
            else:
                print("Missing filename for page", pagename)
        # print('sum_ranks:', sum_ranks, 'rank_mappings:', rank_mappings)

        # Prepare list of files with match value = weighted average of score and rank
        scores_weight = 1.0/2.0*sum_scores
        ranks_weight = 1.0/2.0*sum_ranks
        match_scores = list((filename, scores_weight*score + ranks_weight*rank_mappings[filename])
                            for filename, score in term_scores
                            if filename in rank_mappings)
        # print('match_scores:', match_scores)

        match_scores.sort(reverse=True, key=lambda x: x[1])
        matching_files = list(match[0] for match in match_scores)

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
