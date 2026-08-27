ProMAT – Project Management Tool
Prehľad
Stručný popis: Interný systém na správu projektov s úlohami, dokumentmi a rolami. Umožňuje nahrávať PDF a DOCX súbory a pracovať s nimi cez projekty a úlohy. Všetko beží lokálne, dáta neopúšťajú firmu.

Cieľ projektu: Prepojiť projektový manažment s prácou nad dokumentmi tak, aby tím v jednom nástroji plánoval, ukladal a spravoval kľúčové informácie z príloh.


Architektúra
Vrstva
Technológia
Frontend
Jinja2 templates + Tailwind CSS (CDN) + vanilla JS
Backend
Python 3.11+ / Flask
Databáza
SQLite (cez SQLAlchemy ORM)
Ukladanie súborov
Lokálny súborový systém (uploads/)


Dizajnový vzor: template.html. Dark-mode-first, font Space Grotesk, ikony Material Symbols, Tailwind CSS utility classes, plne responzívne (mobile-first breakpoints).


Kľúčové funkcie
Projekty a úlohy: CRUD projektov, kanban zoznamy, úlohy s termínmi, priradenými riešiteľmi, komentármi, statusom a prioritou
Dokumenty: Nahrávanie PDF/DOCX, automatická extrakcia textu, verzovanie, tagy
Role a oprávnenia: admin, owner, advocate, koncipient, sekretariát
Dashboard: Štatistiky v reálnom čase, priebeh projektov, posledné úlohy, posledné dokumenty


Štruktúra projektu (cieľový stav)
ProMAT/

├── README.md                    # Tento súbor – plán a sledovanie priebehu

├── template.html                # Dizajnový vzor (read-only)

├── requirements.txt             # Python závislosti

├── config.py                    # Konfigurácia appky (SECRET_KEY, DB URI, cesta na upload)

├── run.py                       # Vstupný bod – `python run.py`

├── app/

│   ├── __init__.py              # Flask app factory, registrácia blueprintov

│   ├── extensions.py            # Inštancie SQLAlchemy, LoginManager, CSRFProtect

│   ├── models/

│   │   ├── __init__.py

│   │   ├── user.py              # Model User (role, autentifikácia)

│   │   ├── project.py           # Model Project

│   │   ├── task.py              # Model Task (status, priorita, riešiteľ)

│   │   ├── document.py          # Model Document (metadáta súboru, extrahovaný text)

│   │   └── comment.py           # Model Comment (pri úlohách)

│   ├── blueprints/

│   │   ├── __init__.py

│   │   ├── auth.py              # Routy pre login, logout, registráciu

│   │   ├── dashboard.py         # Route pre dashboard (hlavná stránka)

│   │   ├── projects.py          # CRUD routy pre projekty

│   │   ├── tasks.py             # CRUD routy pre úlohy + kanban

│   │   ├── documents.py         # Routy pre upload, zoznam, detail dokumentov

│   │   └── team.py              # Routy pre správu tímu / používateľov

│   ├── services/

│   │   ├── __init__.py

│   │   └── document_service.py  # Logika extrakcie textu z PDF/DOCX

│   ├── templates/

│   │   ├── base.html            # Základný layout (sidebar, header, footer)

│   │   ├── components/

│   │   │   ├── sidebar.html     # Partial pre navigáciu v sidebari

│   │   │   ├── header.html      # Partial pre horný header

│   │   │   ├── footer.html      # Partial pre footer

│   │   │   ├── stats_card.html  # Znovupoužiteľná komponenta pre stat kartu

│   │   │   ├── project_row.html # Komponenta pre riadok priebehu projektu

│   │   │   ├── task_row.html    # Komponenta pre riadok tabuľky úloh

│   │   │   ├── document_card.html # Komponenta pre položku zoznamu dokumentov

│   │   │   └── modal.html       # Generická komponenta modálu

│   │   ├── auth/

│   │   │   ├── login.html

│   │   │   └── register.html

│   │   ├── dashboard/

│   │   │   └── index.html       # Stránka dashboardu (podľa template.html)

│   │   ├── projects/

│   │   │   ├── list.html

│   │   │   ├── detail.html

│   │   │   └── form.html        # Formulár na vytvorenie/úpravu projektu

│   │   ├── tasks/

│   │   │   ├── list.html        # Tabuľkový pohľad na úlohy

│   │   │   ├── kanban.html      # Kanban pohľad

│   │   │   └── form.html        # Formulár na vytvorenie/úpravu úlohy

│   │   ├── documents/

│   │   │   ├── list.html

│   │   │   ├── detail.html      # Detail dokumentu + extrahovaný text

│   │   │   └── upload.html

│   │   └── team/

│   │       ├── list.html

│   │       └── form.html        # Pozvanie / úprava člena

│   └── static/

│       ├── css/

│       │   └── custom.css       # Vlastné štýly nad rámec Tailwindu

│       └── js/

│           ├── main.js          # Prepínanie sidebaru, dark mode, globálne handlery

│           └── kanban.js        # Logika drag-and-drop pre kanban

└── uploads/                     # Nahraté dokumenty (v gitignore)


Dizajnové pravidlá 
Všetky stránky musia dodržiavať tieto pravidlá:

Dark mode ako predvolený: <html class="dark">, všade použiť dark: Tailwind prefixy
Farby: primary #197fe6, bg-dark #111921, surface-dark #1b252e, border-dark #293038
Font: Space Grotesk (Google Fonts CDN)
Ikony: Material Symbols Outlined (Google Fonts CDN)
Border radius: default 0.25rem, lg 0.5rem, xl 0.75rem
Karty: bg-white dark:bg-surface-dark rounded-xl border border-slate-200 dark:border-border-dark shadow-sm
Aktívna položka v sidebari: background-color: #293038; border-right: 3px solid #197fe6;
Status badge: modrá = In Review, jantárová = Pending, smaragdová = Complete, červená = Critical
Responzívne breakpointy: sm: (640px), md: (768px), lg: (1024px), xl: (1280px)
Mobilný sidebar: predvolene skrytý, otvára sa cez hamburger tlačidlo ako fullscreen overlay
Tabuľky: na mobile horizontálne scrollovateľné (overflow-x-auto)
Grid: na mobile sa skladá z viacstĺpcového do jednostĺpcového
Ako spustiť
# 1. Vytvor virtuálne prostredie

python -m venv venv

venv\Scripts\activate          # Windows

# source venv/bin/activate     # Linux/Mac

# 2. Nainštaluj závislosti

pip install -r requirements.txt

# 3. Spusti appku

python run.py

# 4. (Voliteľné) Naplň vzorovými dátami

python seed.py

# 5. Otvor v prehliadači

# http://localhost:5000

