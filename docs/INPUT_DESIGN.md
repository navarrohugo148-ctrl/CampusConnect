# E. Input Design and F. Connection to Course Theory

## Selected input: Create Event form

**Repository evidence:** `templates/event_form.html` (interface), `app.py` (`event_new`, `event_edit`, `event_form_values`), and `static/style.css` (layout).

**Report screenshot needed:** Run the project, sign in with the sample leader account, open the **Business Club** page, click **Create event**, and capture the full browser form. Insert that screenshot here when preparing the PDF report.

| Input design principle | Concrete design decision | Benefit to the user |
| --- | --- | --- |
| Effectiveness | Requires event title, description, location, date/time, and capacity | Leaders enter the information participants need |
| Accuracy | Date/time picker, number input for capacity, server-side checks for length and future date | Reduces missing and invalid data |
| Ease of use | Explicit labels, example placeholder text, one main Publish button | Users understand the next step quickly |
| Consistency | Shared navigation, cards, buttons, and form styling | Reduces the learning curve |
| Simplicity | Five essential fields without unrelated settings | Avoids unnecessary choices |
| Attractiveness | Clear spacing, readable contrast, responsive form columns | Makes the form easier to scan on desktop and mobile |

The form submits a POST request including a CSRF token. The server checks club leadership, verifies all fields, writes an event to SQLite, and returns a confirmation view. Merely looking correct is not enough: validation and feedback are part of input design.

## Connection between design theory and implementation

- **Requirements → tables:** FR-03 and FR-05 require membership and registration data. Separate junction tables implement those different workflows without data duplication.
- **Requirement → authorization:** FR-04 requires leader controls, so `club_leaders` models permissions per club rather than treating every user as a leader.
- **DFD → actual transactions:** A registration request moves from student input, through the registration process, into `registrations`, and back to the student's confirmation and dashboard.
- **Database integrity → real controls:** SQLite foreign keys and UNIQUE constraints enforce relationships, while Flask validation and a transaction enforce event capacity and authorization.
- **Input design → fewer errors:** Purposeful field types and explicit errors help a leader enter valid activity details.

**Suggested report evidence:** Include an image of the Create Event form, screenshots of a student registration and confirmation, the DFD and ERD from the `docs/` folder, and references to the relevant routes and schema in `app.py`.
