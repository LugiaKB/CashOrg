import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///org.db")
options = ['Expense', 'Income', 'Transfer']
limoptions = ['Expense', 'Income']
excategs = db.execute('SELECT name FROM categ WHERE type = "expense" OR type = "both"')
incategs = db.execute('SELECT name FROM categ WHERE type = "income" OR type = "both"')
alcategs = db.execute('SELECT name FROM categ')

@app.route("/")
@login_required
def index():

    if not db.execute("SELECT id FROM accounts WHERE user_id = :user_id", user_id=session['user_id']):
        return redirect('/create')
    else:
        contas = db.execute('SELECT name, cash FROM accounts WHERE user_id = :user_id LIMIT 3', user_id=session['user_id'])

        rows = db.execute('SELECT * FROM transactions WHERE user_id = :user_id ORDER BY time DESC LIMIT 3', user_id=session['user_id'])
        for row in rows:
            categos = ""
            catego = db.execute('SELECT categ.name FROM categ JOIN sync ON sync.categ_id = categ.id JOIN transactions ON sync.trans_id = transactions.id WHERE transactions.user_id = :user_id AND transactions.id = :trans_id'
                                , user_id=session['user_id'], trans_id=row['id'])
            for cate in catego:
                categos += cate['name'] + ', '
            categos = categos[0:(len(categos) - 2)] + '.'
            row['categs'] = categos

            cname = db.execute('SELECT name FROM accounts WHERE id = :acid', acid=row['account_id'])[0]['name']
            row['conta'] = cname

            iname = db.execute('SELECT name FROM accounts WHERE id = :acid', acid=row['incount_id'])
            if len(iname) < 1:
                row['inconta'] = ''
            else:
                row['inconta'] = iname[0]['name']

        return render_template('index.html', contas=contas, rows=rows)

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():

    if request.method == 'GET':

        return render_template('create.html')

    else:
        contas = db.execute('SELECT name FROM accounts WHERE user_id = :user_id', user_id=session['user_id'])
        name = request.form.get('name')
        if not name:
            return apology("New account needs a name")
        d = 0
        for conte in contas:
            if name == conte['name']:
                d += 1
        if d > 0:
            return apology('each account must have a different name')

        balance = request.form.get('balance')
        if not balance or float(balance) < 0:
            return apology('Invalid balance')

        db.execute('INSERT INTO accounts (user_id, name, cash) VALUES (:user_id, :name, :cash)', user_id=session['user_id'], name=name, cash=balance)
        return redirect('/')

@app.route('/accounts')
@login_required
def accounts():

    contas = db.execute('SELECT name, cash FROM accounts WHERE user_id = :user_id', user_id=session['user_id'])

    if not contas:
        return redirect('/create')
    else:
        return render_template('accounts.html', contas=contas)

