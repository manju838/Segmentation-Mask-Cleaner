#!/usr/bin/env python3
"""
Enhanced Launcher for the Binary Mask Editor Tool

This script initializes and launches the enhanced Binary Mask Editor application
with folder navigation capabilities similar to LabelMe.

Usage:
    python enhanced_launcher.py
    python enhanced_launcher.py --image-folder /path/to/images --mask-folder /path/to/masks --output-folder /path/to/output
"""

import os
import sys
import tkinter as tk
import cv2
import argparse
from enhanced_mask_editor import MaskEditorApp

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Enhanced Binary Mask Editor Tool')
    
    parser.add_argument('--image-folder', 
                       help='Path to the folder containing images')
    
    parser.add_argument('--mask-folder', 
                       help='Path to the folder containing input masks (optional)')
    
    parser.add_argument('--output-folder', 
                       help='Path to the folder for saving edited masks')
    
    parser.add_argument('--auto-save', 
                       action='store_true', 
                       default=True,
                       help='Enable auto-save when switching images (default: True)')
    
    parser.add_argument('--no-auto-save', 
                       action='store_true',
                       help='Disable auto-save functionality')
    
    return parser.parse_args()

def validate_folders(args):
    """Validate the provided folder paths."""
    errors = []
    
    if args.image_folder:
        if not os.path.exists(args.image_folder):
            errors.append(f"Image folder does not exist: {args.image_folder}")
        elif not os.path.isdir(args.image_folder):
            errors.append(f"Image folder path is not a directory: {args.image_folder}")
    
    if args.mask_folder:
        if not os.path.exists(args.mask_folder):
            errors.append(f"Mask folder does not exist: {args.mask_folder}")
        elif not os.path.isdir(args.mask_folder):
            errors.append(f"Mask folder path is not a directory: {args.mask_folder}")
    
    if args.output_folder:
        # Try to create output folder if it doesn't exist
        try:
            os.makedirs(args.output_folder, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create output folder {args.output_folder}: {e}")
    
    return errors

def setup_app_with_args(app, args):
    """Setup the application with command line arguments."""
    if args.image_folder:
        app.image_folder = args.image_folder
        app.mask_folder = args.mask_folder
        app.output_folder = args.output_folder
        
        # Set auto-save preference
        if args.no_auto_save:
            app.auto_save = False
        else:
            app.auto_save = args.auto_save
        
        # Find image files
        app.find_image_files()
        
        if app.image_files:
            print(f"Found {len(app.image_files)} images in {args.image_folder}")
            
            # Load the first image
            app.load_current_image()
            
            # Update the auto-save checkbox in the UI
            if hasattr(app, 'auto_save_var'):
                app.auto_save_var.set(app.auto_save)
            
            print("Application loaded successfully with folder configuration.")
            return True
        else:
            print(f"No image files found in {args.image_folder}")
            return False
    
    return False

def main():
    """
    Main function to launch the Enhanced Binary Mask Editor Tool.
    """
    # Parse command line arguments
    args = parse_arguments()
    
    # Validate folders if provided
    if args.image_folder or args.mask_folder or args.output_folder:
        errors = validate_folders(args)
        if errors:
            print("Error: Invalid folder paths:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
    
    # Create the root Tkinter window
    root = tk.Tk()
    root.title("Enhanced Binary Mask Editor Tool")
    
    # Set application icon if available
    try:
        root.iconbitmap('icon.ico')
    except tk.TclError:
        pass  # Icon not found or not supported
    
    # Initialize the application
    app = MaskEditorApp(root)
    
    # If command line arguments were provided, skip the folder setup dialog
    if args.image_folder:
        print("Setting up application with command line arguments...")
        
        # Override the folder setup dialog result
        app.image_folder = args.image_folder
        app.mask_folder = args.mask_folder
        app.output_folder = args.output_folder
        
        # Set auto-save preference
        if args.no_auto_save:
            app.auto_save = False
        else:
            app.auto_save = args.auto_save
        
        # Find image files
        app.find_image_files()
        
        if app.image_files:
            print(f"Found {len(app.image_files)} images in {args.image_folder}")
            
            # Load the first image
            app.load_current_image()
            
            # Update the auto-save checkbox in the UI
            if hasattr(app, 'auto_save_var'):
                app.auto_save_var.set(app.auto_save)
            
            print("Application loaded successfully with folder configuration.")
            print(f"Images: {len(app.image_files)} files")
            print(f"Auto-save: {'Enabled' if app.auto_save else 'Disabled'}")
            
            # Update status to reflect command line setup
            app.status_label.config(text="Ready - Folders configured via command line")
        else:
            print(f"Warning: No image files found in {args.image_folder}")
            app.status_label.config(text="No images found in specified folder")
    
    # Print usage instructions
    print("\nKeyboard Shortcuts:")
    print("  Left/Right arrows: Navigate between images")
    print("  Ctrl+Z: Undo")
    print("  Ctrl+Y: Redo")
    print("  Ctrl+S: Save current mask")
    print("  Escape: Clear selection")
    print("\nTools:")
    print("  Brush: Draw on mask")
    print("  Line: Draw straight lines")
    print("  Select: Rectangle selection")
    print("  Polygon Select: Custom polygon selection")
    print("\nFor detailed instructions, see Help > Instructions in the application menu.")
    
    # Run the application main loop
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        root.quit()
    except Exception as e:
        print(f"Error running application: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()