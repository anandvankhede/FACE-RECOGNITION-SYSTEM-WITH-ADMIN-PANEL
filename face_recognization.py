import cv2
import os
import tkinter as tk
import tkinter.messagebox as messagebox
from picamera2 import Picamera2, Preview
from datetime import datetime
import face_recognition
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import sqlite3
from tkinter import ttk

# Global variables to store the captured image and face recognition data
captured_image = None
known_face_encodings = []
known_face_names = []
tree = None  # Define tree globally
admin_authenticated = False  # Variable to track admin authentication status

# Initialize Picamera2
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration({"size": (800, 768)}))
picam2.start_preview(Preview.QTGL)
picam2.start()

# Database initialization
conn = sqlite3.connect('attendance_record.db')
c = conn.cursor()

# Create tables if they do not exist
c.execute('''CREATE TABLE IF NOT EXISTS employees
             (name TEXT PRIMARY KEY, email TEXT, registration_date TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS verify
             (name TEXT, verification_date TEXT)''')

# Function to insert employee record into the database
def insert_employee_record(name, email, registration_date):
    try:
        c.execute("INSERT INTO employees (name, email, registration_date) VALUES (?, ?, ?)",
                  (name, email, registration_date))
        conn.commit()
    except sqlite3.IntegrityError:
        messagebox.showinfo("Duplicate Entry", f"{name} is already registered.")

def insert_verification_record(name, verification_date):
    c.execute("INSERT INTO verify (name, verification_date) VALUES (?, ?)",
              (name, verification_date))
    conn.commit()

# Function to remove employee record from the database
def remove_employee_record(name):
    c.execute("DELETE FROM employees WHERE name=?", (name,))
    conn.commit()

# Function to send email notification with attachment to both user and admin
def send_email_notification_with_attachment(subject, message, image_path, user_email, admin_email):
    # Email configuration
    email_sender = 'wankhedeanand19@gmail.com'  # Your email address
    email_password = 'gemw snna woxs oiqg'  # Your email password

    # Create message container
    msg = MIMEMultipart()
    msg['From'] = email_sender
    msg['Subject'] = subject

    # Append date and time to the message
    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
    message += f"\n\n**Your Company Name**\nDate and Time: {dt_string}"

    # Attach message to the email
    msg.attach(MIMEText(message, 'plain'))

    # Attach image file
    with open(image_path, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(image_path)}')
    msg.attach(part)

    # Add both user and admin email addresses as recipients
    msg['To'] = ', '.join([user_email, admin_email])

    # Send email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)  # For Gmail
        server.starttls()
        server.login(email_sender, email_password)
        server.sendmail(email_sender, [user_email, admin_email], msg.as_string())
        server.quit()
        print(f"Email notification sent to user {user_email} and admin {admin_email} successfully.")
    except Exception as e:
        print("Error sending email notification:", str(e))

# Function to save image and name
def save_image_and_name(known_faces_folder, unknown_name, unknown_email):
    global captured_image
    if unknown_name and captured_image is not None:
        if is_registered(unknown_name):
            messagebox.showinfo("Already Registered", f"{unknown_name} is already registered.")
        else:
            unknown_face_path = os.path.join(known_faces_folder, f"{unknown_name}.jpg")
            cv2.imwrite(unknown_face_path, cv2.cvtColor(captured_image, cv2.COLOR_BGR2RGB))
            messagebox.showinfo("Success", "Successfully registered!")
            cv2.destroyWindow('Captured Image')  # Close the 'Captured Image' window
            known_face_image = face_recognition.load_image_file(unknown_face_path)
            known_face_encoding = face_recognition.face_encodings(known_face_image)
            if known_face_encoding:  # Check if encoding exists
                known_face_encodings.append(known_face_encoding[0])  # Assuming only one face per image
                known_face_names.append(unknown_name)
            else:
                messagebox.showerror("Error", "Unable to encode face.")
            
            # Insert registration record into the database
            insert_employee_record(unknown_name, unknown_email, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            root.deiconify()  # Restore the main window
            send_email_notification_with_attachment("New User Registered", 
                                                     f"New user '{unknown_name}' has been registered.",
                                                     unknown_face_path,
                                                     unknown_email,
                                                     'admin_email@gmail.com')  # Admin email
            return  # Exit the function after closing the windows
    else:
        messagebox.showerror("Error", "Please enter a name and capture an image.")

# Function to capture image using Picamera2
def capture_image():
    array = picam2.capture_array()
    image = array.copy()
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

# Function to detect and verify faces
def detect_and_verify_faces(image, known_face_encodings, known_face_names):
    face_locations = face_recognition.face_locations(image)
    face_encodings = face_recognition.face_encodings(image, face_locations)

    if len(face_encodings) == 0:
        return "Unknown"  # If no faces detected, return "Unknown"

    for face_encoding in face_encodings:
        # Compare face encoding with known face encodings
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)

        for i, match in enumerate(matches):
            if match:
                # Detect smiles
                face_landmarks = face_recognition.face_landmarks(image, [face_locations[i]])
                if 'smile' in face_landmarks[0]:  # Check if smile detected
                    return known_face_names[i]

    return "Unknown"

