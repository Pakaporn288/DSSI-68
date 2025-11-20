# PetJoy Project

## Overview
PetJoy is a Django-based project designed to manage and showcase pet-related products. This guide provides all the necessary steps to set up and run the project on another machine.

---

## Requirements
To run this project, ensure the following dependencies are installed:

### Python Packages
- **Django==5.2.4**: Web framework for the project.
- **psycopg2**: PostgreSQL database adapter.
- **python-dotenv**: For managing environment variables.
- **PyYAML**: For YAML serialization (optional).
- **google-generativeai**: Used in `ai_service.py`.

---

## Installation Steps

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
- Create a `.env` file in the root directory.
- Add the following variables:
  ```env
  GOOGLE_API_KEY=<your-google-api-key>
  ```

### 5. Set Up the Database
- Ensure PostgreSQL is installed and running.
- Create a database and user matching the settings in `settings.py`:
  ```sql
  CREATE DATABASE Petjoy_db;
  CREATE USER petjoy_user WITH PASSWORD '12345';
  GRANT ALL PRIVILEGES ON DATABASE Petjoy_db TO petjoy_user;
  ```
- Apply migrations:
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
- **Static Files**: Located in the `petjoy/static/` directory.
- **Media Files**: Stored in the `media/` directory.
- **Default Login URL**: `/login/`.

---

## Additional Information
- Update the `ALLOWED_HOSTS` in `settings.py` for production.
- Use a secure method to store sensitive information like database credentials and API keys.

---

## Encoding and Data Dump Tips
- To avoid encoding issues, use the following commands:
  ```bash
  $env:PYTHONIOENCODING="utf-8"
  python manage.py dumpdata --indent 2 > db.json
  ```
- Alternatively, use:
  ```bash
  python -Xutf8 manage.py dumpdata --indent 2 -o db.json
  ```