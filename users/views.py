# Provides ability to authenticate username+pw, log a user in, log a user out.
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
import logging
logger = logging.getLogger('django')

def index(request):
    logger.debug('running users app, index ... view started')

    # Request has "user" and "is_authenticated" built into it that tells us if the user is signed in or not.
    if not request.user.is_authenticated:
        logger.debug('running users app, index ... user is not authenticated')

        # If user isn't signed in, we redirect them to the login view
        return HttpResponseRedirect(reverse('users:login'))
    
    # Otherwise, if the user is authenticated
    return render(request, "users/user.html")

#----------------------------------------------------------------------------------

def login_view(request):
    logger.debug('running users app, login_view ... view started')

    if request.method == "POST":
        logger.debug('running users app, login_view ... user submitted via POST')
        
        # Assigns to variables the username and password passed in via the form in login.html
        email = request.POST["username"]
        password = request.POST["password"]
        
        # Runs the authenticate function on username and password and saves the result as the variable "user"
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            logger.debug('running users app login_view ... user found in DB')
            
            # This logs the user in if a matching username+password pair is found.
            login(request, user)
            logger.debug('running users app login_view ... user logged in, reversing to index')

            return HttpResponseRedirect(reverse("index"))
        
        # If user = None (e.g. user is not found in DB)    
        else:
            # If the user is None, that means that the user has not yet 
            # registered or has entered the wrong username and/or password.
            # In that case, we will render the login page with the message: Invalid credentials.
            logger.debug('running users app login_view ... user not found in DB')
            return render(request, "users/login.html", {
                "message": "Invalid credentials."
            })
    else:
        logger.debug('running users app login_view ... user arrived via GET')
        # If not submitted via post (e.g. we are not handling data submitted 
        # by the user via the form), then display the login page.
        return render(request, "users/login.html")

#--------------------------------------------------------------------------------

def logout_view(request):
    logger.debug('running users app, logout_view ... view started')

    # logout is a function built into django.
    # This simply logs out the currently logged-in user.
    logout(request)
    # After user is logged out, he is redirected to the login 
    # page with the message "Logged out.".
    logger.debug('running users app, logout_view ... user is logged out and is being redirected to login.html')
    return render(request, "users/login.html", {
        "message": "Logged out."
    })








"""
@app.route("/login", methods=["GET", "POST"])
    def login():
        app.logger.info(f'running /login ...  starting /login ')
        app.logger.info(f'running /login... database URL is: { os.path.abspath("finance.sqlite") }')
        app.logger.info(f'running /login ... CSRF token is: { session.get("csrf_token", None) }')

        nonce = generate_nonce()
        app.logger.info(f'running /login ... nonce is:{nonce}')
        form = LoginForm()

        # Step 1: Store CSRF token and flash temp message, if any.
        temp_flash = session.get('temp_flash', None)
        csrf_token = session.get('csrf_token', None)
        session.clear()
        if temp_flash:
            flash(temp_flash)
        if csrf_token:
            session['csrf_token'] = csrf_token

        # Step 2: Handle submission via post
        if request.method == 'POST':
            
            # Step 2.1: Handle submission via post + user input clears form validation
            if form.validate_on_submit():
                app.logger.info(f'running /login ... User submitted via post and user input passed form validation')
                
                # Step 2.1.1: Pull in email and password from form and pull user item from DB.
                email = form.email.data
                password = form.password.data
                app.logger.info(f'running /login... user-submitted email is: { email }')
                
                try:
                    user = db.session.query(User).filter_by(email = email).scalar()
                    app.logger.info(f'running /login... queried database on user-entered email, result is: { user }')
                    
                    # Step 2.1.2: Validate that user-submitted password is correct
                    if not check_password_hash(user.hash, form.password.data):
                        app.logger.info(f'running /login... error 2.1.2 (invalid password), flashing message and redirecting user to /login')
                        session['temp_flash'] = 'Error: Invalid username and/or password. If you have not yet registered, please click the link below. If you have recently requested a password reset, check your email inbox and spam folders.'
                        time.sleep(1)
                        return redirect('/login')

                    # Step 2.1.3: Validate that user account is confirmed
                    if user.confirmed != 'Yes':
                        app.logger.info(f'running /login... error 2.1.3 (user.confirmed != yes), flashing message and redirecting user to /login')
                        session['temp_flash'] = 'Error: This account has not yet been confirmed. Please check your email inbox and spam folder for email instructions regarding how to confirm your registration. You may re-register below, if needed.'
                        time.sleep(1)
                        return redirect('/login')

                    # Step 2.1.4: Remember which user has logged in
                    session['user'] = user.id
                    app.logger.info(f'running /login... session[user_id] is: { session["user"] }')

                    # Step 2.1.5: Redirect user to home page
                    app.logger.info(f'running /login... redirecting to /index.  User is: { session }')
                    app.logger.info(f'running /login ... session.get(user) is: { session.get("user") }')
                    return redirect(url_for('index'))
                
                # Step 2.1.6: Handle exception if didn't find user email in DB
                except AttributeError as e:
                    app.logger.info(f'running /login... AttributeError {e}. Flashing error and redirecting to login')
                    session['temp_flash'] = 'Error: User not found. Please check your input. If you do not yet have an account, you may register via the link below.'
                    return render_template('login.html', form=form)

            # Step 2.2: Handle submission via post + user input fails form validation
            else:
                app.logger.info(f'Running /login ... Error 2.2, flashing message and redirecting user to /login')
                session['temp_flash'] = 'Error: Invalid input. Please see the red text below for assistance.'
                return render_template('login.html', form=form)
        
        # Step 3: User arrived via GET
        app.logger.info(f'running /login ... user arrived via GET')
        response = make_response(render_template('login.html', form=form, nonce=nonce))
        app.logger.info(f'running /login... response.headers is: {response.headers}')
        return response
                  
# --------------------------------------------------------------------------------



def index(request):
    # Request has "user" and "is_authenticated" built into it that tells us if the user is signed in or not.
    if not request.user.is_authenticated:
        # If user isn't signed in, we redirect them to the login view
        return HttpResponseRedirect(reverse("login"))
    # Otherwise, if the user is authenticated
    return render(request, "users/user.html")


#----------------------------------------------------------------------------------


# This is the login view
def login_view(request):
    if request.method == "POST":
        # Assigns to variables the username and password passed in via the form in login.html
        username = request.POST["username"]
        password = request.POST["password"]
        # Runs the authenticate function on username and password and saves the result as the variable "user"
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # This logs the user in if a matching username+password pair is found.
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            # If the user is None, that means that the user has not yet 
            # registered or has entered the wrong username and/or password.
            # In that case, we will render the login page with the message: Invalid credentials.
            return render(request, "users/login.html", {
                "message": "Invalid credentials."
            })
    else:
        # If not submitted via post (e.g. we are not handling data submitted 
        # by the user via the form), then display the login page.
        return render(request, "users/login.html")


#-------------------------------------------------------------------------------


def logout_view(request):
    # logout is a function built into django.
    # This simply logs out the currently logged-in user.
    logout(request)
    # After user is logged out, he is redirected to the login 
    # page with the message "Logged out.".
    return render(request, "users/login.html", {
        "message": "Logged out."
    })
"""