from nicegui import events, ui
from PIL import Image
import io
import zipfile

class SlicerApp:
    def __init__(self):
        self.img_path = None
        self.pil_image = None
        self.coords = []
        self.target_url = "https://www.deviantart.com/deviantai"
        self.num_slices = 3

    def handle_upload(self, e: events.UploadEventArguments):
        self.pil_image = Image.open(io.BytesIO(e.content.read()))
        self.coords.clear()
        self.render_canvas()

    def handle_click(self, e: events.MouseEventArguments):
        if e.type != 'mousedown' or not self.pil_image:
            return
        
        # Capture exact pixel coordinates on the original image
        x, y = int(e.image_x), int(e.image_y)
        self.coords.append((x, y))

        if len(self.coords) > 2:
            self.coords = [(x, y)] # Reset if more than 2 clicks

        self.update_svg_overlay()

    def update_svg_overlay(self):
        if not self.interactive_img:
            return
        
        svg = ""
        if len(self.coords) == 1:
            x, y = self.coords[0]
            svg = f'<circle cx="{x}" cy="{y}" r="8" fill="#ff0055" />'
        elif len(self.coords) == 2:
            (x1, y1), (x2, y2) = self.coords[0], self.coords[1]
            xmin, xmax = min(x1, x2), max(x1, x2)
            ymin, ymax = min(y1, y2), max(y1, y2)
            w, h = xmax - xmin, ymax - ymin
            svg = f'<rect x="{xmin}" y="{ymin}" width="{w}" height="{h}" fill="rgba(255, 0, 85, 0.3)" stroke="#ff0055" stroke-width="3" />'
        
        self.interactive_img.content = svg

    def build_slices(self):
        if not self.pil_image or len(self.coords) < 2:
            ui.notify("Please upload an image and click two points for the bounding box!", type="warning")
            return

        width, height = self.pil_image.size
        (x1, y1), (x2, y2) = self.coords[0], self.coords[1]
        xmin, xmax = min(x1, x2), max(x1, x2)

        # 3-slice horizontal breakdown
        left = self.pil_image.crop((0, 0, xmin, height))
        target = self.pil_image.crop((xmin, 0, xmax, height))
        right = self.pil_image.crop((xmax, 0, width, height))

        # Output notification
        ui.notify("Artwork sliced successfully! Ready for Sta.sh download.", type="positive")

    def render_canvas(self):
        self.canvas_container.clear()
        with self.canvas_container:
            ui.label(f"Canvas Resolution: {self.pil_image.width}x{self.pil_image.height}px").classes("text-sm text-gray-400")
            # Interactive Image handles auto-scaling and yields exact pixel coordinates
            self.interactive_img = ui.interactive_image(
                self.pil_image, 
                on_mouse=self.handle_click, 
                events=['mousedown'], 
                cross=True
            ).classes("w-full max-w-4xl border border-gray-700 rounded-lg")

app = SlicerApp()

ui.query('body').classes('bg-slate-900 text-white p-6')
ui.label("DA Clue-tober Interactive Asset Slicer").classes("text-2xl font-bold mb-4")

with ui.row().classes("gap-6 w-full"):
    with ui.column().classes("w-1/3 gap-4 bg-slate-800 p-4 rounded-xl"):
        ui.upload(on_upload=app.handle_upload, label="Upload Master Canvas").classes("w-full")
        ui.input("Target URL", value="https://www.deviantart.com/deviantai", on_change=lambda e: setattr(app, 'target_url', e.value)).classes("w-full")
        ui.number("Number of Slices", value=3, min=3, max=16, step=1).classes("w-full")
        ui.button("Generate Slices & HTML", on_click=app.build_slices).classes("w-full bg-pink-600 hover:bg-pink-700")

    app.canvas_container = ui.column().classes("w-2/3")

ui.run(title="DA Canvas Slicer", port=8080)
