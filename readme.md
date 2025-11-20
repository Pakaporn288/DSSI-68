# PetJoy Project

## Requirements
To run this project on another machine, you need to install the following dependencies:

### Python Packages
- Django==5.2.4
- psycopg2 (for PostgreSQL database connection)
- python-dotenv (for environment variable management)
- PyYAML (if you need YAML serialization)
- google-generativeai (used in `ai_service.py`)

### Installation Steps
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd petjoy_project
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up the `.env` file:
   - Create a `.env` file in the root directory.
   - Add the following variables:
     ```env
     GOOGLE_API_KEY=<your-google-api-key>
     ```

5. Set up the database:
   - Ensure PostgreSQL is installed and running.
   - Create a database and user matching the settings in `settings.py`.
   - Apply migrations:
     ```bash
    CREATE DATABASE Petjoy_db;
        <!-- CREATE USER petjoy_user WITH PASSWORD '12345';
        GRANT ALL PRIVILEGES ON DATABASE Petjoy_db TO petjoy_user; -->
        python manage.py migrate
     ```

6. Run the development server:
   ```bash
   python manage.py runserver
   ```

   



python manage.py loaddata data.yaml โหลดไฟล์ data.yaml
python manage.py loaddata db.json โหลดไฟล์ db.json

### Notes
- Static files are located in the `petjoy/static/` directory.
- Media files are stored in the `media/` directory.
- Default login URL: `/login/`.

### Additional Information
- Make sure to update the `ALLOWED_HOSTS` in `settings.py` for production.
- Use a secure method to store sensitive information like database credentials and API keys.

$env:PYTHONIOENCODING="utf-8"
 python manage.py dumpdata --indent 2 > db.json   แปลงไฟล์

python -Xutf8 manage.py dumpdata --indent 2 -o db.json แก้ endcodring (ภาษาที่เพี้ยน)