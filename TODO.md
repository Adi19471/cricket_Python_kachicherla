# Fix Logout and Login Page Issues

## Information Gathered:
- Navbar in base.html has logout button using `{% url 'logout' %}` when authenticated.
- cricket_booking/urls.py defines logout URL with auth_views.LogoutView (redirect to login).
- login.html template exists but URLs expect `registration/login.html` which is missing.
- Root cause: logout redirects to login, but template not found -> broken page.

## Detailed Plan:
1. Create `booking/templates/registration/login.html` with exact content from `booking/templates/login.html`.
   - This fixes LoginView template lookup without changing URLs.
2. No other changes needed (backend logic correct).

## Dependent Files:
- New: booking/templates/registration/login.html

## Followup Steps:
1. Run `python manage.py runserver`.
2. Test: Login -> Navbar shows logout -> Click logout -> Redirects to working login page -> Submit login form -> Redirect to home.
3. Check no errors in console/server logs.

## Progress:
- [x] Step 1: Created booking/templates/registration/login.html
- [ ] Step 2: Test logout/login flow on server
