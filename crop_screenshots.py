"""
Interactive crop tool for screenshots/*.png

Shows the first screenshot in a window. Click and drag to select the region
you want to KEEP. While dragging, everything outside the selection is dimmed
so you can see exactly what will be cut off vs. what remains.

Controls:
    Enter / double-click  -> confirm selection and crop all PNGs
    R                     -> clear selection and redraw
    Esc                   -> cancel, nothing is written
"""
import glob
import os
import sys
import tkinter as tk

from PIL import Image, ImageTk

SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")


def find_pngs():
    files = sorted(glob.glob(os.path.join(SCREENSHOTS_DIR, "*.png")))
    if not files:
        print(f"No PNG files found in {SCREENSHOTS_DIR}")
        sys.exit(1)
    return files


class CropSelector:
    def __init__(self, root, image_path):
        self.root = root
        self.orig = Image.open(image_path).convert("RGB")
        self.img_w, self.img_h = self.orig.size

        screen_w = root.winfo_screenwidth() - 100
        screen_h = root.winfo_screenheight() - 160
        self.scale = min(screen_w / self.img_w, screen_h / self.img_h, 1.0)
        disp_w = int(self.img_w * self.scale)
        disp_h = int(self.img_h * self.scale)

        self.display_img = self.orig.resize((disp_w, disp_h), Image.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(self.display_img)

        self.info = tk.Label(
            root,
            text="Click and drag to select the region to KEEP. Enter=confirm  R=redo  Esc=cancel",
            font=("Segoe UI", 10),
        )
        self.info.pack(pady=(6, 2))

        self.canvas = tk.Canvas(root, width=disp_w, height=disp_h, highlightthickness=0)
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

        self.dims_label = tk.Label(root, text="", font=("Segoe UI", 10, "bold"))
        self.dims_label.pack(pady=(2, 6))

        self.start = None
        self.rect_id = None
        self.dim_ids = []
        self.selection = None  # (x0, y0, x1, y1) in display coords
        self.confirmed = False

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", lambda e: self.confirm())
        root.bind("<Return>", lambda e: self.confirm())
        root.bind("<Escape>", lambda e: self.cancel())
        root.bind("r", lambda e: self.reset())
        root.bind("R", lambda e: self.reset())

        self.disp_w, self.disp_h = disp_w, disp_h

    def clear_overlays(self):
        for i in self.dim_ids:
            self.canvas.delete(i)
        self.dim_ids = []
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None

    def on_press(self, event):
        self.start = (max(0, min(event.x, self.disp_w)), max(0, min(event.y, self.disp_h)))
        self.clear_overlays()

    def on_drag(self, event):
        if not self.start:
            return
        x0, y0 = self.start
        x1 = max(0, min(event.x, self.disp_w))
        y1 = max(0, min(event.y, self.disp_h))
        self.draw_selection(x0, y0, x1, y1)

    def on_release(self, event):
        if not self.start:
            return
        x0, y0 = self.start
        x1 = max(0, min(event.x, self.disp_w))
        y1 = max(0, min(event.y, self.disp_h))
        left, right = sorted((x0, x1))
        top, bottom = sorted((y0, y1))
        if right - left < 2 or bottom - top < 2:
            self.selection = None
            self.dims_label.config(text="Selection too small - try again.")
            return
        self.selection = (left, top, right, bottom)
        self.draw_selection(left, top, right, bottom)
        real_w = round((right - left) / self.scale)
        real_h = round((bottom - top) / self.scale)
        real_x = round(left / self.scale)
        real_y = round(top / self.scale)
        self.dims_label.config(
            text=f"Keep region: {real_w}x{real_h} at ({real_x},{real_y})  "
            f"|  cut: left {real_x}px, top {real_y}px, "
            f"right {self.img_w - real_x - real_w}px, bottom {self.img_h - real_y - real_h}px  "
            f"-- Enter to confirm, R to redo"
        )

    def draw_selection(self, x0, y0, x1, y1):
        self.clear_overlays()
        left, right = sorted((x0, x1))
        top, bottom = sorted((y0, y1))

        # Dim everything outside the selection so it's obvious what gets cut.
        regions = [
            (0, 0, self.disp_w, top),           # above
            (0, bottom, self.disp_w, self.disp_h),  # below
            (0, top, left, bottom),             # left
            (right, top, self.disp_w, bottom),  # right
        ]
        for (rx0, ry0, rx1, ry1) in regions:
            if rx1 > rx0 and ry1 > ry0:
                rid = self.canvas.create_rectangle(
                    rx0, ry0, rx1, ry1, fill="black", stipple="gray50", outline=""
                )
                self.dim_ids.append(rid)

        self.rect_id = self.canvas.create_rectangle(
            left, top, right, bottom, outline="#00ff88", width=2
        )

    def reset(self):
        self.start = None
        self.selection = None
        self.clear_overlays()
        self.dims_label.config(text="")

    def confirm(self):
        if not self.selection:
            self.dims_label.config(text="No selection yet - drag to select first.")
            return
        self.confirmed = True
        self.root.quit()

    def cancel(self):
        self.confirmed = False
        self.root.quit()

    def get_crop_box(self):
        left, top, right, bottom = self.selection
        x0 = round(left / self.scale)
        y0 = round(top / self.scale)
        x1 = round(right / self.scale)
        y1 = round(bottom / self.scale)
        return (x0, y0, x1, y1)


def main():
    files = find_pngs()
    first = files[0]
    print(f"Opening {first} for region selection...")

    root = tk.Tk()
    root.title(f"Select crop region - {os.path.basename(first)}")
    selector = CropSelector(root, first)
    root.mainloop()
    root.destroy()

    if not selector.confirmed:
        print("Cancelled - no files were modified.")
        return

    box = selector.get_crop_box()
    print(f"Applying crop box {box} (left, top, right, bottom) to {len(files)} file(s)...")

    for f in files:
        with Image.open(f) as im:
            cropped = im.crop(box)
            cropped.save(f)
        print(f"  cropped: {f} -> {cropped.size}")

    print("Done.")


if __name__ == "__main__":
    main()