# Function to check if a person is already registered
def is_registered(name):
    return name in known_face_names

# Function to handle registration process
def register_process(known_faces_folder):
    # Function to capture and save image
    def save_image(register_window):
        global captured_image
        captured_image = capture_image()
        cv2.imshow('Captured Image', cv2.cvtColor(captured_image, cv2.COLOR_BGR2RGB))  
        register_window.destroy()  # Close the registration window after capturing image
        save_image_and_name(known_faces_folder, entry_name.get(), entry_email.get())

    # Create registration window
    register_window = tk.Toplevel(root)
    register_window.title("Register Person")
    register_window.geometry("300x250")  # Set window size

    # Entry for name
    entry_name = tk.Entry(register_window)
    entry_name.placeholder = "Enter name"
    add_placeholder(entry_name, entry_name.placeholder)
    entry_name.pack(pady=10)

    # Entry for email
    entry_email = tk.Entry(register_window)
    entry_email.placeholder = "Enter email"
    add_placeholder(entry_email, entry_email.placeholder)
    entry_email.pack(pady=5)
    
    # Button to capture image
    capture_button = tk.Button(register_window, text="Capture", command=lambda: save_image(register_window))
    capture_button.pack()

# Function to handle verification process
def verify_process():
    # Load known faces from the images in the folder
    known_faces_folder = "known_faces"
    known_face_encodings = []
    known_face_names = []

    for filename in os.listdir(known_faces_folder):
        if filename.endswith(".jpg") or filename.endswith(".png"):
            image_path = os.path.join(known_faces_folder, filename)
            known_face_image = face_recognition.load_image_file(image_path)
            known_face_encoding = face_recognition.face_encodings(known_face_image)
            if known_face_encoding:  # Check if encoding exists
                known_face_encodings.append(known_face_encoding[0])  # Assuming only one face per image
                known_face_names.append(os.path.splitext(filename)[0])

    # Check if there are any known faces saved
    if not known_face_encodings:
        messagebox.showinfo("No Known Faces", "No faces are registered. Please register first.")
        return

    # Main loop for verification process
    while True:
        array = picam2.capture_array()
        image = array.copy()

        # Convert the RGB image to BGR
        bgr_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Detect and verify faces
        name = detect_and_verify_faces(bgr_image, known_face_encodings, known_face_names)

        # If face is not detected, show message
        if name == "Unknown":
            result = messagebox.askokcancel("Face Not Detected", "No face detected. Do you want to continue?")
            if not result:
                break
            continue  # Continue to next iteration of the loop

        # Show a message box with the recognized person's name
        messagebox.showinfo("Recognized", f"Recognized person: {name}")

        # Get the current date and time
        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")

        # Save details to a text file
        with open("attendance.txt", "a") as file:
            file.write(f"Recognized: {name}, Time: {dt_string}\n")

        # Insert verification record into the database
        insert_verification_record(name, dt_string)

        break  # Exit the verification loop if a known face is recognized

# Function to handle removal process
def remove_person():
    # Function to remove person
    def remove_process():
        person_name = remove_entry.get().strip()  # Get the name entered by the user
        if person_name:
            image_path = os.path.join("known_faces", f"{person_name}.jpg")
            if os.path.exists(image_path):  # Check if the image exists
                os.remove(image_path)  # Remove the image file
                messagebox.showinfo("Success", f"{person_name} removed successfully.")
                
                # Remove user record from the database
                remove_employee_record(person_name)
                
                send_email_notification_with_attachment("User Removed", f"User '{person_name}' has been removed.", image_path, person_name, 'admin_email@gmail.com')
            else:
                messagebox.showerror("Error", f"{person_name} not found.")
            remove_window.destroy()  # Close the remove window
        else:
            messagebox.showerror("Error", "Please enter a name.")

    # Create remove window
    remove_window = tk.Toplevel(root)
    remove_window.title("Remove Person")
    remove_window.geometry("300x100")  # Set window size

    # Entry for name to remove
    remove_entry = tk.Entry(remove_window)
    remove_entry.placeholder = "Enter name"
    add_placeholder(remove_entry, remove_entry.placeholder)
    remove_entry.pack(pady=10)

    # Button to remove person
    remove_button = tk.Button(remove_window, text="Remove", command=remove_process)
    remove_button.pack()

