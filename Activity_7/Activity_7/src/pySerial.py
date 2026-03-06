import serial
import time
import sys

# --- Configuration ---
SERIAL_PORT = 'COM5'
BAUD_RATE = 9600
SERVO_MIN_ANGLE = 0
SERVO_MAX_ANGLE = 180

def get_valid_angle_input():
    while True:
        try:
            user_input = input("\nEnter desired servo angle (0-180): ")
            angle = int(user_input)

            if not (SERVO_MIN_ANGLE <= angle <= SERVO_MAX_ANGLE):
                print(f"Error: Range 0-180 only.")
                continue

            while True:
                confirm = input(f"Confirm {angle}°? (Y/N): ").upper()
                if confirm == 'Y': return angle
                elif confirm == 'N': break
                else: print("Invalid Y/N input.")
        except ValueError:
            print("Error: Numbers only.")

def main():
    ser = None
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) 

        while True:
            angle_to_send = get_valid_angle_input()
            command = f"{angle_to_send}\n"
            ser.write(command.encode('utf-8'))
            print(f"Sent: {angle_to_send}°")
            time.sleep(0.1)
    except serial.SerialException as e:
        print(f"Serial Error: {e}")
    finally:
        if ser and ser.is_open: ser.close()

if __name__ == "__main__":
    main()