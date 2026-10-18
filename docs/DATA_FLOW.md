# B. Data Flow Design

## Level 0 Data Flow Diagram

The diagram below captures the flow of data across the main processes. GitHub renders Mermaid automatically in Markdown previews.

```mermaid
flowchart LR
    S[External entity: Student]
    L[External entity: Club Leader]
    P1((1.0 Manage Accounts & Memberships))
    P2((2.0 Manage Clubs & Events))
    P3((3.0 Process Event Registrations))
    P4((4.0 Record Attendance))
    D1[(D1 Users)]
    D2[(D2 Clubs & Memberships)]
    D3[(D3 Events)]
    D4[(D4 Registrations)]

    S -->|Account details, join/leave requests| P1
    P1 -->|Login status, membership confirmation| S
    P1 <-->|Credentials and user records| D1
    P1 <-->|Club memberships| D2
    L -->|Event details, edits, cancellations| P2
    P2 -->|Confirmation and managed events| L
    P2 <-->|Club and leader records| D2
    P2 <-->|Event details and capacity| D3
    S -->|Event selection and registration/cancellation| P3
    P3 -->|Registration status, capacity| S
    P3 <-->|Event details| D3
    P3 <-->|Registration records| D4
    L -->|Selected student check-in| P4
    P4 -->|Attendance confirmation| L
    P4 <-->|Registration and attendance data| D4
```

## Main components

- **External entities:** Student; Club Leader (both interact through the web interface).
- **Processes:** (1) account/membership management, (2) club/event management, (3) event registration, (4) attendance tracking.
- **Data stores:** D1 users; D2 clubs, club memberships, club leaders; D3 events; D4 registrations.
- **Data flows:** account details, requests to join clubs, new event details, event registration requests, returned confirmation, attendance selections, and persisted records.

## Example: event registration from input to storage

1. The student opens an event detail page and presses **Register for event**.
2. Flask reads the submitted event identifier from the URL and the authenticated user identifier from the session, and verifies the CSRF token.
3. Within a database write transaction, the system checks whether the event exists, is open, still has capacity, and does not already have a registration for this student.
4. On success, SQLite inserts `(event_id, user_id)` into `registrations`. The unique constraint protects against duplicate pairs.
5. Flask commits the transaction and displays a confirmation; the event count and dashboard reflect the stored registration.

**Why this reflects the real system:** each labeled data flow corresponds to a concrete route, submitted form, database query, or response shown to the user.
