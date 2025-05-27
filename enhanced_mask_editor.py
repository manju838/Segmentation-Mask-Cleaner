import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox, ttk
import numpy as np
import cv2
from PIL import Image, ImageTk
import os
import glob
import re

class MaskEditorApp:
    def __init__(self, root):
        """
        Initialize the Binary Mask Editor application with folder navigation.
        
        Args:
            root: The tkinter root window.
        """
        self.root = root
        self.root.title("Binary Mask Editor Tool - Enhanced")
        self.root.geometry("1200x800")
        
        # Folder and file management variables
        self.image_folder = None
        self.mask_folder = None
        self.output_folder = None
        self.image_files = []
        self.current_image_index = 0
        self.auto_save = True
        
        # Variables
        self.image_path = None
        self.mask_path = None
        
        # Set image and masks
        self.original_image = None
        self.mask_image = None
        self.display_image = None
        self.current_tool = "brush"
        self.brush_size = 10
        self.is_drawing = False
        self.last_x, self.last_y = 0, 0
        self.undo_stack = []
        self.redo_stack = []
        self.overlay_alpha = 0.5
        
        self.show_mask_only = False
        self.show_image_only = False
        
        self.selection_start = None
        self.selection_rect = None
        self.selected_region = None
        self.cursor_indicator = None
        
        # Polygon selection variables
        self.polygon_points = []
        self.polygon_lines = []
        self.polygon_vertices = []
        self.temp_line = None
        self.polygon_closed = False
        self.active_vertex = None
        self.hover_vertex = None
        self.polygon_region = None
        self.close_indicator = None
        self.close_option_active = False
        
        # Panning variables
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.panning = False
        
        # Update control flags to prevent recursion
        self._updating_display = False
        self._updating_selections = False
        self._highlighting = False
        
        # Show folder setup dialog at startup
        self.setup_folders()
        
        # Create GUI elements
        self.create_menu()
        self.create_toolbar()
        self.create_navigation_bar()
        self.create_canvas()
        self.create_statusbar()
        
        # Key bindings
        self.root.bind("<Control-z>", self.undo)
        self.root.bind("<Control-y>", self.redo)
        self.root.bind("<Left>", self.previous_image)
        self.root.bind("<Right>", self.next_image)
        self.root.bind("<Control-s>", self.save_current_mask)
        self.root.bind("<Configure>", self.on_window_resize)
        self.root.bind("<Escape>", self.escape_pressed)
        
        self.root.focus_set()
        
        # Load first image if folders were set up successfully
        if self.image_files:
            self.load_current_image()
        else:
            self.status_label.config(text="No images found. Use File > Setup Folders to configure directories.")

    def setup_folders(self):
        """Setup folder paths for images, masks, and output."""
        setup_dialog = FolderSetupDialog(self.root)
        result = setup_dialog.show()
        
        if result:
            self.image_folder = result['image_folder']
            self.mask_folder = result['mask_folder']
            self.output_folder = result['output_folder']
            self.auto_save = result['auto_save']
            
            # Find all image files
            self.find_image_files()
            
            if not self.image_files:
                messagebox.showwarning("No Images", "No image files found in the selected folder.")
        else:
            # User cancelled setup
            self.image_folder = None
            self.mask_folder = None
            self.output_folder = None
            self.image_files = []

    def find_image_files(self):
        """Find all image files in the image folder and sort them."""
        if not self.image_folder:
            return
        
        # Supported image extensions
        extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff']
        
        self.image_files = []
        for ext in extensions:
            pattern = os.path.join(self.image_folder, ext)
            self.image_files.extend(glob.glob(pattern))
        
        # Sort files naturally (img1, img2, img10 instead of img1, img10, img2)
        self.image_files.sort(key=self.natural_sort_key)
        
        # Reset index
        self.current_image_index = 0

    def natural_sort_key(self, text):
        """Natural sorting key for filenames with numbers."""
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]

    def get_mask_path_for_image(self, image_path):
        """Get the corresponding mask path for an image."""
        if not self.mask_folder:
            return None
        
        # Extract filename without extension
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # Create mask filename based on your naming convention
        # Convert "imgX" to "og_mask_imgX"
        if base_name.startswith('img'):
            mask_name = f"og_mask_{base_name}"
        else:
            mask_name = f"og_mask_{base_name}"
        
        # Try different extensions
        for ext in ['.png', '.jpg', '.jpeg']:
            mask_path = os.path.join(self.mask_folder, mask_name + ext)
            if os.path.exists(mask_path):
                return mask_path
        
        return None

    def get_output_path_for_image(self, image_path):
        """Get the output path for saving the edited mask."""
        if not self.output_folder:
            return None
        
        # Extract filename without extension
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # Create output filename: "imgX" becomes "mask_imgX.png"
        if base_name.startswith('img'):
            output_name = f"mask_{base_name}.png"
        else:
            output_name = f"mask_{base_name}.png"
        
        return os.path.join(self.output_folder, output_name)

    def load_current_image(self):
        """Load the current image and its corresponding mask."""
        if not self.image_files or self.current_image_index >= len(self.image_files):
            return
        
        # Save current mask before loading new image
        if self.auto_save and self.mask_image is not None:
            self.save_current_mask()
        
        # Clear undo/redo stacks when switching images
        self.undo_stack = []
        self.redo_stack = []
        
        # Get current image path
        image_path = self.image_files[self.current_image_index]
        
        # Load image
        self.image_path = image_path
        self.original_image = cv2.imread(image_path)
        
        if self.original_image is None:
            messagebox.showerror("Error", f"Failed to load image: {os.path.basename(image_path)}")
            return
        
        # Convert BGR to RGB
        self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
        
        # Try to load corresponding mask
        mask_path = self.get_mask_path_for_image(image_path)
        
        if mask_path and os.path.exists(mask_path):
            self.mask_path = mask_path
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            
            if mask is not None:
                # Resize mask if needed
                if mask.shape != (self.original_image.shape[0], self.original_image.shape[1]):
                    mask = cv2.resize(mask, (self.original_image.shape[1], self.original_image.shape[0]))
                
                # Binarize mask
                _, self.mask_image = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
            else:
                # Create blank mask if mask file couldn't be loaded
                self.mask_image = np.zeros((self.original_image.shape[0], self.original_image.shape[1]), dtype=np.uint8)
                self.mask_path = None
        else:
            # Create blank mask if no mask file found
            self.mask_image = np.zeros((self.original_image.shape[0], self.original_image.shape[1]), dtype=np.uint8)
            self.mask_path = None
        
        # Update display
        self.update_display()
        self.update_navigation_info()
        self.update_status_display()

    def next_image(self, event=None):
        """Navigate to the next image."""
        if self.current_image_index < len(self.image_files) - 1:
            self.current_image_index += 1
            self.load_current_image()

    def previous_image(self, event=None):
        """Navigate to the previous image."""
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.load_current_image()

    def save_current_mask(self, event=None):
        """Save the current mask to the output folder."""
        if self.mask_image is None:
            return
        
        output_path = self.get_output_path_for_image(self.image_path)
        if output_path:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save mask
            cv2.imwrite(output_path, self.mask_image)
            
            if not self.auto_save:  # Only show message for manual saves
                self.status_label.config(text=f"Saved: {os.path.basename(output_path)}")

    def create_navigation_bar(self):
        """Create navigation controls for browsing images."""
        nav_frame = ttk.Frame(self.root, padding="5")
        nav_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Navigation controls
        ttk.Button(nav_frame, text="◀ Previous", command=self.previous_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_frame, text="Next ▶", command=self.next_image).pack(side=tk.LEFT, padx=5)
        
        # Image info
        self.nav_info_label = ttk.Label(nav_frame, text="", font=('Arial', 10))
        self.nav_info_label.pack(side=tk.LEFT, padx=20)
        
        # Save button
        ttk.Button(nav_frame, text="Save Mask", command=self.save_current_mask).pack(side=tk.RIGHT, padx=5)
        
        # Auto-save toggle
        self.auto_save_var = tk.BooleanVar(value=self.auto_save)
        ttk.Checkbutton(nav_frame, text="Auto-save", variable=self.auto_save_var, 
                       command=self.toggle_auto_save).pack(side=tk.RIGHT, padx=5)

    def update_navigation_info(self):
        """Update the navigation information display."""
        if self.image_files:
            current = self.current_image_index + 1
            total = len(self.image_files)
            image_name = os.path.basename(self.image_files[self.current_image_index])
            
            # Check if mask exists
            mask_path = self.get_mask_path_for_image(self.image_files[self.current_image_index])
            mask_status = "✓" if mask_path and os.path.exists(mask_path) else "✗"
            
            # Check if output exists
            output_path = self.get_output_path_for_image(self.image_files[self.current_image_index])
            output_status = "✓" if output_path and os.path.exists(output_path) else "✗"
            
            info_text = f"{current}/{total}: {image_name} | Mask: {mask_status} | Output: {output_status}"
            self.nav_info_label.config(text=info_text)
        else:
            self.nav_info_label.config(text="No images loaded")

    def toggle_auto_save(self):
        """Toggle auto-save functionality."""
        self.auto_save = self.auto_save_var.get()

    def create_menu(self):
        """Create the application menu bar with file, edit, view and help menus."""
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Setup Folders", command=self.setup_folders)
        file_menu.add_separator()
        file_menu.add_command(label="Open Image", command=self.open_image)
        file_menu.add_command(label="Open Mask", command=self.open_mask)
        file_menu.add_separator()
        file_menu.add_command(label="Save Mask", command=self.save_current_mask, accelerator="Ctrl+S")
        file_menu.add_command(label="Save Mask As...", command=self.save_mask_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Navigation menu
        nav_menu = tk.Menu(menubar, tearoff=0)
        nav_menu.add_command(label="Previous Image", command=self.previous_image, accelerator="←")
        nav_menu.add_command(label="Next Image", command=self.next_image, accelerator="→")
        nav_menu.add_separator()
        nav_menu.add_command(label="Go to Image...", command=self.go_to_image)
        menubar.add_cascade(label="Navigation", menu=nav_menu)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Invert Mask", command=self.invert_mask)
        edit_menu.add_command(label="Clear Selection", command=self.clear_selection)
        edit_menu.add_command(label="Fill Selection", command=self.fill_selection)
        edit_menu.add_command(label="Delete Selection", command=self.delete_selection)
        edit_menu.add_separator()
        edit_menu.add_command(label="Clean Noise", command=self.clean_noise)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Zoom In", command=lambda: self.zoom(1.2))
        view_menu.add_command(label="Zoom Out", command=lambda: self.zoom(0.8))
        view_menu.add_command(label="Reset Zoom", command=lambda: self.zoom(reset=True))
        view_menu.add_separator()
        
        overlay_menu = tk.Menu(view_menu, tearoff=0)
        overlay_menu.add_command(label="No Overlay", command=lambda: self.set_overlay(0))
        overlay_menu.add_command(label="25% Overlay", command=lambda: self.set_overlay(0.25))
        overlay_menu.add_command(label="50% Overlay", command=lambda: self.set_overlay(0.5))
        overlay_menu.add_command(label="75% Overlay", command=lambda: self.set_overlay(0.75))
        overlay_menu.add_command(label="Full Mask", command=lambda: self.set_overlay(1))
        view_menu.add_cascade(label="Overlay Transparency", menu=overlay_menu)
        
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Instructions", command=self.show_instructions)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)

    def go_to_image(self):
        """Navigate to a specific image by index."""
        if not self.image_files:
            return
        
        current = self.current_image_index + 1
        total = len(self.image_files)
        
        new_index = simpledialog.askinteger(
            "Go to Image",
            f"Enter image number (1-{total}):",
            initialvalue=current,
            minvalue=1,
            maxvalue=total
        )
        
        if new_index is not None:
            self.current_image_index = new_index - 1
            self.load_current_image()

    def create_toolbar(self):
        """Create the toolbar with various editing tools and options."""
        toolbar = ttk.Frame(self.root, padding="5")
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        # Tool selection
        tools_frame = ttk.LabelFrame(toolbar, text="Tools", padding="5")
        tools_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.tool_var = tk.StringVar(value="brush")
        
        ttk.Radiobutton(tools_frame, text="Brush", variable=self.tool_var, 
                        value="brush", command=lambda: self.set_tool("brush")).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(tools_frame, text="Line", variable=self.tool_var,
                        value="line", command=lambda: self.set_tool("line")).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(tools_frame, text="Select", variable=self.tool_var,
                        value="select", command=lambda: self.set_tool("select")).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(tools_frame, text="Polygon Select", variable=self.tool_var,
                        value="polygon", command=lambda: self.set_tool("polygon")).pack(side=tk.LEFT, padx=5)
        
        # Brush settings
        brush_frame = ttk.LabelFrame(toolbar, text="Brush Settings", padding="5")
        brush_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Label(brush_frame, text="Size:").pack(side=tk.LEFT, padx=5)
        size_control_frame = ttk.Frame(brush_frame)
        size_control_frame.pack(side=tk.LEFT, padx=5)

        self.brush_size_var = tk.IntVar(value=10)
        brush_slider = ttk.Scale(size_control_frame, from_=1, to=50, 
                                variable=self.brush_size_var, 
                                orient=tk.HORIZONTAL, length=100,
                                command=self.update_brush_size)
        brush_slider.pack(side=tk.TOP)

        size_entry_frame = ttk.Frame(size_control_frame)
        size_entry_frame.pack(side=tk.TOP, pady=2)

        self.size_entry = ttk.Entry(size_entry_frame, textvariable=self.brush_size_var, width=5)
        self.size_entry.pack(side=tk.LEFT)
        self.size_entry.bind('<Return>', self.validate_brush_size_entry)
        self.size_entry.bind('<FocusOut>', self.validate_brush_size_entry)
        
        # Brush color
        color_frame = ttk.LabelFrame(toolbar, text="Draw Color", padding="5")
        color_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.brush_color_var = tk.IntVar(value=255)
        ttk.Radiobutton(color_frame, text="White", variable=self.brush_color_var, 
                        value=255).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(color_frame, text="Black", variable=self.brush_color_var, 
                        value=0).pack(side=tk.LEFT, padx=5)
        
        # Action buttons
        action_frame = ttk.LabelFrame(toolbar, text="Actions", padding="5")
        action_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(action_frame, text="Fill", command=self.fill_selection).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Delete", command=self.delete_selection).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Clean Noise", command=self.clean_noise).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Invert", command=self.invert_mask).pack(side=tk.LEFT, padx=5)
        
        self.mask_only_btn = ttk.Button(action_frame, text="Show Mask Only", command=self.toggle_mask_only)
        self.mask_only_btn.pack(side=tk.LEFT, padx=5)
        
        self.image_only_btn = ttk.Button(action_frame, text="Show Image Only", command=self.toggle_image_only)
        self.image_only_btn.pack(side=tk.LEFT, padx=5)
        
        # Undo/Redo
        history_frame = ttk.LabelFrame(toolbar, text="History", padding="5")
        history_frame.pack(side=tk.RIGHT, padx=5, pady=5)
        
        ttk.Button(history_frame, text="Undo", command=self.undo).pack(side=tk.LEFT, padx=5)
        ttk.Button(history_frame, text="Redo", command=self.redo).pack(side=tk.LEFT, padx=5)

    def create_canvas(self):
        """Create the main canvas for displaying and editing images."""
        self.canvas_frame = ttk.Frame(self.root)
        self.canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="#2c2c2c")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind canvas events
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Motion>", self.update_cursor)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)
        
        self.image_container = self.canvas.create_image(0, 0, anchor="nw")
        self.scale = 1.0

    def create_statusbar(self):
        """Creates a status bar at the bottom of the window."""
        self.statusbar = ttk.Frame(self.root)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(self.statusbar, text="Ready", anchor=tk.W, padding=5)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.coords_label = ttk.Label(self.statusbar, text="", padding=5)
        self.coords_label.pack(side=tk.RIGHT)

    def update_status_display(self):
        """Update the status bar to show current image and mask file names."""
        status_parts = []
        
        if self.image_path:
            status_parts.append(f"Image: {os.path.basename(self.image_path)}")
        
        if self.mask_path:
            status_parts.append(f"Mask: {os.path.basename(self.mask_path)}")
        else:
            status_parts.append("Mask: None (creating new)")
        
        if not status_parts:
            status_text = "Ready. Use File > Setup Folders to configure directories."
        else:
            status_text = " | ".join(status_parts)
        
        self.status_label.config(text=status_text)

    def validate_brush_size_entry(self, event=None):
        """Validate and update brush size from entry widget."""
        try:
            value = self.brush_size_var.get()
            if value < 1:
                value = 1
            elif value > 50:
                value = 50
            
            self.brush_size_var.set(value)
            self.brush_size = value
            self.update_cursor(None)
            
        except tk.TclError:
            self.brush_size_var.set(self.brush_size)

    def escape_pressed(self, event=None):
        """Handle Escape key press to deselect active functionality."""
        self.clear_selection()
        self.clear_polygon_selection()
        
        if self.current_tool in ["select", "polygon"]:
            self.current_tool = "brush"
            self.tool_var.set("brush")
        
        self.is_drawing = False
        
        if hasattr(self, 'temp_line') and self.temp_line:
            self.canvas.delete(self.temp_line)
            self.temp_line = None
        
        if self.cursor_indicator:
            self.canvas.delete(self.cursor_indicator)
            self.cursor_indicator = None
        
        self.status_label.config(text="Selection cleared. Ready for editing.")

    def open_image(self):
        """Opens a file dialog for the user to select an image file."""
        path = filedialog.askopenfilename(
            title="Open Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg")]
        )
        
        if path:
            self.image_path = path
            self.original_image = cv2.imread(path)
            
            if self.original_image is None:
                messagebox.showerror("Error", "Failed to load the image file.")
                return
            
            self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
            
            if self.mask_image is None or self.mask_image.shape[:2] != self.original_image.shape[:2]:
                self.mask_image = np.zeros((self.original_image.shape[0], self.original_image.shape[1]), dtype=np.uint8)
            
            self.update_display()
            self.update_status_display()

    def open_mask(self):
        """Opens a file dialog for the user to select a mask file."""
        if self.original_image is None:
            messagebox.showinfo("Information", "Please open an image first.")
            return
        
        path = filedialog.askopenfilename(
            title="Open Mask",
            filetypes=[("Image files", "*.png *.jpg *.jpeg")]
        )
        
        if path:
            mask = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            
            if mask is None:
                messagebox.showerror("Error", "Failed to load the mask file.")
                return
            
            if mask.shape != (self.original_image.shape[0], self.original_image.shape[1]):
                answer = messagebox.askyesno(
                    "Size Mismatch", 
                    "The mask has different dimensions than the image. Would you like to resize it to match?"
                )
                if answer:
                    mask = cv2.resize(mask, (self.original_image.shape[1], self.original_image.shape[0]))
                else:
                    return
            
            self.save_undo_state()
            _, self.mask_image = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
            self.mask_path = path
            
            self.update_display()
            self.status_label.config(text=f"Loaded mask: {os.path.basename(path)}")

    def save_mask_as(self):
        """Opens a save file dialog to get a new file path."""
        if self.mask_image is None:
            messagebox.showinfo("Information", "No mask to save.")
            return
        
        path = filedialog.asksaveasfilename(
            title="Save Mask As",
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        
        if path:
            cv2.imwrite(path, self.mask_image)
            self.mask_path = path
            self.status_label.config(text=f"Saved mask to: {os.path.basename(path)}")

    def update_display(self):
        """Update the display with the current image and mask overlay."""
        if self.original_image is None or self.mask_image is None:
            return
        
        if hasattr(self, '_updating_display') and self._updating_display:
            return
        self._updating_display = True
        
        if self.show_mask_only:
            white_background = np.ones_like(self.original_image) * 255
            colored_mask = np.zeros_like(self.original_image)
            colored_mask[self.mask_image == 255] = [0, 0, 180]
            self.display_image = np.where(self.mask_image[..., np.newaxis] == 255, 
                                        colored_mask, white_background)
        elif self.show_image_only:
            self.display_image = self.original_image.copy()
        else:
            colored_mask = np.zeros_like(self.original_image)
            colored_mask[self.mask_image == 255] = [0, 0, 180]
            self.display_image = cv2.addWeighted(
                self.original_image, 1.0, 
                colored_mask, self.overlay_alpha, 
                0
            )
        
        pil_image = Image.fromarray(self.display_image)
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = self.root.winfo_width() - 40
            canvas_height = self.root.winfo_height() - 200
        
        img_width, img_height = pil_image.size
        width_ratio = canvas_width / img_width
        height_ratio = canvas_height / img_height
        
        display_scale = min(width_ratio, height_ratio)
        display_scale *= self.scale
        
        new_width = int(img_width * display_scale)
        new_height = int(img_height * display_scale)
        
        if new_width > 0 and new_height > 0:
            display_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
            
            self.photo_image = ImageTk.PhotoImage(display_image)
            self.canvas.itemconfig(self.image_container, image=self.photo_image)
            
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            x_pos = max(0, (canvas_width - new_width) // 2)
            y_pos = max(0, (canvas_height - new_height) // 2)
            self.canvas.coords(self.image_container, x_pos, y_pos)
            
            self.display_scale = display_scale
            self.display_offset_x = x_pos
            self.display_offset_y = y_pos
            
            if not hasattr(self, '_updating_selections') or not self._updating_selections:
                self.update_selections_after_zoom()
        
        self._updating_display = False

    def toggle_image_only(self):
        """Toggle between normal view and image-only view."""
        self.show_image_only = not self.show_image_only
        
        if self.show_image_only:
            self.show_mask_only = False
            self.mask_only_btn.config(text="Show Mask Only")
        
        if self.show_image_only:
            self.image_only_btn.config(text="Show Overlay")
            self.status_label.config(text="Showing image only")
        else:
            self.image_only_btn.config(text="Show Image Only")
            self.status_label.config(text="Showing overlay")
        
        self.update_display()

    def toggle_mask_only(self):
        """Toggle between normal overlay view and mask-only view."""
        self.show_mask_only = not self.show_mask_only
        
        if self.show_mask_only:
            self.show_image_only = False
            self.image_only_btn.config(text="Show Image Only")
        
        if self.show_mask_only:
            self.mask_only_btn.config(text="Show Overlay")
            self.status_label.config(text="Showing mask only")
        else:
            self.mask_only_btn.config(text="Show Mask Only")
            self.status_label.config(text="Showing overlay")
        
        self.update_display()

    def set_tool(self, tool_name):
        """Activates the specified tool."""
        self.current_tool = tool_name
        self.status_label.config(text=f"Selected tool: {tool_name}")
        
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
            self.selection_rect = None
            self.selection_start = None
            self.selected_region = None
        
        self.clear_polygon_selection()

    def clear_polygon_selection(self):
        """Clear any active polygon selection."""
        for line_id in self.polygon_lines:
            self.canvas.delete(line_id)
        
        for vertex_id in self.polygon_vertices:
            self.canvas.delete(vertex_id)
        
        self.polygon_points = []
        self.polygon_lines = []
        self.polygon_vertices = []
        self.polygon_closed = False
        self.active_vertex = None
        self.hover_vertex = None
        self.polygon_region = None
        self.close_option_active = False
        
        if self.temp_line:
            self.canvas.delete(self.temp_line)
            self.temp_line = None
        
        if hasattr(self, 'close_indicator') and self.close_indicator:
            self.canvas.delete(self.close_indicator)
            self.close_indicator = None
        
        self._updating_display = False
        self._updating_selections = False
        self._highlighting = False

    def update_brush_size(self, value):
        """Update the brush size based on slider value."""
        self.brush_size = int(float(value))
        self.update_cursor(None)

    def update_cursor(self, event):
        """Update the cursor appearance based on the current tool and brush size."""
        if self.original_image is None or self.mask_image is None:
            return
            
        if self.cursor_indicator:
            self.canvas.delete(self.cursor_indicator)
            self.cursor_indicator = None
        
        if event is None:
            return
            
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        if self.current_tool in ["brush", "line"]:
            brush_radius = self.brush_size * self.display_scale
            
            self.cursor_indicator = self.canvas.create_oval(
                canvas_x - brush_radius, canvas_y - brush_radius,
                canvas_x + brush_radius, canvas_y + brush_radius,
                outline="#444444", width=1, fill="#444444", stipple="gray50"
            )
        elif self.current_tool == "polygon":
            # Check if hovering over a vertex
            self.hover_vertex = None
            for i, (px, py) in enumerate(self.polygon_points):
                if abs(canvas_x - px) < 15 and abs(canvas_y - py) < 15:
                    self.hover_vertex = i
                    
                    # Highlight the vertex
                    self.canvas.itemconfig(
                        self.polygon_vertices[i],
                        fill="yellow",
                        outline="yellow"
                    )
                else:
                    # Reset vertex appearance if it was previously highlighted
                    if i < len(self.polygon_vertices):
                        self.canvas.itemconfig(
                            self.polygon_vertices[i], 
                            fill="red" if i > 0 else "green",
                            outline="white"
                        )
            
            # Check if hovering near the first point (for closing)
            if len(self.polygon_points) >= 3 and not self.polygon_closed:
                first_x, first_y = self.polygon_points[0]
                distance = ((canvas_x - first_x)**2 + (canvas_y - first_y)**2)**0.5
                
                if distance < 20:  # Detection radius for closing
                    # Highlight first point to indicate closing is possible
                    self.canvas.itemconfig(
                        self.polygon_vertices[0],
                        fill="yellow",
                        outline="black",
                        width=2
                    )
                    
                    # Add temporary indicator to show potential closing action
                    if not hasattr(self, 'close_indicator') or not self.close_indicator:
                        self.close_indicator = self.canvas.create_text(
                            first_x, first_y - 15,
                            text="Click to close",
                            fill="white",
                            font=('Arial', 8)
                        )
                    
                    # Change cursor to indicate closing action
                    self.canvas.config(cursor="hand2")
                    
                    self.close_option_active = True  # Set flag to indicate closing option is active
                else:
                    # Reset first vertex appearance
                    if len(self.polygon_vertices) > 0:
                        self.canvas.itemconfig(
                            self.polygon_vertices[0],
                            fill="green",
                            outline="white",
                            width=1
                        )
                    
                    # Remove temporary closing indicator
                    if hasattr(self, 'close_indicator') and self.close_indicator:
                        self.canvas.delete(self.close_indicator)
                        self.close_indicator = None
                    
                    # Reset cursor
                    self.canvas.config(cursor="crosshair")
                    self.close_option_active = False  # Reset flag
            else:
                # Default polygon cursor
                self.canvas.config(cursor="crosshair")
        elif self.current_tool == "select":
            self.canvas.config(cursor="crosshair")
        else:
            self.canvas.config(cursor="")

    def set_overlay(self, alpha):
        """Set the transparency level of the mask overlay."""
        self.overlay_alpha = alpha
        self.update_display()

    def zoom(self, factor=1.0, reset=False):
        """Zoom the image display."""
        if reset:
            self.scale = 1.0
        else:
            self.scale *= factor
            
        self.scale = max(0.1, min(10.0, self.scale))
        self.update_display()
        self.status_label.config(text=f"Zoom: {self.scale:.2f}x")

    def save_undo_state(self):
        """Save the current mask state to the undo stack."""
        if self.mask_image is not None:
            self.undo_stack.append(self.mask_image.copy())
            self.redo_stack = []

    def undo(self, event=None):
        """Undo the last edit operation."""
        if len(self.undo_stack) > 0:
            self.redo_stack.append(self.mask_image.copy())
            self.mask_image = self.undo_stack.pop()
            self.update_display()
            self.status_label.config(text="Undo")

    def redo(self, event=None):
        """Redo the last undone operation."""
        if len(self.redo_stack) > 0:
            self.undo_stack.append(self.mask_image.copy())
            self.mask_image = self.redo_stack.pop()
            self.update_display()
            self.status_label.config(text="Redo")

    def invert_mask(self):
        """Invert the mask."""
        if self.mask_image is not None:
            self.save_undo_state()
            self.mask_image = cv2.bitwise_not(self.mask_image)
            self.update_display()
            self.status_label.config(text="Mask inverted")

    def clean_noise(self):
        """Apply morphological operations to clean noise in the mask."""
        if self.mask_image is None:
            return
        
        kernel_size = simpledialog.askinteger(
            "Clean Noise", 
            "Enter kernel size for operations (odd number):",
            initialvalue=5,
            minvalue=3,
            maxvalue=21
        )
        
        if kernel_size is None:
            return
        
        if kernel_size % 2 == 0:
            kernel_size += 1
        
        self.save_undo_state()
        
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        
        # If we have a selection, only clean that area
        if self.selected_region is not None:
            x, y, w, h = self.selected_region
            
            # Extract region
            region = self.mask_image[y:y+h, x:x+w].copy()
            
            # Apply operations
            region = cv2.morphologyEx(region, cv2.MORPH_OPEN, kernel)
            region = cv2.morphologyEx(region, cv2.MORPH_CLOSE, kernel)
            
            # Put region back
            self.mask_image[y:y+h, x:x+w] = region
        elif self.polygon_region is not None:
            # Create a copy of the mask
            mask_copy = self.mask_image.copy()
            
            # Apply morphological operations to the entire mask
            cleaned_mask = cv2.morphologyEx(mask_copy, cv2.MORPH_OPEN, kernel)
            cleaned_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_CLOSE, kernel)
            
            # Apply the changes only within the polygon region
            self.mask_image = np.where(self.polygon_region > 0, cleaned_mask, self.mask_image)
        else:
            # Clean entire mask
            self.mask_image = cv2.morphologyEx(self.mask_image, cv2.MORPH_OPEN, kernel)
            self.mask_image = cv2.morphologyEx(self.mask_image, cv2.MORPH_CLOSE, kernel)
        
        self.update_display()
        self.status_label.config(text=f"Cleaned noise with kernel size {kernel_size}")

    def fill_selection(self):
        """Fill the selected region with the currently selected color."""
        color = self.brush_color_var.get()
        
        # Check if we have a rectangle selection
        if self.selected_region is not None:
            self.save_undo_state()
            x, y, w, h = self.selected_region
            
            # Create a mask to only fill white pixels in the selection
            if color == 255:  # If filling with white, target black pixels
                target_mask = (self.mask_image[y:y+h, x:x+w] == 0)
            else:  # If filling with black, target white pixels
                target_mask = (self.mask_image[y:y+h, x:x+w] == 255)
            
            # Apply the fill only to targeted pixels
            region = self.mask_image[y:y+h, x:x+w].copy()
            region[target_mask] = color
            self.mask_image[y:y+h, x:x+w] = region
            
            self.update_display()
            self.status_label.config(text=f"Selection filled with {color}")
        
        # Check if we have a polygon selection
        elif self.polygon_region is not None:
            self.save_undo_state()
            
            # Apply the color to the masked area
            if color == 255:  # White
                self.mask_image[self.polygon_region == 255] = 255
            else:  # Black
                self.mask_image[self.polygon_region == 255] = 0
            
            self.update_display()
            self.status_label.config(text=f"Polygon area filled with {color}")
        else:
            messagebox.showinfo("Information", "No selection to fill. Please use Select or Polygon Select first.")

    def delete_selection(self):
        """Delete the mask content in the selected region."""
        # Check if we have a rectangle selection
        if self.selected_region is not None:
            self.save_undo_state()
            x, y, w, h = self.selected_region
            
            # Set the selected region to black (0)
            self.mask_image[y:y+h, x:x+w] = 0
            
            self.update_display()
            self.status_label.config(text="Selection deleted")
        
        # Check if we have a polygon selection
        elif self.polygon_region is not None:
            self.save_undo_state()
            
            # Delete the mask content in the polygon area
            self.mask_image[self.polygon_region == 255] = 0
            
            self.update_display()
            self.status_label.config(text="Polygon area deleted")
        else:
            messagebox.showinfo("Information", "No selection to delete. Please use Select or Polygon Select first.")

    def clear_selection(self):
        """Clears the current selection."""
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
            self.selection_rect = None
            self.selection_start = None
            self.selected_region = None
        
        self.clear_polygon_selection()
        self.status_label.config(text="Selection cleared")

    def on_window_resize(self, event):
        """Handle window resize events."""
        if event.widget == self.root:
            self.root.after(100, self.update_display)

    def update_selections_after_zoom(self):
        """Update selection visuals after zooming or resizing."""
        # Prevent recursive calls
        if hasattr(self, '_updating_selections') and self._updating_selections:
            return
        self._updating_selections = True
        
        # Update rectangle selection if active
        if self.selection_rect and self.selection_start and self.selected_region:
            x, y, w, h = self.selected_region
            start_x, start_y = x, y
            end_x, end_y = x + w, y + h
            
            # Convert to display coordinates
            display_start_x, display_start_y = self.image_to_display_coords(start_x, start_y)
            display_end_x, display_end_y = self.image_to_display_coords(end_x, end_y)
            
            # Update rectangle coords
            self.canvas.coords(
                self.selection_rect,
                display_start_x, display_start_y, display_end_x, display_end_y
            )
        
        # Update polygon selection if active
        if self.polygon_points and len(self.polygon_lines) > 0:
            # Store the original points in image coordinates before applying zoom
            image_points = []
            for point in self.polygon_points:
                image_points.append(self.display_to_image_coords(point[0], point[1]))
            
            # Convert image coordinates back to new display coordinates after zoom
            updated_points = []
            for img_x, img_y in image_points:
                disp_x, disp_y = self.image_to_display_coords(img_x, img_y)
                updated_points.append((disp_x, disp_y))
            
            # Update lines
            for i, line_id in enumerate(self.polygon_lines):
                start_idx = i
                end_idx = (i + 1) % len(updated_points)
                
                start_x, start_y = updated_points[start_idx]
                end_x, end_y = updated_points[end_idx]
                
                self.canvas.coords(line_id, start_x, start_y, end_x, end_y)
            
            # Update vertices
            for i, vertex_id in enumerate(self.polygon_vertices):
                x, y = updated_points[i]
                self.canvas.coords(
                    vertex_id,
                    x - 5, y - 5,
                    x + 5, y + 5
                )
            
            # Update polygon points with new display coordinates
            self.polygon_points = updated_points
            
            # If the polygon is closed, update the selection mask without triggering display update
            if self.polygon_closed and not hasattr(self, '_highlighting') or not self._highlighting:
                self.polygon_region = self.create_polygon_mask()
            
            # Update close indicator if it exists
            if hasattr(self, 'close_indicator') and self.close_indicator:
                if len(self.polygon_points) > 0:
                    first_x, first_y = self.polygon_points[0]
                    self.canvas.coords(self.close_indicator, first_x, first_y - 15)
        
        # Clear the flag
        self._updating_selections = False

    def display_to_image_coords(self, display_x, display_y):
        """Convert display coordinates to image coordinates."""
        # Account for image position in canvas
        adjusted_x = display_x - self.display_offset_x
        adjusted_y = display_y - self.display_offset_y
        
        # Convert from display scale to image scale
        image_x = int(adjusted_x / self.display_scale)
        image_y = int(adjusted_y / self.display_scale)
        
        # Ensure coordinates are within image bounds
        if self.mask_image is not None:
            image_x = max(0, min(image_x, self.mask_image.shape[1] - 1))
            image_y = max(0, min(image_y, self.mask_image.shape[0] - 1))
        
        return (image_x, image_y)

    def image_to_display_coords(self, image_x, image_y):
        """Convert image coordinates to display coordinates."""
        # Convert from image scale to display scale
        display_x = int(image_x * self.display_scale) + self.display_offset_x
        display_y = int(image_y * self.display_scale) + self.display_offset_y
        
        return (display_x, display_y)

    def create_vertex_marker(self, x, y, is_first=False):
        """Create a visual marker for a polygon vertex."""
        # Use a different color for the first point
        fill_color = "green" if is_first else "red"
        
        # Create a small circle as the vertex marker
        vertex_id = self.canvas.create_oval(
            x - 5, y - 5,
            x + 5, y + 5,
            fill=fill_color,
            outline="white",
            tags="vertex"
        )
        
        return vertex_id

    def create_polygon_mask(self):
        """Create a binary mask from the current polygon selection."""
        if len(self.polygon_points) < 3:
            return None
        
        # Create a blank mask of the same size as the image
        polygon_mask = np.zeros_like(self.mask_image)
        
        # Convert display coordinates to image coordinates
        image_points = []
        for point in self.polygon_points:
            x, y = self.display_to_image_coords(point[0], point[1])
            image_points.append([x, y])
        
        # Fill the polygon area in the mask
        pts = np.array(image_points, np.int32)
        pts = pts.reshape((-1, 1, 2))
        cv2.fillPoly(polygon_mask, [pts], 255)
        
        return polygon_mask

    def highlight_polygon_selection(self):
        """Highlight the polygon selection area."""
        # Prevent recursion
        if hasattr(self, '_highlighting') and self._highlighting:
            return
        self._highlighting = True
        
        # Create a mask for the polygon
        self.polygon_region = self.create_polygon_mask()
        
        # Update display only if not already updating
        if not hasattr(self, '_updating_display') or not self._updating_display:
            self.update_display()
        
        self.status_label.config(text="Polygon selection complete. Use Fill or Delete to modify.")
        
        # Clear flag
        self._highlighting = False

    def on_mouse_down(self, event):
        """Handle mouse button press events."""
        if self.original_image is None or self.mask_image is None:
            return
        
        # Get canvas coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Check if click is within the image
        if canvas_x < self.display_offset_x or canvas_y < self.display_offset_y or \
        canvas_x >= self.display_offset_x + self.photo_image.width() or \
        canvas_y >= self.display_offset_y + self.photo_image.height():
            return
        
        # Convert to image coordinates
        image_x, image_y = self.display_to_image_coords(canvas_x, canvas_y)
        
        self.is_drawing = True
        self.last_x, self.last_y = image_x, image_y
        
        if self.current_tool == "brush":
            self.save_undo_state()
            self.draw_brush(image_x, image_y)
            self.update_display()
        elif self.current_tool == "select":
            self.selection_start = (image_x, image_y)
            
            # Clear previous selection
            if self.selection_rect:
                self.canvas.delete(self.selection_rect)
            
            # Start new selection rect
            display_x, display_y = self.image_to_display_coords(image_x, image_y)
            self.selection_rect = self.canvas.create_rectangle(
                display_x, display_y, display_x, display_y,
                outline='yellow', width=2, dash=(4, 4)
            )
        elif self.current_tool == "line":
            self.save_undo_state()
            # Start a new line
            self.line_start = (image_x, image_y)
            
            # Create a temporary line on the canvas for visual feedback
            display_x, display_y = self.image_to_display_coords(image_x, image_y)
            self.temp_line = self.canvas.create_line(
                display_x, display_y, display_x, display_y,
                fill='yellow', width=2
            )
        elif self.current_tool == "polygon":
            # Check if we're trying to close the polygon
            if len(self.polygon_points) >= 3 and not self.polygon_closed:
                first_x, first_y = self.polygon_points[0]
                distance = ((canvas_x - first_x)**2 + (canvas_y - first_y)**2)**0.5
                
                if distance < 20:  # Direct distance check
                    # Close the polygon
                    last_pt = self.polygon_points[-1]
                    first_pt = self.polygon_points[0]
                    
                    # Create the closing line
                    line_id = self.canvas.create_line(
                        last_pt[0], last_pt[1], 
                        first_pt[0], first_pt[1],
                        fill="yellow", width=2
                    )
                    self.polygon_lines.append(line_id)
                    self.polygon_closed = True
                    
                    # Create the mask for the polygon region
                    self.polygon_region = self.create_polygon_mask()
                    
                    # Update status
                    self.status_label.config(text="Polygon closed. Use Fill/Delete to modify the selected area.")
                    
                    # Clean up closing indicator
                    if hasattr(self, 'close_indicator') and self.close_indicator:
                        self.canvas.delete(self.close_indicator)
                        self.close_indicator = None
                    
                    # Remove temporary line if it exists
                    if self.temp_line:
                        self.canvas.delete(self.temp_line)
                        self.temp_line = None
                    
                    return  # Exit after closing the polygon
            
            # Check if clicking on an existing vertex for dragging
            if self.hover_vertex is not None:
                self.active_vertex = self.hover_vertex
                return
            
            # If the polygon is closed, start a new one
            if self.polygon_closed:
                self.clear_polygon_selection()
            
            # Add a new point
            self.polygon_points.append((canvas_x, canvas_y))
            
            # Add a vertex marker
            is_first = len(self.polygon_points) == 1
            vertex_id = self.create_vertex_marker(canvas_x, canvas_y, is_first)
            self.polygon_vertices.append(vertex_id)
            
            # If this is the first point, no line to draw yet
            if len(self.polygon_points) > 1:
                # Draw line from previous point to this point
                last_x, last_y = self.polygon_points[-2]
                line_id = self.canvas.create_line(
                    last_x, last_y, canvas_x, canvas_y,
                    fill="yellow", width=2
                )
                self.polygon_lines.append(line_id)
                
            # Remove temporary line if it exists
            if self.temp_line:
                self.canvas.delete(self.temp_line)
                self.temp_line = None
                
            # If we have at least 3 points, check if we can close the polygon
            if len(self.polygon_points) >= 3:
                self.update_cursor(event)  # Update to check for closing option

    def on_mouse_move(self, event):
        """Handle mouse movement events."""
        if self.original_image is None or self.mask_image is None:
            return
        
        # Get canvas coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Update coordinates display
        self.coords_label.config(text=f"Canvas: {int(canvas_x)},{int(canvas_y)}")
        
        # Update cursor
        self.update_cursor(event)
        
        # If not drawing, exit
        if not self.is_drawing:
            # If we're in polygon mode and have at least one point, show temporary line
            if self.current_tool == "polygon" and self.polygon_points and not self.polygon_closed:
                if self.temp_line:
                    self.canvas.delete(self.temp_line)
                
                last_x, last_y = self.polygon_points[-1]
                self.temp_line = self.canvas.create_line(
                    last_x, last_y, canvas_x, canvas_y,
                    fill="yellow", width=2, dash=(4, 4)
                )
            return
        
        # Check if coordinates are within image bounds
        if canvas_x < self.display_offset_x or canvas_y < self.display_offset_y or \
           canvas_x >= self.display_offset_x + self.photo_image.width() or \
           canvas_y >= self.display_offset_y + self.photo_image.height():
            return
        
        # Convert to image coordinates
        image_x, image_y = self.display_to_image_coords(canvas_x, canvas_y)
        
        if self.current_tool == "brush":
            self.draw_line(self.last_x, self.last_y, image_x, image_y)
            self.last_x, self.last_y = image_x, image_y
            self.update_display()
        elif self.current_tool == "select" and self.selection_start:
            # Update selection rectangle
            start_x, start_y = self.selection_start
            
            # Update selection rectangle on canvas
            display_start_x, display_start_y = self.image_to_display_coords(start_x, start_y)
            display_curr_x, display_curr_y = self.image_to_display_coords(image_x, image_y)
            
            self.canvas.coords(
                self.selection_rect,
                display_start_x, display_start_y, display_curr_x, display_curr_y
            )
        elif self.current_tool == "line" and hasattr(self, 'line_start'):
            # Update temporary line
            start_x, start_y = self.line_start
            display_start_x, display_start_y = self.image_to_display_coords(start_x, start_y)
            display_curr_x, display_curr_y = self.image_to_display_coords(image_x, image_y)
            
            self.canvas.coords(
                self.temp_line,
                display_start_x, display_start_y, display_curr_x, display_curr_y
            )
        elif self.current_tool == "polygon" and self.active_vertex is not None:
            # Drag the active vertex
            self.polygon_points[self.active_vertex] = (canvas_x, canvas_y)
            
            # Update vertex marker
            if self.active_vertex < len(self.polygon_vertices):
                self.canvas.coords(
                    self.polygon_vertices[self.active_vertex],
                    canvas_x - 5, canvas_y - 5,
                    canvas_x + 5, canvas_y + 5
                )
            
            # Update connected lines
            if len(self.polygon_points) > 1:
                # Update line before the vertex
                prev_idx = (self.active_vertex - 1) % len(self.polygon_points)
                prev_x, prev_y = self.polygon_points[prev_idx]
                
                if self.active_vertex > 0 or self.polygon_closed:
                    line_idx = prev_idx if self.polygon_closed else self.active_vertex - 1
                    if line_idx < len(self.polygon_lines) and line_idx >= 0:
                        self.canvas.coords(
                            self.polygon_lines[line_idx],
                            prev_x, prev_y, canvas_x, canvas_y
                        )
                
                # Update line after the vertex
                next_idx = (self.active_vertex + 1) % len(self.polygon_points)
                
                if next_idx != self.active_vertex and (self.active_vertex < len(self.polygon_points) - 1 or self.polygon_closed):
                    line_idx = self.active_vertex
                    if line_idx < len(self.polygon_lines):
                        next_x, next_y = self.polygon_points[next_idx]
                        self.canvas.coords(
                            self.polygon_lines[line_idx],
                            canvas_x, canvas_y, next_x, next_y
                        )
            
            # If polygon is closed, update the selection mask
            if self.polygon_closed:
                self.polygon_region = self.create_polygon_mask()

    def on_mouse_up(self, event):
        """Handle mouse button release events."""
        if not self.is_drawing:
            return
        
        self.is_drawing = False
        
        # Get canvas coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Convert to image coordinates
        image_x, image_y = self.display_to_image_coords(canvas_x, canvas_y)
        
        if self.current_tool == "select" and self.selection_start:
            # Calculate rectangle in image coordinates
            start_x, start_y = self.selection_start
            
            # Make sure coordinates are within image bounds
            start_x = max(0, min(start_x, self.mask_image.shape[1] - 1))
            start_y = max(0, min(start_y, self.mask_image.shape[0] - 1))
            end_x = max(0, min(image_x, self.mask_image.shape[1] - 1))
            end_y = max(0, min(image_y, self.mask_image.shape[0] - 1))
            
            # Ensure start is the top-left and end is the bottom-right
            left = min(start_x, end_x)
            top = min(start_y, end_y)
            right = max(start_x, end_x)
            bottom = max(start_y, end_y)
            
            # Store the selection region (x, y, width, height)
            self.selected_region = (left, top, right - left, bottom - top)
            
            # Highlight white pixels in the selection
            self.highlight_selection()
            
            self.status_label.config(text=f"Selected region: {self.selected_region}")
        elif self.current_tool == "line" and hasattr(self, 'line_start'):
            # Draw permanent line on the mask
            start_x, start_y = self.line_start
            self.draw_line(start_x, start_y, image_x, image_y)
            
            # Remove temporary line
            self.canvas.delete(self.temp_line)
            delattr(self, 'line_start')
            delattr(self, 'temp_line')
            
            self.update_display()
        elif self.current_tool == "polygon":
            # Release the active vertex if dragging
            self.active_vertex = None
            
            # If the polygon is closed, update the mask
            if self.polygon_closed:
                self.polygon_region = self.create_polygon_mask()

    def highlight_selection(self):
        """Highlight the white pixels in the current selection."""
        if self.selected_region is None:
            return
        
        # Get the selection region
        x, y, w, h = self.selected_region
        
        # Create a visual highlight in the display
        # This is done in the update_display method by using a different overlay
        # We'll update the display to show the highlight
        self.update_display()

    def on_mouse_wheel(self, event):
        """Handle mouse wheel events for zooming."""
        if event.num == 4 or event.delta > 0:
            self.zoom(1.1)
        elif event.num == 5 or event.delta < 0:
            self.zoom(0.9)

    def draw_brush(self, x, y):
        """Draw a filled circle at the specified coordinates."""
        cv2.circle(
            self.mask_image, 
            (x, y), 
            self.brush_size, 
            self.brush_color_var.get(), 
            -1
        )

    def draw_line(self, x1, y1, x2, y2):
        """Draw a line between the specified coordinates."""
        cv2.line(
            self.mask_image, 
            (x1, y1), 
            (x2, y2), 
            self.brush_color_var.get(), 
            self.brush_size
        )

    def show_instructions(self):
        """Display instructions for using the tool."""
        instructions = """
Enhanced Binary Mask Editor Tool Instructions

NEW FEATURES:
- Folder-based navigation: Set up image, mask, and output folders at startup
- Auto-navigation: Use arrow keys (← →) to move between images
- Auto-save: Automatically saves masks when switching images (optional)
- Progress tracking: See which images have masks and outputs

NAVIGATION:
- Left/Right arrow keys: Navigate between images
- Ctrl+S: Save current mask
- Navigation menu: Go to specific image by number

TOOLS:
- Brush: Draw on the mask with selected color and size
- Line: Draw straight lines
- Select: Select rectangular regions
- Polygon Select: Create polygon selections by clicking points

POLYGON SELECTION:
- Click to add points to create a polygon
- Close the polygon by clicking near the first point
- Drag vertices to adjust the polygon shape
- Use Fill/Delete to modify the selected area
- Press Escape to clear selection

WORKFLOW:
1. File > Setup Folders to configure directories
2. Navigate through images using arrow keys
3. Edit masks using the tools
4. Masks auto-save when moving to next image (if enabled)
5. Manual save with Ctrl+S or Save button

NAMING CONVENTION:
- Images: img1.png, img2.png, ...
- Input masks: og_mask_img1.png, og_mask_img2.png, ...
- Output masks: mask_img1.png, mask_img2.png, ...
"""
        messagebox.showinfo("Instructions", instructions)

    def show_about(self):
        """Display information about the tool."""
        about_text = """
Enhanced Binary Mask Editor Tool

An improved version of the mask editor with folder navigation and batch processing capabilities.

NEW FEATURES:
- Folder-based workflow similar to LabelMe
- Automatic image-mask pairing
- Progress tracking and navigation
- Auto-save functionality
- Keyboard shortcuts for navigation
- Full polygon selection support

Perfect for editing large batches of masks generated by SAM2 or other segmentation models.

Created with Python, OpenCV, and Tkinter.
"""
        messagebox.showinfo("About", about_text)


class FolderSetupDialog:
    """Dialog for setting up folder paths."""
    
    def __init__(self, parent):
        self.parent = parent
        self.result = None
        
    def show(self):
        """Show the folder setup dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Setup Folders")
        self.dialog.geometry("600x400")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (400 // 2)
        self.dialog.geometry(f"600x400+{x}+{y}")
        
        # Variables
        self.image_folder_var = tk.StringVar()
        self.mask_folder_var = tk.StringVar()
        self.output_folder_var = tk.StringVar()
        self.auto_save_var = tk.BooleanVar(value=True)
        
        self.create_widgets()
        
        # Wait for dialog to close
        self.dialog.wait_window()
        return self.result
    
    def create_widgets(self):
        """Create the dialog widgets."""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Folder Setup", font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Instructions
        instructions = ttk.Label(main_frame, 
                                text="Select the folders containing your images, masks, and where to save edited masks:",
                                wraplength=550)
        instructions.pack(pady=(0, 20))
        
        # Image folder
        img_frame = ttk.LabelFrame(main_frame, text="Image Folder", padding="10")
        img_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(img_frame, textvariable=self.image_folder_var, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(img_frame, text="Browse", command=self.browse_image_folder).pack(side=tk.RIGHT)
        
        # Mask folder
        mask_frame = ttk.LabelFrame(main_frame, text="Input Mask Folder (Optional)", padding="10")
        mask_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(mask_frame, textvariable=self.mask_folder_var, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(mask_frame, text="Browse", command=self.browse_mask_folder).pack(side=tk.RIGHT)
        
        # Output folder
        output_frame = ttk.LabelFrame(main_frame, text="Output Folder (for edited masks)", padding="10")
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(output_frame, textvariable=self.output_folder_var, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(output_frame, text="Browse", command=self.browse_output_folder).pack(side=tk.RIGHT)
        
        # Options
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.pack(fill=tk.X, pady=20)
        
        ttk.Checkbutton(options_frame, text="Auto-save masks when switching images", 
                       variable=self.auto_save_var).pack(anchor=tk.W)
        
        # Naming convention info
        info_frame = ttk.LabelFrame(main_frame, text="File Naming Convention", padding="10")
        info_frame.pack(fill=tk.X, pady=5)
        
        info_text = """Expected naming convention:
• Images: img1.png, img2.png, img3.png, ...
• Input masks: og_mask_img1.png, og_mask_img2.png, ...
• Output masks: mask_img1.png, mask_img2.png, ..."""
        
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack(anchor=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.LEFT, padx=10)
    
    def browse_image_folder(self):
        """Browse for image folder."""
        folder = filedialog.askdirectory(title="Select Image Folder")
        if folder:
            self.image_folder_var.set(folder)
    
    def browse_mask_folder(self):
        """Browse for mask folder."""
        folder = filedialog.askdirectory(title="Select Input Mask Folder")
        if folder:
            self.mask_folder_var.set(folder)
    
    def browse_output_folder(self):
        """Browse for output folder."""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder_var.set(folder)
    
    def ok_clicked(self):
        """Handle OK button click."""
        # Validate inputs
        if not self.image_folder_var.get():
            messagebox.showerror("Error", "Please select an image folder.")
            return
        
        if not os.path.exists(self.image_folder_var.get()):
            messagebox.showerror("Error", "Image folder does not exist.")
            return
        
        if not self.output_folder_var.get():
            messagebox.showerror("Error", "Please select an output folder.")
            return
        
        # Create output folder if it doesn't exist
        try:
            os.makedirs(self.output_folder_var.get(), exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot create output folder: {e}")
            return
        
        # Set result
        self.result = {
            'image_folder': self.image_folder_var.get(),
            'mask_folder': self.mask_folder_var.get() if self.mask_folder_var.get() else None,
            'output_folder': self.output_folder_var.get(),
            'auto_save': self.auto_save_var.get()
        }
        
        self.dialog.destroy()
    
    def cancel_clicked(self):
        """Handle Cancel button click."""
        self.result = None
        self.dialog.destroy()


# Usage example
if __name__ == "__main__":
    root = tk.Tk()
    app = MaskEditorApp(root)
    root.mainloop()