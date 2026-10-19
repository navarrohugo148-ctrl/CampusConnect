# CampusConnect — University Club Activities Management System

**ISM4113 Systems Design Midterm Project**

CampusConnect is a responsive web application where students discover university clubs, join communities, register for events, and review their activities. Assigned club leaders can create, edit, cancel events, and record attendance. The application uses **Flask, SQLite, HTML, CSS, and JavaScript**.

> This project is an educational local prototype, not a production university platform. The clubs, events, and users initially shown are **fictional sample records**.

## Quick start (Windows 11)

1. Install [Python 3](https://www.python.org/downloads/) (check **Add Python to PATH** during setup).
2. Download or clone this repository. Open the **CampusConnect** folder in File Explorer, click the address bar, type `cmd` and press Enter. A Command Prompt opens in the project folder.
3. Create a virtual environment:

   ```bat
   py -m venv .venv
   ```

4. Install dependencies:

   ```bat
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

5. Start the system:

   ```bat
   .venv\Scripts\python.exe app.py
   ```

6. Visit **http://127.0.0.1:5000** in your browser.

**First launch:** the system automatically creates `instance/campusconnect.sqlite3` and loads sample clubs, events, and demo accounts.

### Demo sign-ins

| User type | Email | Password |
| --- | --- | --- |
| Student | `student@campusconnect.test` | `Demo1234!` |
| Club leader | `leader@campusconnect.test` | `Demo1234!` |

- The **student** account can join clubs and register for events.
- The **leader** account manages the Business Club and Student Government Association. Log in with it to access **Create event**, **Edit event**, **Cancel event**, and **View attendance** features.
- You can also register a brand-new student account.

**Local reset:** stop the app, delete `instance/campusconnect.sqlite3`, and run `app.py` again to regenerate sample data. This deletes any real entries you made locally. Do not commit the database to GitHub.

## Main functions

- **Account management:** register, log in, and log out; passwords stored as salted hashes.
- **Club directory:** browse/search clubs; join and leave clubs.
- **Event discovery:** upcoming events, details, venue, time, and remaining capacity.
- **Event registration:** students register or cancel; the database prevents duplicates.
- **Event management:** only assigned leaders can create, edit, and cancel events.
- **Attendance tracking:** leaders check in registered students; attendance time is saved.
- **Personal dashboard:** clubs and registered events; leaders see their managed clubs.

## Project structure

```text
CampusConnect/
├── app.py                  Flask routes, authorization, database schema, demo seed
├── requirements.txt        Python dependency (Flask)
├── README.md               Purpose, setup, features, and demo credentials
├── .gitignore              Protects local database, virtual environment, secrets
├── templates/              Server-rendered HTML pages and shared components
├── static/
│   ├── style.css           Responsive visual design
│   └── app.js              Live club search
├── docs/
│   ├── SYSTEM_REQUIREMENTS.md
│   ├── DATA_FLOW.md
│   ├── DATABASE_DESIGN.md
│   └── INPUT_DESIGN.md
└── tests/
    └── test_app.py         Automated integration tests
```

## Database design

The SQLite schema contains six normalized tables:

1. `users` — identities and password hashes
2. `clubs` — club descriptions and categories
3. `club_leaders` — which users are leaders of each club
4. `club_memberships` — many-to-many club membership
5. `events` — each event belongs to one club
6. `registrations` — which user reserved which event; attendance timestamp

Read [`docs/DATABASE_DESIGN.md`](docs/DATABASE_DESIGN.md) for the ER diagram, data dictionary, relationships, and normalization rationale. See [`docs/DATA_FLOW.md`](docs/DATA_FLOW.md) for the Level 0 DFD.

