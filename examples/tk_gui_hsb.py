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

b = Bridge()  # Enter bridge IP here.

# If running for the first time, press button on bridge and run with b.connect() uncommented
# b.connect()

root = Tk()

lights = b.get_light_objects("id")
light_selection: list[int] = []


def hue_command(x: str) -> None:
    if len(light_selection) > 0:
        b.set_light(light_selection, "hue", int(x))


def sat_command(x: str) -> None:
    if len(light_selection) > 0:
        b.set_light(light_selection, "sat", int(x))


def bri_command(x: str) -> None:
    if len(light_selection) > 0:
        b.set_light(light_selection, "bri", int(x))


def button_command(light_id: int, button_state: BooleanVar) -> None:
    b.set_light(light_id, "on", button_state.get())


def select_button_command(light: int, button_state: BooleanVar) -> None:
    global light_selection
    if button_state.get():
        light_selection.append(light)
    else:
        light_selection.remove(light)
    print(light_selection)


slider_frame = Frame(root)
slider_frame.pack(pady=10)

channels_frame = Frame(root)
channels_frame.pack()

label_frame = Frame(channels_frame)
label_frame.pack(side=LEFT, padx=10)

label_state = Label(label_frame)
label_state.config(text="State")
label_state.pack()

label_select = Label(label_frame)
label_select.config(text="Select")
label_select.pack()

label_name = Label(label_frame)
label_name.config(text="Name")
label_name.pack()

hue_slider = Scale(slider_frame, from_=65535, to=0, command=hue_command)
sat_slider = Scale(slider_frame, from_=254, to=0, command=sat_command)
bri_slider = Scale(slider_frame, from_=254, to=0, command=bri_command)
hue_slider.pack(side=LEFT)
sat_slider.pack(side=LEFT)
bri_slider.pack(side=LEFT)


for light_id in lights:
    channel_frame = Frame(channels_frame)
    channel_frame.pack(side=LEFT, padx=10)

    button_var = BooleanVar()
    button_var.set(b.get_light(light_id, "on"))
    button = Checkbutton(
        channel_frame,
        variable=button_var,
        command=lambda light_id=light_id, button_var=button_var: button_command(
            int(light_id), button_var
        ),
    )
    button.pack()

    select_button_var = BooleanVar()
    # select_button_var.set(b.get_light(light_id, 'on'))
    select_button_callback = partial(
        select_button_command, int(light_id), select_button_var
    )
    select_button = Checkbutton(
        channel_frame, variable=select_button_var, command=select_button_callback
    )
    select_button.pack()

    label = Label(channel_frame)
    label.config(text=b.get_light(light_id, "name"))
    label.pack()

root.mainloop()