# Function to add placeholder text to Entry widget
def add_placeholder(entry, placeholder):
    entry.insert(0, placeholder)
    entry.bind("<FocusIn>", lambda event, e=entry: on_entry_click(event, e))
    entry.bind("<FocusOut>", lambda event, e=entry: on_focus_out(event, e))

def on_entry_click(event, entry):
    if entry.get() == entry.placeholder:
        entry.delete(0, "end")
        if entry.placeholder == "Enter password":  # Check if entry is for password
            entry.config(fg='black', show='*')  # Mask the input with asterisks when the user starts typing
        else:
            entry.config(fg='black')  # Change text color for other entries

def on_focus_out(event, entry):
    if entry.get() == "":
        entry.insert(0, entry.placeholder)
        entry.config(fg='grey')  # Change text color to grey when placeholder is displayed
    if entry.placeholder == "Enter password":  # Check if entry is for password
        entry.config(show='')  # Remove masking when not focused

# Function to initialize face recognition
def initialize_face_recognition():
    global root
    root = tk.Tk()
    root.title("Face Recognition")
    root.geometry("300x150")  # Set window size

    # Frame for buttons
    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)

    # Button for verification
    verify_button = tk.Button(button_frame, text="Verify", command=verify_process)
    verify_button.pack(side=tk.LEFT, padx=10)

    # Button for admin authentication
    admin_button = tk.Button(button_frame, text="Admin", command=admin_authenticate)
    admin_button.pack(side=tk.LEFT, padx=10)

    # Start the Tkinter main loop
    root.mainloop()

# Function to authenticate admin
def admin_authenticate():
    global admin_authenticated  # Use the global variable to track admin authentication

    if not admin_authenticated:  # Check if admin is not already authenticated
        # Function to authenticate the admin
        def authenticate_admin():
            password = entry_password.get().strip()  # Get the password entered by the admin
            if password == "A":  # Change "admin_password" to your actual admin password
                admin_window.deiconify()  # Show the admin window
                auth_window.destroy()  # Close the authentication window
                admin_authenticated = True  # Update admin authentication status
            else:
                messagebox.showerror("Authentication Failed", "Incorrect password.")

        # Create authentication window
        auth_window = tk.Toplevel(root)
        auth_window.title("Admin Authentication")
        auth_window.geometry("200x100")

        # Entry for password
        entry_password = tk.Entry(auth_window, show="*")
        entry_password.placeholder = "Enter Admin Password"
        add_placeholder(entry_password, entry_password.placeholder)
        entry_password.pack(pady=10)

        # Button to authenticate
        auth_button = tk.Button(auth_window, text="Authenticate", command=authenticate_admin)
        auth_button.pack()

        # Create admin window (hidden by default)
        global admin_window
        admin_window = tk.Toplevel(root)
        admin_window.title("Admin Panel")
        admin_window.geometry("600x400")
        admin_window.withdraw()  # Hide the admin window initially

        # Create a Treeview widget to display records in table format
        global tree  # Define tree as global variable
        tree = ttk.Treeview(admin_window, columns=("Name", "Email", "Registration Date"), show="headings")
        tree.heading("Name", text="Name")
        tree.heading("Email", text="Email")
        tree.heading("Registration Date", text="Registration Date")
        tree.pack(expand=True, fill="both")

        # Button for registration
        register_button = tk.Button(admin_window, text="Register", command=lambda: register_process("known_faces"))
        register_button.pack(pady=5)

        # Button for removing person
        remove_button = tk.Button(admin_window, text="Remove", command=remove_person)
        remove_button.pack(pady=5)

        # Button for viewing employee records
        view_button = tk.Button(admin_window, text="View Records", command=view_records)
        view_button.pack(pady=5)
    else:
        admin_window.deiconify()  # If admin is already authenticated, just show the admin window

# Function to view employee records
def view_records():
    global tree  # Ensure that tree variable is recognized as global

    # Retrieve employee records from the database
    c.execute("SELECT * FROM employees")
    records = c.fetchall()

    # Clear existing data in the Treeview
    for record in tree.get_children():
        tree.delete(record)

    # Insert records into the Treeview
    for record in records:
        tree.insert("", "end", values=record)

# Initialize the face recognition window
initialize_face_recognition()