@app.route("/launch", methods=["GET", "POST"])
@login_required
def launch():

    contas = db.execute('SELECT name FROM accounts WHERE user_id = :user_id', user_id=session['user_id'])

    if request.method == 'GET':
        if not contas:
            return redirect('/create')
        elif len(contas) == 1:
            return render_template('launch.html', contas=contas, options=limoptions, incategs=incategs, excategs=excategs)
        else:
            return render_template('launch.html', contas=contas, options=options, incategs=incategs, excategs=excategs)
    else:

        name = request.form.get('name')
        if not name:
            return apology('operation must have a name')

        cost = request.form.get('cost')
        a = 0
        for c in cost:
            if c.isalpha():
                a += 1
        if not c or a != 0:
            return apology('invalid cost')
        cost = float(cost)

        categs = request.form.getlist('categ')
        print(categs)
        print(alcategs)
        b = 0
        for categ in categs:
            for alcateg in alcategs:
                if categ == alcateg['name']:
                    b += 1
        if b != len(categs):
            return apology('invalid category')

        conta = request.form.get('conta')
        if not conta:
            return apology('invalid account')
        c = 0
        for cont in contas:
            if conta == cont['name']:
                c += 1
        if c != 1:
            return apology('invalid account')
        conta_id = db.execute('SELECT id FROM accounts WHERE name = :name AND user_id = :user_id', name=conta, user_id=session['user_id'])[0]['id']

        operation = request.form.get('operation')
        if not operation or operation not in options:
            return apology('invalid operation')

        cash = db.execute('SELECT cash FROM accounts WHERE name = :name AND user_id = :user_id', name=conta, user_id=session['user_id'])[0]['cash']

        if operation == 'Expense':

            cash -= cost
            db.execute('UPDATE accounts SET cash = :cash WHERE id = :iden', cash=cash, iden=conta_id)
            trans_id = db.execute('INSERT INTO transactions (user_id, account_id, item_name, transaction_type, cost, time) VALUES (:user_id, :account_id, :name, :t_type, :cost, datetime())'
                        , user_id=session['user_id'], account_id=conta_id, name=name, t_type=operation, cost=cost)
            for cat in categs:

                catid = db.execute('SELECT id FROM categ WHERE name = :cat', cat=cat)[0]['id']
                db.execute('INSERT INTO sync (trans_id, categ_id) VALUES (:trans_id, :catid)', trans_id=trans_id, catid=catid)

            return redirect('/')

        elif operation == 'Income':

            cash += cost
            db.execute('UPDATE accounts SET cash = :cash WHERE id = :iden', cash=cash, iden=conta_id)
            trans_id = db.execute('INSERT INTO transactions (user_id, account_id, item_name, transaction_type, cost, time) VALUES (:user_id, :account_id, :name, :t_type, :cost, datetime())'
                        , user_id=session['user_id'], account_id=conta_id, name=name, t_type=operation, cost=cost)
            for cat in categs:

                catid = db.execute('SELECT id FROM categ WHERE name = :cat', cat=cat)[0]['id']
                db.execute('INSERT INTO sync (trans_id, categ_id) VALUES (:trans_id, :catid)', trans_id=trans_id, catid=catid)

            return redirect('/')

        elif operation == 'Transfer':

            inconta = request.form.get('receive')
            if not inconta:
                return apology('invalid receiving account1')
            e = 0
            for conti in contas:
                if inconta == conti['name']:
                    e += 1
                if e != 1:
                    return apology('invalid receiving account2')
            inconta_id = db.execute('SELECT id FROM accounts WHERE name = :name AND user_id = :user_id', name=inconta, user_id=session['user_id'])[0]['id']
            incash = db.execute('SELECT cash FROM accounts WHERE name = :name AND user_id = :user_id', name=inconta, user_id=session['user_id'])[0]['cash']

            cash -= cost
            incash += cost

            db.execute('UPDATE accounts SET cash = :cash WHERE id = :iden', cash=cash, iden=conta_id)
            db.execute('UPDATE accounts SET cash = :cash WHERE id = :iden', cash=incash, iden=inconta_id)
            trans_id = db.execute('INSERT INTO transactions (user_id, account_id, item_name, transaction_type, cost, time, incount_id) VALUES (:user_id, :account_id, :name, :t_type, :cost, datetime(), :incount_id)'
                        , user_id=session['user_id'], account_id=conta_id, name=name, t_type=operation, cost=cost, incount_id=inconta_id)
            for cat in categs:

                catid = db.execute('SELECT id FROM categ WHERE name = :cat', cat=cat)[0]['id']
                db.execute('INSERT INTO sync (trans_id, categ_id) VALUES (:trans_id, :catid)', trans_id=trans_id, catid=catid)

            return redirect('/')

        else:
            return apology('invalid operation')


@app.route("/history", methods=["GET", "POST"])
@login_required
def history():
    """Show history of transactions"""
    rows = db.execute('SELECT * FROM transactions WHERE user_id = :user_id ORDER BY time DESC', user_id=session['user_id'])
    expenses = []
    incomes = []
    transfers = []
    for row in rows:
        categos = ""
        catego = db.execute('SELECT categ.name FROM categ JOIN sync ON sync.categ_id = categ.id JOIN transactions ON sync.trans_id = transactions.id WHERE transactions.user_id = :user_id AND transactions.id = :trans_id'
                             , user_id=session['user_id'], trans_id=row['id'])
        for cate in catego:
            categos += cate['name'] + ', '
        categos = categos[0:(len(categos) - 2)] + '.'
        row['categs'] = categos

        cname = db.execute('SELECT name FROM accounts WHERE id = :acid', acid=row['account_id'])[0]['name']
        row['conta'] = cname

        iname = db.execute('SELECT name FROM accounts WHERE id = :acid', acid=row['incount_id'])
        if len(iname) < 1:
            row['inconta'] = ''
        else:
            row['inconta'] = iname[0]['name']

        if row['transaction_type'] == 'Expense':
            expenses.append(row)
        elif row['transaction_type'] == 'Income':
            incomes.append(row)
        elif row['transaction_type'] == 'Transfer':
            transfers.append(row)


    if request.method == 'GET':

        print(rows)
        return render_template('history.html', options=options, rows=rows)
    else:

        opti = request.form.get('opera')

        if opti == 'Expense':
            return render_template('history.html', options=options, rows=expenses)
        elif opti == 'Income':
            return render_template('history.html', options=options, rows=incomes)
        elif opti == 'Transfer':
            return render_template('history.html', options=options, rows=transfers)
        else:
            return redirect('/history')

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirmation")
        hashed = generate_password_hash(password)
        nick = db.execute('SELECT username FROM users WHERE username = :username', username=username)

        if len(nick) != 0 or len(username) == 0:
            return apology("Invalid username")

        if len(password) < 8 or len(password) == 0:
            return apology("Password must contain 8 characters.")

        if password != confirm:
            return apology("Password doesn't match")

        user_id = db.execute('INSERT INTO users (username, hash) VALUES (:username, :password)', username=username, password=hashed)
        session['user_id'] = user_id
        return redirect('/')

    else:
        return render_template('register.html')

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
