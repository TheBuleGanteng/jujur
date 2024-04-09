# Jujur - A personal financial management tool
### [Video Demo](XX WIP XX)

### Description:
- Jujur helps users track their personal finances across bank accounts, consolidating the data to provide an easy-to-understand picture of net worth.   
- This project is a successor to [MyFinance50](https://github.com/TheBuleGanteng/MyFinance50_public), a project I submitted in early 2024 as my final project for [Harvard University's CS50p 2022](https://cs50.harvard.edu/python/2022/)

#### Motivation for project:
- The primary motivation behind this project was to continue building my skills in web development, particularly involving the following areas:
    - Use of RESTful APIs generally
    - Use and augmentation (via RAG-ing) of off-the-shelf LLMs
    - Use of market data
    - Visualization of data via charts and graphs 

- The secondary motivation behind this project was to solve a personal pain point of manually downloading bank statements and consolidating key data to obtain a cohesive picture of my personal finances (or lack thereof 💸😓)

#### Key elements:
1. This project features key elements of a brokerage account, including: 
    - User sign-up, including registration confirmation link sent via email
    
1. User registration
    - See: app.py -> /register, /register_confirmation/
    - See: register.html, register_confirmation.html
    - Two-stage user registration in which a user completes all fields and upon submit, the user's status is set to unconfirmed and the user is sent an email with a cryptographic registration confirmation link.
    - When the user clicks the registration confirmation link, the user's account status is updated to confirmed and the user is now able to log in and use the app.
    - Unconfirmed accounts over a threshold age are automatically purged from the database.

1. User registration
    - See: app.py -> /register, /register_confirmation/
    - See: register.html, register_confirmation.html
    - Two-stage user registration in which a user completes all fields and upon submit, the user's status is set to unconfirmed and the user is sent an email with a cryptographic registration confirmation link.
    - When the user clicks the registration confirmation link, the user's account status is updated to confirmed and the user is now able to log in and use the app.
    - Unconfirmed accounts over a threshold age are automatically purged from the database.

1. Customizable user profile, including accounting and tax settings
    - See app.py -> /profile
    - See profile.html
    - Updatable settings for first name, last name, username, LIFO/FIFO, capital loss tax offsets, short-term capital gains tax rates, and long-term capital gains tax rates.
    - Live validation to the user for username availability 
    - Submit button is enabled only when valid inputs are detected
    - Use of a nifty slider to update tax rates

1. Password change
    - See app.py -> password_change
    - See password_change.html
    - In-app password change using user email address and current password as validators

1. Password reset
    - See app.py -> /password_reset_request, /password_reset_request_new
    - See password_reset_request.html, password_reset_request_new.html 
    - Two-stage password reset in which the user provides his or her email, is automatically sent an email with a cryptograpic password reset link, and once the user clicks the link, the app validates the link and allows the user to reset his or her password.
    - Cryptographic link is time-bound for increased security.

1. Index:
    - See app.py -> index
    - See index.html
    - Index view provides the user with an in-depth view of the user's current portfolio of open positions and cash, including before- and after-tax returns.
    - User can see additional information about the stocks in their portfolio by clicking on any ticker, which redirects the user to that company's corporate profile page via the '/quote' route.
    - Short- and long-term capital gains, taxes, and after-tax proceeds use a waterfall mechanism to calculate the appropriate amount of short- and long-term capital gains for each transaction, including share sales that include the sale of shares purchased in temporally distinct blocks. This process accounts for the use of LIFO or FIFO accounting, as set by the user at the time of registration and is updatable in the user's profile.
    - Market prices are live and refreshed upon page reload, using the [FMP API](https://site.financialmodelingprep.com/developer/docs)

1. Detailed index:
    - See app.py -> /index_detail
    - See index_detail.html
    - A more granular view of the user's current portfolio of open positions, cash, and previous share sales, broken down by cost basis, current market value, short- and long-term capital gains, short- and long-term capital gains tax, capital loss tax offsets, and before and after-tax returns.
    - User can see additional information about the stocks in their portfolio by clicking on any ticker, which redirects the user to that company's corporate profile page via the '/quote' route.
    - Market prices are live and refreshed upon page reload, using the [FMP API](https://site.financialmodelingprep.com/developer/docs)

1. Buy:
    - See app.py -> /buy
    - See buy.html
    - Allows user to 'buy' shares in any of the ~7,000 companies available via the FMP API.
    - User input for stock symbol is checked in real-time against a database record of companies downloaded from the FMP API daily and provides real-time autocomplete capabilities, allowing the user to search by company symbol or name.
    - Once the user has inputted a valid share symbol and a number of shares to be purchased, the user is provided with real-time feedback regarding his or her cash on hand, the cost of the proposed share purchase, and whether cash on hand is sufficient to cover the proposed purchase.
    - Only after valid inputs for symbol and number of shares is detected, the submit button is enabled.
    - The symbol, number of shares, and market price of the company are again validated on the back-end before the database is updated to adjust the transactions table and user table to reflect the new purchase transaction and the reduction in user's cash.

1. Sell:
    - See app.py -> /sell
    - See sell.html
    - Allows the user to 'sell' shares currently 'owned'
    - User selects the company in which he or she wishes to sell shares from the list of companies in the user's current portfolio.
    - Once the user has inputted the number of shares he or she wishes to sell, the user is provided with real-time feedback regarding whether he or she owns sufficient shares to cover the proposed sale.
    - Only after valid inputs for symbol and number of shares is detected, the submit button is enabled.
    - The symbol, number of shares, and market price of the company are again validated on the back-end before the database is updated to adjust the transactions table and user table to reflect the new sale transaction and the increase in user's cash.
    
1. Quote:
    - See app.py -> /quote
    - See quote.html, quoted.html
    - Allows user to view in-depth real-time information regarding companies.
    - User input for stock symbol is checked in real-time against a database record of companies downloaded from the FMP API daily and provides real-time autocomplete capabilities, allowing the user to search by company symbol or name.
    - Only after valid input for symbol is detected, the submit button is enabled.
    - Upon submission of a valid symbol, the user is redirected to the company profile corresponding to that symbol, including the company's stock price, daily change, beta, 52-week price range, company description, industry, etc.



#### UNDER THE HOOD:

1. Languages used:
    - Front-end: HTML / JavaScript incl. AJAX for live search and autocomplete / [Bootstrap5](https://getbootstrap.com/docs/5.0/getting-started/introduction/) CSS w/ minor  customizations / [Jinja](https://jinja.palletsprojects.com/en/3.1.x/) / [Flask-WTF](https://flask-wtf.readthedocs.io/en/1.2.x/)
    - Back-end: Python / Django
    - Datbase: sqlite3 (managed via Django)
    - Server: [Gunicorn](https://gunicorn.org/)
    - Reverse proxy: [nginx](https://www.nginx.com/)
    - Process control: [Supervisor](http://supervisord.org/) 
    - Docker: Spawns Gunicorn and Nginx containers via [Docker Desktop](https://www.docker.com/products/docker-desktop/)

1. Extensive automated testing of all routes via [Pytest](https://docs.pytest.org/en/8.0.x/)

1. Significant focus on security:
    - Protection against SQL injection via use of Django's Object-Relational Mapping (ORM) system.
    - Protection against HTML injection via use of jinja to pass user-inputted elements to HTML.
    - Protection against various injections via custom form fields with whitelisted characters.
    - Protection against various injections via secondary back-end validation of all user submissions.
    - Protection against cross-site scripting (XSS) via use of a Content Security Policy (CSP).
    - Protection against clickjacking via CSP's "frame-ancestors" directive.
    - Secondary protection against clickjacking via use of X_FRAME_OPTIONS.
    - Protection against cross-site registry attacks via Django's built-in CSRF middleware.
    - Protection against man-in-the-middle attacks by enforcing HTTPS only site-wide.
    - Protection against fraudulent or automated account creation via use of cryptographic tokens sent to the user via email as part of 2-step registration and password reset processes
    - Automatic logout due to a specified period of inactivity, including warning popup for improved UX.
    - Exclusion of sensitive data (e.g. passwords) from being stored in Session or in cryptographic token used for password reset
    - Externalization of sensitive data (e.g. login needed to send emails programmatically) to .env file protected against upload to GitHub via .gitignore file
    - Daily automated purging of stale, unconfirmed user accounts via a cron job