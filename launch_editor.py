#!/usr/bin/env python3
"""
# python launch_editor.py inpainting_test_images/test1.png inpainting_test_images/og_mask_test1_cleaned.png

Launcher for the Binary Mask Editor Tool

This script initializes and launches the Binary Mask Editor application, 
which allows users to edit and clean binary masks generated from
segmentation models like SAM2 (Segment Anything Model 2).
"""

import os
import sys
import tkinter as tk
import cv2
from mask_editor import MaskEditorApp

def main():
    """
    Main function to launch the Binary Mask Editor Tool.
    
    You can provide paths to the image and mask as command line arguments, 
    or they will be loaded from within the application using the file dialogs.
    
    Usage:
        python launch_editor.py [image_path] [mask_path]
    
    Args:
        image_path (optional): Path to the input image file
        mask_path (optional): Path to the binary mask file
    """
    # Create the root Tkinter window
    root = tk.Tk()
    
    # Set window title
    root.title("Binary Mask Editor Tool")
    
    # Initialize the application
    app = MaskEditorApp(root)
    
    # Set application icon if available
    try:
        root.iconbitmap('icon.ico')
    except tk.TclError:
        pass  # Icon not found or not supported
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        # Get the image path from the first argument
        image_path = sys.argv[1]
        
        # Verify the image file exists
        if os.path.isfile(image_path):
            # Set the image path in the application
            app.image_path = image_path
            
            # Load the image using OpenCV
            app.original_image = cv2.imread(image_path)
            
            # Check if image was loaded successfully
            if app.original_image is None:
                print(f"Error: Failed to load image {image_path}")
            else:
                # Convert BGR to RGB for display (OpenCV uses BGR by default)
                app.original_image = cv2.cvtColor(app.original_image, cv2.COLOR_BGR2RGB)
                
                # If mask path is provided as the second argument
                if len(sys.argv) > 2:
                    mask_path = sys.argv[2]
                    if os.path.isfile(mask_path):
                        app.mask_path = mask_path
                        
                        # Load the mask as grayscale
                        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                        
                        if mask is None:
                            print(f"Error: Failed to load mask {mask_path}")
                        else:
                            # Ensure the mask has the same dimensions as the image
                            if mask.shape != (app.original_image.shape[0], app.original_image.shape[1]):
                                print("Warning: Resizing mask to match image dimensions")
                                mask = cv2.resize(mask, (app.original_image.shape[1], app.original_image.shape[0]))
                            
                            # Binarize the mask (ensure it's strictly black and white)
                            _, app.mask_image = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
                
                # Update the display with the loaded image/mask
                app.update_display()
                print(f"Loaded image: {os.path.basename(image_path)}")
                if len(sys.argv) > 2 and app.mask_image is not None:
                    print(f"Loaded mask: {os.path.basename(mask_path)}")
    
    # Run the application main loop
    root.mainloop()

if __name__ == "__main__":
    main()