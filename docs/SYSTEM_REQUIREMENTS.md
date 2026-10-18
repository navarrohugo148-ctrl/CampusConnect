# A. System Overview and Requirements

## Problem

University students often learn about club activities through disconnected group chats, social media, or verbal announcements. Event details, registrations, and attendance records may be scattered or lost. Club leaders lack a single place to organize activities and follow participation.

## Users

- **Students:** explore clubs, join or leave clubs, register for events, view registrations.
- **Club leaders:** all student functions plus manage events and record attendance **for assigned clubs only**.

Club leadership is defined by a `club_leaders` database record, rather than by making every account a global administrator.

## Goal and functions

Centralize campus club information and the complete event workflow in one platform: discover → join → publish → register → attend → review.

## Functional requirements and implementation traceability

| ID | Requirement | Design decision / why | Evidence in repository |
| --- | --- | --- | --- |
| FR-01 | Create an account and authenticate. | A `users` table separates identities from club and event data; salted password hashes protect credentials. | `app.py`: `register`, `login`, `logout` routes; `templates/register.html`, `templates/login.html` |
| FR-02 | Browse and search all available clubs. | One `clubs` table provides a reusable directory; client-side search reduces steps. | `app.py`: `clubs` route; `templates/clubs.html`; `static/app.js` |
| FR-03 | Join and leave clubs without duplicate membership. | The composite primary key `(user_id, club_id)` ensures one membership per person per club. | `app.py`: `change_membership`; table `club_memberships` |
| FR-04 | Club leaders can create, edit, and cancel activities. | Authorization is checked by the club-specific `club_leaders` mapping. | `app.py`: `event_new`, `event_edit`, `event_cancel`, `is_leader`; `templates/event_form.html` |
| FR-05 | Students register for an event and see capacity. | `registrations` is a junction table; transactions, capacity checks, and uniqueness prevent oversubscription and duplicates. | `app.py`: `change_registration`; `templates/event_detail.html` |
| FR-06 | Club leaders record event attendance. | Attendance is stored as a timestamp on the unique event registration, tying check-in to a registered student. | `app.py`: `attendance`; `templates/attendance.html` |
| FR-07 | Users see their own clubs and event registrations. | A dashboard combines data across membership and registration relationships. | `app.py`: `dashboard`; `templates/dashboard.html` |
| FR-08 | Store data between browser sessions. | SQLite persists records on disk; foreign keys protect references. | `app.py`: `SCHEMA`, `db`, `init_db` |

## Nonfunctional considerations

- **Usability:** readable navigation, labels for forms, responsive styling, and clear status messages.
- **Integrity:** primary keys, foreign keys, uniqueness checks, capacity limits, and parameterized SQL.
- **Privacy:** only assigned club leaders can access event attendance lists.
- **Maintainability:** separate server code, HTML templates, CSS/JavaScript, and design docs.

## Project scope for this midterm

The database begins with four fictional sample clubs and five sample events. Initial club leader accounts are seeded. University-wide administration, real email notifications, production hosting, and leader approval workflows are out of scope for the current classroom prototype.
