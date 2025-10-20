# 🧠 Face Recognition Attendance System

An **AI-powered attendance system** that uses **Face Recognition** for secure and automated student attendance tracking.
Built with **React.js** (Frontend), **Flask** (Backend), and **FaceNet with MTCNN** (Machine Learning Model) for accurate face detection and recognition.

---

## 📋 Features

* 👤 **Automated Face Recognition** using MTCNN + FaceNet Embedding.
* 🧾 **Attendance Logging** with time and student details.
* 🔐 **Secure Admin Access** via Flask APIs with SSL configuration.
* 📊 **Dashboard Visualization** showing daily and weekly attendance reports.
* 🧍‍♂️ **Student Enrollment Module** to register new users via webcam.
* 🌐 Responsive Web Interface built with React.js — accessible on both desktop and mobile devices for flexible usage.

---

## 🛠️ Technologies Used

| Component            | Technology             |
| -------------------- | ---------------------- |
| **Frontend**         | React.js               |
| **Backend**          | Flask (Python)         |
| **Database**         | SQLite                 |
| **Machine Learning** | OpenCV, FaceNet, MTCNN |
| **Security**         | SSL Certificates       |
| **Language**         | JavaScript, Python     |


## ⚙️ Installation & Setup

### **1. Clone the Repository**

```bash
git clone https://github.com/<your-username>/Face-Attendance-System.git
cd Face-Attendance-System
```

---

### **2. Install Dependencies**

#### **Frontend**

```bash
npm install
cd ..
```

#### **Backend**

```bash
cd facenet
pip install -r requirements.txt
cd ..
```

---

### **3. Generate SSL Certificates (You can skip this step if you want only Localhost)**

**Install the Local CA (First time only and needs mkcert installed on your system)**

```bash
mkcert -install
```

**Generate Certificate (Enter your wifi ip to host it over that wifi or simply pust localhost)**

```bash
mkcert {Your IP}
```

Note :- Make changes into all jsx fiiles, app.py file and vite.config.js and use the same ip everywhere

---

### **4. Run the Application**

> Open **two terminals** from the project root:

**Terminal 1 – Frontend**

```bash
npm run dev
```

**Terminal 2 – Backend**

```bash
python facenet/app.py
```

* React runs on: `http://localhost:5173`
* Flask API runs on: `http://localhost:5000`

Note:- Put your ip instead of localhost if you want to host it

---
