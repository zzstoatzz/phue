"""
This example creates 3 sliders for the first 3 lights
and shows the name of the light under each slider.
There is also a checkbox to toggle the light.

WARNING: If you have not previously connected to the bridge, run connect_bridge.py first.
"""

from functools import partial
from tkinter import (
    LEFT,
    BooleanVar,
    Checkbutton,
    Frame,
    Label,
    Scale,
    Tk,
)

from phue import Bridge


def scale_command(x: str, light_id: int) -> None:
    b.set_light(light_id, {"bri": int(x), "transitiontime": 1})


def button_command(button_var: BooleanVar, light_id: int) -> None:
    b.set_light(light_id, "on", button_var.get())


b = Bridge()  # Enter bridge IP here.

# If running for the first time, press button on bridge and run with b.connect() uncommented
# b.connect()

root = Tk()

horizontal_frame = Frame(root)
horizontal_frame.pack()

lights = b.get_light_objects("id")

for light_id in lights:
    channel_frame = Frame(horizontal_frame)
    channel_frame.pack(side=LEFT)

    scale = Scale(
        channel_frame,
        from_=254,
        to=0,
        command=partial(scale_command, light_id=light_id),
        length=200,
        showvalue=False,
    )
    scale.set(b.get_light(light_id, "bri"))  # type: ignore
    scale.pack()

    button_var = BooleanVar()
    button_var.set(b.get_light(light_id, "on"))
    button = Checkbutton(
        channel_frame,
        variable=button_var,
        command=partial(button_command, button_var, light_id),
    )
    button.pack()

    label = Label(channel_frame)
    label.config(text=b.get_light(light_id, "name"))
    label.pack()

root.mainloop()
