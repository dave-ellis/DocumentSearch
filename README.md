# Document Search

(based on FindInProject)

Searches all documents in a project using tf-idf and displays the results in scratch view.


## Installation

Install it from the [Package Control Web Site](https://packagecontrol.io/)

1. Run `Package Control: Install Package`
2. Search for `DocumentSearch` and install.

To install from GitHub do the following:

1. Select the menu option `Preferences -> Browse Packages...`
2. Clone or download git repository into a directory named `DocumentSearch` under the packages folder


## Configuration

Configuration is available through the menu option `Preferences -> Package Settings -> DocumentSearch`:
* Search settings, including:
    * Supported File Encodings
    * Maximum line length in result view
    * Excluded Directories and file extensions
    * Maximum File size
    * Maximum match count
* Key bindings
* Result view color scheme


## Usage

In normal contexts using the default key bindings:

Shortcut | Command | Description
--- | --- | ---
`ctrl`+`alt`+`f` | document_search | Opens DocumentSearch input panel

In a result view using the default key bindings:

Shortcut | Command | Description
--- | --- | ---
`up` / `down` | document_search_next_line | Browse back/forward in results
`Pageup` / `Pagedown` | document_search_next_file | Browse back/forward between files
`Left` / `Right` | document_search_fold | Fold/Unfold results within the selected file
`Enter` | document_search_open_result | Open currently selected result
