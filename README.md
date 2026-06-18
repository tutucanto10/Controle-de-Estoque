🧱 DOMMA — Sistema de Controle de Estoque

Desktop application for corporate IT asset management — built in Python for real production use.

Full-featured system to manage equipment across construction sites: track assets, log transfers, generate reports, and export to PDF/Excel. Built and actively used at DOMMA Incorporações.

✅ Status: Production — running in the field daily.


Features
📦 Stock Control

Register, edit and delete items per construction site
Detailed fields: name, serial number, category, status, condition, notes
Quantity tracking: total · in use · available · under maintenance
Dynamic filters by category, name and status

🔄 Movement Log

Automatic logging of entries, exits, returns and transfers
Logs include: date, responsible, notes, origin/destination site
Safe transfer control between sites

💻 Notebook Module

Individual tracking of corporate notebooks
Statuses: Available · Allocated · Triage · Under Review · Maintenance
Peripheral association (mouse, keyboard, monitor, etc.)
Local SQLite storage with future Supabase sync

📊 Reports & Dashboard

Overview panel with KPIs and interactive charts (Matplotlib)
Filters by period, movement type and site
Export to Excel (.xlsx) and PDF (.pdf)
Charts: "Movements by Type" and "Top 5 Most Moved Items"

📂 Attachments

Upload invoices, receipts and images
Files linked to items with dynamic path stored in the database


Tech Stack
TechRolePython 3.11+Core languageCustomTkinterModern desktop UISQLite / Supabase (PostgreSQL)Local & remote databaseMatplotlibCharts and visualizationsPandas + OpenPyXLExcel exportReportLabPDF report generationasyncpgAsync Supabase sync (upcoming)

Getting Started
bash# 1. Clone the repo
git clone https://github.com/tutucanto10/Controle-de-Estoque.git
cd Controle-de-Estoque

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python controle_estoque.py

Project Structure
Controle-de-Estoque/
├── dist/                  # PyInstaller executables
├── build/                 # Compilation temp files
├── assets/                # Icons, images, PDFs
├── controle_estoque.py    # Application entrypoint
├── db.py                  # Database layer
├── requirements.txt       # Dependencies
└── .gitignore

Build (.exe)
bashpyinstaller --onefile --noconsole --icon=domma.ico \
  --hidden-import=customtkinter \
  --collect-all pandas \
  --collect-all matplotlib \
  --collect-all reportlab \
  controle_estoque.py
Output: dist/controle_estoque.exe

Roadmap

 Full stock control with movement logging
 Notebook module with peripheral tracking
 Dashboard with charts
 PDF and Excel export
 File/attachment upload
 Real-time Supabase sync
 Web dashboard (FastAPI + React)
 Mobile app for stock queries
 QR Code label printing
 Preventive maintenance intelligence
 SharePoint / Microsoft 365 integration


Author
Artur Canto — Python Backend Developer
LinkedIn · Portfolio · GitHub
