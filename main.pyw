from PIL import Image
from time import sleep
from usb import core, util
from usb.backend import libusb1
from winotify import Notification
import pystray
import threading
from os import path

BASE_DIR = path.join(path.dirname(__file__))
WIRELESS_RECEIVER = 0x00B7
WIRELESS_WIRED = 0x00B6
TRAN_ID = b"\x1f"
LOOP_TIME = 30


def update_icon():
    global stop
    sleep(2)
    while not stop:
        icon.icon = update_img()
        sleep(LOOP_TIME)


def find_mouse():
    backend = libusb1.get_backend()
    mouse = core.find(idVendor=0x1532, idProduct=WIRELESS_RECEIVER, backend=backend)
    if not mouse:
        mouse = core.find(idVendor=0x1532, idProduct=WIRELESS_WIRED, backend=backend)
    return mouse


def get_mouse():
    mouse = find_mouse()
    while not mouse:
        sleep(1)
        mouse = find_mouse()

    if mouse.idProduct == WIRELESS_RECEIVER:
        return [mouse, True]
    if mouse.idProduct == WIRELESS_WIRED:
        return [mouse, False]


def battery_msg():
    msg = b"\x00" + TRAN_ID + b"\x00\x00\x00\x02\x07\x80"
    crc = 0

    for i in msg[2:]:
        crc ^= i

    msg += bytes(80)
    msg += bytes([crc, 0])

    return msg


def get_battery():
    global wireless
    [mouse, wireless] = get_mouse()
    msg = battery_msg()

    mouse.set_configuration()

    util.claim_interface(mouse, 0)

    mouse.ctrl_transfer(bmRequestType=0x21, bRequest=0x09, wValue=0x300, data_or_wLength=msg, wIndex=0x00)

    util.dispose_resources(mouse)

    result = mouse.ctrl_transfer(bmRequestType=0xA1, bRequest=0x01, wValue=0x300, data_or_wLength=90, wIndex=0x00)

    util.dispose_resources(mouse)
    util.release_interface(mouse, 0)

    return f"{result[9] / 255 * 100:.5f}"


def update_img():
    global prev_battery, wireless
    try:
        battery = float(get_battery())

        if not wireless and battery < 100:
            return Image.open(f"{BASE_DIR}/images/battery_charging.png")

        if prev_battery - battery > 5:
            battery = prev_battery
        prev_battery = battery

        if 25 >= battery > 0:
            return Image.open(f"{BASE_DIR}/images/battery_25.png")
        if 50 >= battery > 25:
            return Image.open(f"{BASE_DIR}/images/battery_50.png")
        if 75 >= battery > 50:
            return Image.open(f"{BASE_DIR}/images/battery_75.png")
        if 100 >= battery > 75:
            return Image.open(f"{BASE_DIR}/images/battery_100.png")
    except:
        return Image.open(f"{BASE_DIR}/images/mouse_image.png")


def on_clicked(icon, item):
    global stop, wireless
    if str(item) == "Stop":
        stop = True
        icon.stop()

    if str(item) == "Check battery":
        update_img()
        battery = float(get_battery())

        title = "Battery"
        if not wireless:
            title = "Charging"

        Notification(app_id="Deathadder V3 Pro  ", title=title, msg=f"{battery:.2f}%", duration="long", icon=f"{BASE_DIR}/images/mouse_image.png").show()


if __name__ == "__main__":
    global stop, prev_battery
    stop = False
    prev_battery = -1

    image = Image.open(f"{BASE_DIR}/images//mouse_image.png")
    icon = pystray.Icon("Mouse Battery ", image, f"Mouse Battery ", menu=pystray.Menu(pystray.MenuItem("Check battery", on_clicked), pystray.MenuItem("Stop", on_clicked)))

    thread = threading.Thread(target=update_icon)
    thread.start()
    icon.run()
