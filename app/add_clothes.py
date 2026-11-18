from main import SessionLocal, ClothingItem
import tkinter as tk
from pathlib import Path
import shutil
from tags import ALL_CATEGORIES
from PIL import Image, ImageTk

"""
GUI tool to add clothes to the database with manual tagging.
"""

def main(session):
    root = tk.Tk()
    root.geometry("1400x800")  # make window bigger

    files = Path("~/workspace/data/wardrobe/stage3").expanduser().glob("*.jpg")
    # only use images not already in static/images
    files = [p for p in files if not (Path("app/static/images") / p.name).is_file()]
    clothes = []
    i = 0
    img_obj = None

    # --- IMAGE ---
    image_label = tk.Label(root)
    image_label.pack(pady=10)

    def show():
        nonlocal img_obj
        image = Image.open(files[i])
        image = image.resize((500, 500))
        img_obj = ImageTk.PhotoImage(image)
        image_label.config(image=img_obj)

    # --- FEATURES ROW ---
    features_frame = tk.Frame(root)
    features_frame.pack(pady=10)

    features = {}
    for cat, options in ALL_CATEGORIES.items():
        frame = tk.Frame(features_frame)

        label = tk.Label(frame, text=cat)
        label.pack()

        feature = tk.Listbox(frame, selectmode="multiple", height=8, width=18, exportselection=False)
        for item in options:
            feature.insert(tk.END, item)
        feature.pack()

        frame.pack(side="left", padx=10)
        features[cat] = feature

    # --- CORRUPTION CHECK ---
    button_frame = tk.Frame(root)
    button_frame.pack(pady=20)

    corrupted_var = tk.BooleanVar(value=False)
    corrupted_check = tk.Checkbutton(button_frame, text="Mark Corrupted", variable=corrupted_var)
    corrupted_check.pack(side="left", padx=10)

    # --- SUBMIT BUTTON ---
    def submit():
        nonlocal i

        img_path = Path("app/static/images") / files[i].name
        shutil.copy(files[i], img_path)

        if corrupted_var.get():
            # mark as corrupted and skip tagging
            item = ClothingItem(image_path=img_path.name, tags="corrupted")
        else:
            # normal tagging
            tags = [
                f"{name}:{feat.get(x)}"
                for name, feat in features.items()
                for x in feat.curselection()
            ]
            item = ClothingItem(image_path=img_path.name, tags=",".join(tags))
        session.add(item)
        session.commit()

        for feat in features.values():
            feat.selection_clear(0, tk.END)
        corrupted_var.set(False)

        i += 1
        if i < len(files):
            show()
        else:
            image_label.config(text="Done", image="")
            button.config(state="disabled")
            corrupted_check.config(state="disabled")

    button = tk.Button(button_frame, text="submit", command=submit)
    button.pack(side="left", padx=10)

    show()
    root.mainloop()


if __name__ == "__main__":
    session = SessionLocal()
    main(session)
    session.close()


