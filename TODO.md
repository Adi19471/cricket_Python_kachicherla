# New Task: Color-code Time Slots (Green=Available, Red=Not Available)

## Plan:
**Information Gathered:**
- index.html has slots grid, JS fetches booked slots via /api/booked-slots/, adds .slot-booked (gray).
- CSS: .slot-available (green), .slot-booked (gray), needs red for booked.
- No backend change needed.

**Detailed Plan:**
1. Update base.html CSS: .slot-booked { background: #dc3545 !important; } (red).
2. index.html: Add "Not Available" text on booked slots via JS.
3. Keep green for available.

**Dependent Files:** booking/templates/base.html
**Followup:** Test on running server - booked slots red "Not Available", available green.

Ready to proceed? Confirm.
