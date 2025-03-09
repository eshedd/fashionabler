import os
from rembg import remove, new_session

print('Creating rembg session...')
session = new_session()

print('Segmenting images...')
input_dir = "imgs/flatlay/"
output_dir = "imgs/segmented/"
for img_file in os.listdir(input_dir):
    print(img_file)
    input_path = os.path.join(input_dir, img_file)
    output_path = os.path.join(output_dir, img_file)
    with open(input_path, 'rb') as i:
        with open(output_path, 'wb') as o:
            input = i.read()
            output = remove(  # Auto-removes background
                data=input,
                session=session,
                bgcolor=(255, 255, 255, 255)
            )
            o.write(output)
