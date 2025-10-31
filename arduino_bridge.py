# Python script to be saved in the system and then be executed
import serial, time, psutil, os, sys, shutil
from pynput.mouse import Controller, Button

# CONFIG — update if necessary
PORT = "/dev/ttyACM0"   # change if your Arduino appears as different device
BAUD = 115200

# feature detection for brightness
HAS_BRIGHTNESSCTL = shutil.which("brightnessctl") is not None
HAS_XBACKLIGHT = shutil.which("xbacklight") is not None
HAS_PACTL = shutil.which("pactl") is not None

# Open serial
try:
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(2)
    ser.reset_input_buffer()
    print("Connected to", PORT)
except Exception as e:
    print("Could not open serial port:", e)
    sys.exit(1)

mouse = Controller()
last_clk = 0
last_move_time = time.time()

def set_volume(adc_value):
    try:
        vol = int((adc_value / 1023.0) * 100)
        if HAS_PACTL:
            os.system(f"pactl set-sink-volume @DEFAULT_SINK@ {vol}% >/dev/null 2>&1")
        else:
            os.system(f"amixer -D pulse sset Master {vol}% >/dev/null 2>&1")
    except Exception:
        pass

def set_brightness(adc_value):
    try:
        pct = int((adc_value / 1023.0) * 100)
        if HAS_BRIGHTNESSCTL:
            os.system(f"brightnessctl set {pct}% >/dev/null 2>&1")
        elif HAS_XBACKLIGHT:
            os.system(f"xbacklight -set {pct} >/dev/null 2>&1")
        else:
            # fallback to sysfs
            bpath = "/sys/class/backlight"
            try:
                entries = os.listdir(bpath)
                if entries:
                    dev = entries[0]
                    maxval = int(open(f"{bpath}/{dev}/max_brightness").read().strip())
                    value = int((pct/100.0) * maxval)
                    with open(f"{bpath}/{dev}/brightness", "w") as f:
                        f.write(str(value))
            except Exception:
                pass
    except Exception:
        pass

def parse_and_act(line):
    global last_clk, last_move_time
    if not line:
        return
    parts = [p.strip() for p in line.split(',')]
    if len(parts) < 5:
        return
    try:
        vol = int(parts[0].split(':')[1])
        bri = int(parts[1].split(':')[1])
        x = int(parts[2].split(':')[1])
        y = int(parts[3].split(':')[1])
        clk = int(parts[4].split(':')[1])
    except Exception:
        return

    # actions
    set_volume(vol)
    set_brightness(bri)

    # joystick -> mouse (deadzone + scaling)
    cx, cy = 512, 512
    dx = x - cx
    dy = y - cy
    dead = 80
    sensitivity = 35
    mx = dx // sensitivity if abs(dx) > dead else 0
    my = dy // sensitivity if abs(dy) > dead else 0

    now = time.time()
    if (mx != 0 or my != 0) and (now - last_move_time > 0.02):
        try:
            mouse.move(mx, -my)  # invert Y
        except Exception:
            pass
        last_move_time = now

    # click on rising edge
    if clk == 1 and last_clk == 0:
        try:
            mouse.click(Button.left)
        except Exception:
            pass
    last_clk = clk

def get_cpu_temp():
    # try psutil sensors
    try:
        temps = psutil.sensors_temperatures()
        if 'coretemp' in temps:
            return int(temps['coretemp'][0].current)
        for k, v in temps.items():
            if v:
                return int(v[0].current)
    except Exception:
        pass
    # fallback to sysfs
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(int(f.read().strip()) / 1000)
    except Exception:
        return 45

try:
    while True:
        try:
            raw = ser.readline().decode(errors='ignore').strip()
            if raw:
                # debug print if needed:
                # print("RX:", raw)
                parse_and_act(raw)

                # send RAM and temp to Arduino
                ram = int(psutil.virtual_memory().percent)
                cpu_temp = get_cpu_temp()
                msg = f"RAM:{ram},{int(cpu_temp)}\n"
                ser.write(msg.encode())

        except serial.SerialException as e:
            print("Serial error:", e)
            time.sleep(0.5)
        except UnicodeDecodeError:
            continue
        time.sleep(0.01)

except KeyboardInterrupt:
    print("Interrupted")
finally:
    ser.close()
