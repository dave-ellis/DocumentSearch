# FindInProject
Text search plugin for Sublime Text 3 projects. This is an alternative to the default "Find in files" command that comes with Sublime Text. It includes an interactive result view and a configurable search thread that runs in the background.

![example.gif](https://raw.githubusercontent.com/Wramberg/FindInProject/master/example.gif "Example of use")

## Installation
The plugin is tested on Windows and Linux but should also work on macOS. To install it from https://packagecontrol.io/ do the following:

1. Open the command palette and find "Package Control: Install Package"
2. Search for FindInProject and install.

To install from GitHub do the following:

1. Locate Sublime Text packages folder by choosing *Preferences -> Browse Packages...* in the menu
2. Clone or download git repository into a new folder named "FindInProject" under the packages folder

## Configuration
All configuration is available through the *Preferences->Package Settings->FindInProject* menu. This includes

* Default settings which can be copied into the user settings and then changed
* Default keymap which can overridden in the user keymap
* Default color scheme which can be copied into the user color scheme and then changed

The settings include options for

* Encodings to try
* Maximum line length in result view
* Directories and file extensions to ignore
* File sizes to ignore
* Excessive hit count (to cancel large searches)
* and more (descriptive comments are included in the settings file)

## Usage
In normal contexts (using the default keymap) the following shortcut is available.

Shortcut | Command | Description
--- | --- | ---
`ctrl`+`shift`+`f` | find_in_project | Opens FindInProject input panel

When in a result view (using the default keymap) the following shortcuts are available.

Shortcut | Command | Description
--- | --- | ---
`up` / `down` | find_in_project_next_line | Browse back/forward in results
`Pageup` / `Pagedown` | find_in_project_next_file | Browse back/forward between files
`Left` / `Right` | find_in_project_fold | Fold/Unfold results within the selected file
`Enter` | find_in_project_open_result | Open currently selected result

For details see the keymap file available through the *Preferences->Package Settings->FindInProject* menu.
