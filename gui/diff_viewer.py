"""
GUI Diff Viewer for Python Style Converter with Change Highlighting.
Shows side-by-side diff with old code on left, new code on right.
Highlights specific changes with colors.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import difflib
import re
from typing import List, Tuple
from pathlib import Path


class SimpleDiffViewer:
    """GUI window for displaying side-by-side code diffs with change highlighting."""

    def __init__(self):
        """Initialize the diff viewer window."""
        self.root = tk.Tk()
        self.root.title("Python Style Converter - Diff Viewer")
        self.root.geometry("1200x700")

        # Result variables
        self.result = None  # Will be "apply", "skip", or "quit"
        self.apply_to_all = False

        self.create_widgets()

    def create_widgets(self):
        """Create the GUI widgets."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # File label
        self.file_label = ttk.Label(main_frame, text="", font=("Arial", 12, "bold"))
        self.file_label.pack(fill=tk.X, pady=(0, 10))

        # Changes summary
        changes_frame = ttk.LabelFrame(main_frame, text="Changes to be Applied", padding="5")
        changes_frame.pack(fill=tk.X, pady=(0, 10))

        self.changes_text = tk.Text(changes_frame, height=4, wrap=tk.WORD,
                                   font=("Consolas", 9), bg="#f8f9fa")
        self.changes_text.pack(fill=tk.X)

        # Scrolling instructions
        scroll_info = ttk.Label(main_frame, text="💡 Tip: Use mouse wheel to scroll vertically, Shift + mouse wheel to scroll horizontally",
                               font=("Arial", 9), foreground="gray")
        scroll_info.pack(anchor=tk.W, pady=(5, 0))

        # Code comparison frame
        comparison_frame = ttk.Frame(main_frame)
        comparison_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Configure columns
        comparison_frame.columnconfigure(0, weight=1)
        comparison_frame.columnconfigure(2, weight=1)
        comparison_frame.rowconfigure(1, weight=1)

        # Left side - Original Code
        ttk.Label(comparison_frame, text="Original Code", font=("Arial", 11, "bold")).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 5))

        # Original code frame with scrollbars
        original_frame = ttk.Frame(comparison_frame)
        original_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        original_frame.columnconfigure(0, weight=1)
        original_frame.rowconfigure(0, weight=1)

        self.original_text = tk.Text(
            original_frame, wrap=tk.NONE, font=("Consolas", 10), bg="#fff"
        )
        self.original_text.grid(row=0, column=0, sticky="nsew")

        # Vertical scrollbar for original
        original_v_scroll = ttk.Scrollbar(original_frame, orient="vertical",
                                        command=self.sync_vertical_scroll)
        original_v_scroll.grid(row=0, column=1, sticky="ns")
        self.original_text.configure(yscrollcommand=self.update_vertical_scrollbars)

        # Horizontal scrollbar for original
        original_h_scroll = ttk.Scrollbar(original_frame, orient="horizontal",
                                        command=self.sync_horizontal_scroll)
        original_h_scroll.grid(row=1, column=0, sticky="ew")
        self.original_text.configure(xscrollcommand=self.update_horizontal_scrollbars)

        # Store scrollbar references
        self.original_v_scroll = original_v_scroll
        self.original_h_scroll = original_h_scroll

        # Separator
        ttk.Separator(comparison_frame, orient="vertical").grid(
            row=0, column=1, rowspan=2, sticky="ns", padx=5)

        # Right side - Modified Code
        ttk.Label(comparison_frame, text="After Transformation", font=("Arial", 11, "bold")).grid(
            row=0, column=2, sticky=tk.W, padx=(5, 0))

        # Modified code frame with scrollbars
        modified_frame = ttk.Frame(comparison_frame)
        modified_frame.grid(row=1, column=2, sticky="nsew", padx=(5, 0))
        modified_frame.columnconfigure(0, weight=1)
        modified_frame.rowconfigure(0, weight=1)

        self.modified_text = tk.Text(
            modified_frame, wrap=tk.NONE, font=("Consolas", 10), bg="#fff"
        )
        self.modified_text.grid(row=0, column=0, sticky="nsew")

        # Vertical scrollbar for modified
        modified_v_scroll = ttk.Scrollbar(modified_frame, orient="vertical",
                                        command=self.sync_vertical_scroll)
        modified_v_scroll.grid(row=0, column=1, sticky="ns")
        self.modified_text.configure(yscrollcommand=self.update_vertical_scrollbars)

        # Horizontal scrollbar for modified
        modified_h_scroll = ttk.Scrollbar(modified_frame, orient="horizontal",
                                        command=self.sync_horizontal_scroll)
        modified_h_scroll.grid(row=1, column=0, sticky="ew")
        self.modified_text.configure(xscrollcommand=self.update_horizontal_scrollbars)

        # Store scrollbar references
        self.modified_v_scroll = modified_v_scroll
        self.modified_h_scroll = modified_h_scroll

        # Setup highlighting styles
        self.setup_diff_highlighting()

        # Synchronize scrolling between both text widgets
        self.sync_scrolling()

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)

        # Apply to all checkbox
        self.apply_all_var = tk.BooleanVar()
        ttk.Checkbutton(button_frame, text="Apply this choice to all remaining files",
                       variable=self.apply_all_var).pack(pady=(0, 10))

        # Buttons
        btn_frame = ttk.Frame(button_frame)
        btn_frame.pack()

        ttk.Button(btn_frame, text="✓ Apply Changes",
                  command=self.on_apply).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✗ Skip File",
                  command=self.on_skip).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="⏹ Quit",
                  command=self.on_quit).pack(side=tk.LEFT, padx=5)

    def setup_diff_highlighting(self):
        """Setup text highlighting for diff visualization."""
        # Line number styling
        self.original_text.tag_configure("line_number", background="#f6f8fa", foreground="#586069", font=("Consolas", 9))
        self.modified_text.tag_configure("line_number", background="#f6f8fa", foreground="#586069", font=("Consolas", 9))

        # Line-level changes (lighter backgrounds)
        self.original_text.tag_configure("removed_line", background="#ffecec")
        self.original_text.tag_configure("changed_line", background="#fff5b4")

        self.modified_text.tag_configure("added_line", background="#e6ffed")
        self.modified_text.tag_configure("changed_line", background="#fff5b4")

        # Word-level changes (stronger highlighting for individual words/tokens)
        self.original_text.tag_configure("removed_word", background="#ffcccc", foreground="#d73a49", font=("Consolas", 10, "bold"))
        self.modified_text.tag_configure("added_word", background="#ccffcc", foreground="#28a745", font=("Consolas", 10, "bold"))

        # Legacy tags (keeping for compatibility)
        self.original_text.tag_configure("removed", background="#ffecec", foreground="#d73a49")
        self.modified_text.tag_configure("added", background="#e6ffed", foreground="#28a745")

    def sync_scrolling(self):
        """Synchronize scrolling between both text widgets."""

        def on_mousewheel(event, widget_name):
            """Handle mouse wheel scrolling."""
            # Vertical scrolling (default)
            if event.state == 0:  # No modifier keys
                delta = -1 * (event.delta // 120) if event.delta else (-1 if event.num == 4 else 1)
                self.original_text.yview_scroll(delta, "units")
                self.modified_text.yview_scroll(delta, "units")
            # Horizontal scrolling (with Shift key)
            elif event.state & 0x1:  # Shift key pressed
                delta = -1 * (event.delta // 120) if event.delta else (-1 if event.num == 4 else 1)
                self.original_text.xview_scroll(delta, "units")
                self.modified_text.xview_scroll(delta, "units")

            return "break"  # Prevent default scrolling

        # Bind scroll events for synchronization
        self.original_text.bind("<MouseWheel>", lambda e: on_mousewheel(e, "original"))
        self.modified_text.bind("<MouseWheel>", lambda e: on_mousewheel(e, "modified"))

        # For Linux
        self.original_text.bind("<Button-4>", lambda e: on_mousewheel(e, "original"))
        self.original_text.bind("<Button-5>", lambda e: on_mousewheel(e, "original"))
        self.modified_text.bind("<Button-4>", lambda e: on_mousewheel(e, "modified"))
        self.modified_text.bind("<Button-5>", lambda e: on_mousewheel(e, "modified"))

    def sync_vertical_scroll(self, *args):
        """Synchronize vertical scrolling when scrollbar is used."""
        # Apply the scroll to both text widgets
        self.original_text.yview(*args)
        self.modified_text.yview(*args)

    def sync_horizontal_scroll(self, *args):
        """Synchronize horizontal scrolling when scrollbar is used."""
        # Apply the scroll to both text widgets
        self.original_text.xview(*args)
        self.modified_text.xview(*args)

    def update_vertical_scrollbars(self, *args):
        """Update both vertical scrollbars when text widgets scroll."""
        # Update both scrollbars to show the same position
        self.original_v_scroll.set(*args)
        self.modified_v_scroll.set(*args)

    def update_horizontal_scrollbars(self, *args):
        """Update both horizontal scrollbars when text widgets scroll."""
        # Update both scrollbars to show the same position
        self.original_h_scroll.set(*args)
        self.modified_h_scroll.set(*args)

    def show_diff(self, file_path: Path, original_code: str, modified_code: str,
                  changes_made: List[str]) -> Tuple[bool, bool]:
        """
        Show the diff and wait for user choice.

        Returns:
            Tuple of (apply_changes, apply_to_all)
        """
        # Update file path
        self.file_label.config(text=f"File: {file_path}")

        # Show changes
        self.changes_text.delete(1.0, tk.END)
        for change in changes_made:
            self.changes_text.insert(tk.END, f"• {change}\n")

        # Show code
        self.original_text.delete(1.0, tk.END)
        self.original_text.insert(tk.END, original_code)

        self.modified_text.delete(1.0, tk.END)
        self.modified_text.insert(tk.END, modified_code)

        # Apply syntax highlighting for changes
        self.highlight_changes_in_display(original_code, modified_code)

        # Center and show window
        self.center_window()
        self.root.lift()
        self.root.focus_force()

        # Reset result
        self.result = None

        # Show window and wait for result
        print(f"🎨 Showing GUI for {file_path}")

        # Simple event loop - wait until user clicks a button
        while self.result is None:
            try:
                self.root.update()
            except tk.TclError:
                # Window was closed
                self.result = "quit"
                break

        apply_to_all = self.apply_all_var.get()

        print(f"✅ GUI result: {self.result}, apply_to_all: {apply_to_all}")

        # Hide window
        self.root.withdraw()

        return self.result == "apply", apply_to_all

    def highlight_changes_in_display(self, original_code: str, modified_code: str):
        """Highlight changes in the displayed code."""
        # Split into lines for comparison
        original_lines = original_code.splitlines()
        modified_lines = modified_code.splitlines()

        # Find line-by-line differences
        matcher = difflib.SequenceMatcher(None, original_lines, modified_lines)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                # Lines that were changed - highlight the specific differences
                for orig_idx, mod_idx in zip(range(i1, i2), range(j1, j2)):
                    if orig_idx < len(original_lines) and mod_idx < len(modified_lines):
                        self.highlight_line_changes(
                            original_lines[orig_idx], modified_lines[mod_idx],
                            orig_idx, mod_idx
                        )
            elif tag == 'delete':
                # Lines that were removed
                for orig_idx in range(i1, i2):
                    if orig_idx < len(original_lines):
                        line_start = self.get_line_start_position(self.original_text, orig_idx)
                        line_end = self.get_line_end_position(self.original_text, orig_idx)
                        self.original_text.tag_add("removed_line", line_start, line_end)

            elif tag == 'insert':
                # Lines that were added
                for mod_idx in range(j1, j2):
                    if mod_idx < len(modified_lines):
                        line_start = self.get_line_start_position(self.modified_text, mod_idx)
                        line_end = self.get_line_end_position(self.modified_text, mod_idx)
                        self.modified_text.tag_add("added_line", line_start, line_end)

    def highlight_line_changes(self, original_line: str, modified_line: str,
                             orig_line_idx: int, mod_line_idx: int):
        """Highlight specific word changes within a line."""
        # Tokenize the lines to find word-level differences
        orig_words = re.findall(r'\w+', original_line)
        mod_words = re.findall(r'\w+', modified_line)

        # Find different words
        orig_words_set = set(orig_words)
        mod_words_set = set(mod_words)

        # Words that were removed (in original but not in modified)
        removed_words = orig_words_set - mod_words_set
        # Words that were added (in modified but not in original)
        added_words = mod_words_set - orig_words_set

        # Highlight removed words in original text
        for word in removed_words:
            self.highlight_word_in_line(self.original_text, word, orig_line_idx, "removed_word")

        # Highlight added words in modified text
        for word in added_words:
            self.highlight_word_in_line(self.modified_text, word, mod_line_idx, "added_word")

    def highlight_word_in_line(self, text_widget: tk.Text, word: str, line_idx: int, tag: str):
        """Highlight a specific word in a specific line of a text widget."""
        line_start = f"{line_idx + 1}.0"
        line_end = f"{line_idx + 1}.end"

        # Get the line content
        line_content = text_widget.get(line_start, line_end)

        # Find all occurrences of the word in the line
        start_pos = 0
        while True:
            word_pos = line_content.find(word, start_pos)
            if word_pos == -1:
                break

            # Check if it's a whole word (not part of another word)
            if (word_pos == 0 or not line_content[word_pos - 1].isalnum()) and \
               (word_pos + len(word) >= len(line_content) or not line_content[word_pos + len(word)].isalnum()):

                word_start = f"{line_idx + 1}.{word_pos}"
                word_end = f"{line_idx + 1}.{word_pos + len(word)}"
                text_widget.tag_add(tag, word_start, word_end)

            start_pos = word_pos + 1

    def get_line_start_position(self, text_widget: tk.Text, line_idx: int) -> str:
        """Get the start position of a line in a text widget."""
        return f"{line_idx + 1}.0"

    def get_line_end_position(self, text_widget: tk.Text, line_idx: int) -> str:
        """Get the end position of a line in a text widget."""
        return f"{line_idx + 1}.end"

    def center_window(self):
        """Center the window on screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def on_apply(self):
        """Handle Apply button click."""
        print("🟢 User clicked Apply")
        self.result = "apply"

    def on_skip(self):
        """Handle Skip button click."""
        print("🟡 User clicked Skip")
        self.result = "skip"

    def on_quit(self):
        """Handle Quit button click."""
        if messagebox.askyesno("Quit", "Are you sure you want to quit?"):
            print("🔴 User clicked Quit")
            self.result = "quit"


# Global GUI instance to reuse
_gui_instance = None

def show_diff_gui(file_path: Path, original_code: str, modified_code: str,
                  changes_made: List[str]) -> Tuple[bool, bool]:
    """
    Show GUI diff viewer and return user choice.

    Args:
        file_path: Path to the file being modified
        original_code: Original source code
        modified_code: Modified source code
        changes_made: List of changes that were made

    Returns:
        Tuple of (apply_changes, apply_to_all)
    """
    global _gui_instance

    try:
        # Create GUI instance if needed
        if _gui_instance is None:
            print("🔧 Creating new GUI instance")
            _gui_instance = SimpleDiffViewer()

        # Show the diff
        result = _gui_instance.show_diff(file_path, original_code, modified_code, changes_made)

        return result

    except Exception as e:
        print(f"❌ GUI Error: {e}")
        import traceback
        traceback.print_exc()

        # Clean up broken GUI instance
        if _gui_instance:
            try:
                _gui_instance.root.destroy()
            except:
                pass
            _gui_instance = None

        raise e


def cleanup_gui():
    """Clean up GUI resources."""
    global _gui_instance
    if _gui_instance:
        try:
            _gui_instance.root.destroy()
        except:
            pass
        _gui_instance = None