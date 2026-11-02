"""0.96" SSD1306 OLED (128x64): text output, with a mirrored mode for the HUD.

The beam splitter reflects the screen, which flips it left to right. Turning on
`mirror` flips the image first so the reflection reads correctly.

Run on the Pi to show a test message (add --mirror for the HUD view):
    cd src && python -m glasses.display "Hello World"
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont, ImageOps

I2C_BUS = 1
ADDRESS = 0x3C
WIDTH = 128
HEIGHT = 64


def open_oled():
    """Connect to the real OLED over I2C."""
    from luma.core.interface.serial import i2c
    from luma.oled.device import ssd1306

    return ssd1306(i2c(port=I2C_BUS, address=ADDRESS), width=WIDTH, height=HEIGHT)


class Display:
    def __init__(self, device=None, mirror: bool = False, font=None):
        self.device = device if device is not None else open_oled()
        self.mirror = mirror
        self.font = font or ImageFont.load_default()
        left, top, right, bottom = self.font.getbbox("Mg")
        self.line_height = bottom - top + 2

    @property
    def max_lines(self) -> int:
        return self.device.height // self.line_height

    def render(self, lines: list[str]) -> Image.Image:
        """Draw text lines into an image the size of the screen (mirrored if set)."""
        image = Image.new("1", (self.device.width, self.device.height), 0)
        draw = ImageDraw.Draw(image)
        for i, line in enumerate(lines[: self.max_lines]):
            draw.text((0, i * self.line_height), line, font=self.font, fill=1)
        if self.mirror:
            image = ImageOps.mirror(image)
        return image

    def show_lines(self, lines: list[str]) -> None:
        """Show each string on its own line. Extra lines are cut off."""
        self.device.display(self.render(lines).convert(self.device.mode))

    def wrap(self, text: str) -> list[str]:
        """Split text into lines that fit the screen width, breaking at spaces."""
        lines: list[str] = []
        for paragraph in text.splitlines() or [""]:
            line = ""
            for word in paragraph.split():
                candidate = f"{line} {word}" if line else word
                if line and self.font.getlength(candidate) > self.device.width:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
        return lines

    def show_text(self, text: str) -> None:
        """Show text, wrapping long lines to fit the screen."""
        self.show_lines(self.wrap(text))

    def clear(self) -> None:
        self.device.clear()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Show text on the OLED.")
    parser.add_argument("text", nargs="?", default="Hello World")
    parser.add_argument("--mirror", action="store_true", help="flip for the beam splitter")
    args = parser.parse_args()

    display = Display(mirror=args.mirror)
    display.show_text(args.text)
    input("Showing text. Press Enter to clear and exit.")
    display.clear()


if __name__ == "__main__":
    main()
