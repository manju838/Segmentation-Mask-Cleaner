# Segmentation-Mask-Cleaner

This tool expects an image and a binary segmentation mask as input and helps clean up any islands or noise in the segmentation mask.

TODOs:

1) Bugs/Modifications in Mask Cleaner code
<br>[] The image and the mask selected should be displayed all the times on status bar, else getting confused about what to save the cleaned mask as.    
<br>[x] ~~Brush Settings size should be accept integers for brushsize~~
<br>[] Polygon created using "Polygon Select" is not transforming with mouse scroll
<br>[] Need a method to identify files and masks without loading them seperately for each image
<br>[x] ~~Escape btn to deselect any functionality~~
<br>[] Once I move to a different image, the functionality that is active should become inactive, for eg, if Polygon Select is active, after I save and move to a different image, this should be deactivated and the polygon should vanish. 

Erraneous errors in terminal even though app is functioning:<br>
[]<br>
```bash
Traceback (most recent call last):
File "C:\Users\manju\.conda\envs\wall2_env\lib\tkinter\__init__.py", line 1892, in __call__
return self.func(*args)
File "C:\Users\manju\Downloads\temp_test\Mask_Cleaner\new_version\mask_editor.py", line 150, in <lambda>
value="brush", command=lambda: self.set_tool("brush")).pack(side=tk.LEFT, padx=5)
File "C:\Users\manju\Downloads\temp_test\Mask_Cleaner\new_version\mask_editor.py", line 575, in set_tool
self.clear_polygon_selection()
File "C:\Users\manju\Downloads\temp_test\Mask_Cleaner\new_version\mask_editor.py", line 597, in clear_polygon_selection
if self.temp_line:
AttributeError: 'MaskEditorApp' object has no attribute 'temp_line'
```


1) New feature additions
<br>[] Add a SAM2 segmentation that uses GPU, it should have all functionality present in the online huggingface based SAM2 segmentation tool found [here](https://huggingface.co/spaces/yumyum2081/SAM2-Image-Predictor)

<br>[] A Postprocessing method that traces a line for the  


Usage:
```bash
python launch_editor.py
```