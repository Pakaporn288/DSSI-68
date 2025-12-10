# PetJoy Project

## ภาพรวม
PetJoy เป็นโครงการที่ใช้ Django ออกแบบมาเพื่อจัดการและจัดแสดงผลิตภัณฑ์ที่เกี่ยวข้องกับสัตว์เลี้ยง คู่มือนี้อธิบายขั้นตอนที่จำเป็นทั้งหมดในการตั้งค่าและรันโครงการบนเครื่องอื่น

---

## ความต้องการ
ในการรันโครงการนี้ โปรดตรวจสอบให้แน่ใจว่ามีการติดตั้งส่วนที่ต้องมีต่อไปนี้:

### Python Packages
- **Django==5.2.4**: เฟรมเวิร์กเว็บสำหรับโครงการ
- **psycopg2**: อะแดปเตอร์ฐานข้อมูล PostgreSQL
- **python-dotenv**: สำหรับการจัดการตัวแปรสภาพแวดล้อม
- **PyYAML**: สำหรับการทำ serialization ของ YAML (ไม่บังคับ)
- **google-generativeai**: ใช้ใน `ai_service.py`

---

## ขั้นตอนการติดตั้ง

### 1. Clone the Repository
```bash
git clone <repository-url>
cd petjoy_project
```

### 2. Create and Activate a Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Required Packages
```bash
pip install -r requirements.txt
```

### 4. Set Up the `.env` File
- สร้างไฟล์ `.env` ในไดเร็กทอรีรูท
- เพิ่มตัวแปรต่อไปนี้:
  ```env
  GOOGLE_API_KEY=<your-google-api-key>
  ```
- ถ้าใช้ PostgreSQL:
  ```
  DB_NAME=Petjoy_db
  DB_USER=petjoy_user
  DB_PASSWORD=12345
  DB_HOST=localhost
  DB_PORT=5432
  ```

### 5. Set Up the Database
- ตรวจสอบให้แน่ใจว่าติดตั้งและใช้งาน PostgreSQL เรียบร้อยแล้ว
- สร้างฐานข้อมูลและผู้ใช้ที่ตรงกับการตั้งค่าใน `settings.py`:
  ```sql
  CREATE DATABASE Petjoy_db;
  CREATE USER petjoy_user WITH PASSWORD '12345';
  GRANT ALL PRIVILEGES ON DATABASE Petjoy_db TO petjoy_user;
  ```
- จากนั้น migrations:
  ```bash
  python manage.py migrate
  ```

### 6. Load Data (Optional)
- Load data from `data.yaml`:
  ```bash
  python manage.py loaddata data.yaml
  ```
- Or load data from `db.json`:
  ```bash
  python manage.py loaddata db.json
  ```

### 7. Run the Development Server
```bash
python manage.py runserver
```

---

## Notes
- **ไฟล์คงที่**: อยู่ในไดเร็กทอรี `petjoy/static/`
- **ไฟล์สื่อ**: เก็บไว้ในไดเร็กทอรี `media/`
- **URL ล็อกอินเริ่มต้น**: `/login/`

---



## การ Dump & Restore Database
- Dump JSON
  ```bash
  python -Xutf8 manage.py dumpdata --indent 2 -o db.json
  ```
- แปลง JSON → YAML
- ภายในโปรเจกต์มีไฟล์:
  ```bash
  json_to_yaml.py
  ```
- ใช้งานดังนี้:
  ```bash
  python json_to_yaml.py
  ```
- ผลลัพธ์จะได้ data.yaml