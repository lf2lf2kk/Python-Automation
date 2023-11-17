from PIL import Image
import os

def resize_image(input_path, max_width=1080):
    with Image.open(input_path) as img:
        if img.size[0] <= max_width:
            return
        
        width_percent = (max_width / float(img.size[0]))
        new_height = int((float(img.size[1]) * float(width_percent)))

        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        img.save(input_path)

def resize_images_in_folder(folder_path):
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            input_path = os.path.join(folder_path, filename)
            resize_image(input_path)

folder_path = './assets' 
resize_images_in_folder(folder_path)
