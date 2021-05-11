import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

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
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")



@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    if request.method == "GET":

        current_user = session["user_id"]
        current_cash=db.execute("SELECT cash FROM users WHERE id = :id", id=current_user)

        # portfolio_table=""
        table_symbols=[]
        table_volumes=[]
        table_share_price=[]
        table_stock_name=[]
        table_total_value=[]

        rows=db.execute("SELECT stock_symbol,volume FROM portfolio WHERE id = :id", id=current_user)
        for row in rows:
            symbol=row["stock_symbol"]
            table_symbols.append(str(symbol))

            table_volumes.append(row["volume"])

            lookedup=lookup(row["stock_symbol"])
            table_share_price.append(lookedup.get("price"))
            table_stock_name.append(lookedup.get("name"))

            table_total_value.append(int(lookedup.get("price"))*int(row["volume"]))

        # at this point we have lists with stock_symbols, amounts, prices and stock names just need to generate the code for portfolio table

        # for row in table_symbols:
        #     y=0
        #     portfolio_table+="<tr><td>"+str(table_stock_name[y])+"</td><td>"+str(table_symbols[y])+"</td><td>"+str(table_volumes[y])+"</td><td>"+str(table_share_price[y])+"</td></tr>"
        #     y+=1
        # not sure if this is going to insert into index.html correctly

        current_cash=int(current_cash[0]["cash"])
        current_total_value=current_cash

        for i in range(len(table_volumes)):

            volume=int(table_volumes[i])
            price=int(table_share_price[i])
            current_total_value+= volume*price

        return render_template("index.html", current_cash=current_cash, table_symbols=table_symbols,table_volumes=table_volumes,table_share_price=table_share_price,table_stock_name=table_stock_name, table_total_value=table_total_value,current_total_value=current_total_value)

    else:
        # dont think ill be posting with index
        return apology("Should this even exist, how did u get here?")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    lookedup = []
    if request.method == "POST":
        if not request.form.get("buy_symbol"):
            return apology("Must provide stock symbol", 403)
        shares_to_buy = request.form.get("buy_amount")
        if not shares_to_buy:
            return apology("Must provide number of shares to buy", 403)

        shares_to_buy = int(shares_to_buy)

        if shares_to_buy <= 0:
            return apology("Must provide positive number of shares to buy", 403)

        else:
            lookedup = lookup(request.form.get("buy_symbol"))

            if not lookedup:
                return apology("Not a stock symbol", 403)


            current_user = session["user_id"]
            user_cash = db.execute("SELECT cash FROM users WHERE id = :id", id=current_user)

            # see if properly selecting cash amount
            if not user_cash:
                return apology("Didn't find user's current balance", 000)


            current_cash = user_cash[0]["cash"]
            current_cash = int(current_cash)

            stock_name = lookedup.get("name")
            stock_price = lookedup.get("price")
            stock_symbol = lookedup.get("symbol")

            total_cost = shares_to_buy * stock_price
            if current_cash < total_cost:
                return apology("You do not have enough money for this purchase", 000)

            new_balance = current_cash - total_cost

            db.execute("UPDATE users SET cash = :new_balance WHERE id = :id", new_balance=new_balance, id=current_user)

            db.execute("INSERT INTO purchases (id,stock_symbol,volume_purchased,price,date_purchased) VALUES(:id,:symbol,:amount,:price,datetime('now'))", id=current_user, symbol=stock_symbol, amount=shares_to_buy, price=stock_price)

            check_holdings = db.execute("SELECT volume FROM portfolio WHERE id = :id AND stock_symbol=:stock_symbol", id=current_user, stock_symbol=stock_symbol)

            if not check_holdings:
                db.execute("INSERT INTO portfolio (id,stock_symbol,volume) VALUES(:id,:stock_symbol,:volume)", id=current_user, stock_symbol=stock_symbol, volume=shares_to_buy)
            else:
                old_volume = check_holdings[0]["volume"]
                old_volume = int(old_volume)
                new_volume = old_volume+shares_to_buy
                db.execute("UPDATE portfolio SET volume = :new_volume", new_volume=new_volume)



            return render_template("bought.html", stock_name=stock_name,stock_price=stock_price, stock_symbol=stock_symbol, shares_to_buy=shares_to_buy, total_cost= total_cost)



    else:
        return render_template("buy.html")


    return apology("TODO BUY")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    if request.method == "GET":
        current_user = session["user_id"]

        sales=db.execute("SELECT stock_symbol, volume_sold, price, date_sold FROM sales WHERE id = :id", id=current_user)
        lookedup=[]
        sales_table_stock_name=[]
        sales_table_symbols=[]
        sales_table_stock_price=[]
        sales_table_volumes=[]
        sales_table_date=[]

        for row in sales:
            lookedup = lookup(row["stock_symbol"])
            sales_table_stock_name.append(str(lookedup.get("name")))
            sales_table_symbols.append(str(row["stock_symbol"]))
            sales_table_stock_price.append(float(row["price"]))
            sales_table_volumes.append(int(row["volume_sold"]))
            sales_table_date.append(str(row["date_sold"]))

        buys = db.execute("SELECT stock_symbol, volume_purchased, price, date_purchased FROM purchases WHERE id = :id", id=current_user)

        buy_table_stock_name=[]
        buy_table_symbols=[]
        buy_table_volumes=[]
        buy_table_share_price=[]
        buy_table_date=[]

        lookedup=[]

        for row in buys:

            lookedup = lookup(row["stock_symbol"])
            buy_table_stock_name.append(str(lookedup.get("name")))
            buy_table_symbols.append(str(row["stock_symbol"]))
            buy_table_volumes.append(int(row["volume_purchased"]))
            buy_table_share_price.append(float(row["price"]))
            buy_table_date.append(str(row["date_purchased"]))


        return render_template("history.html",
        sales_table_stock_name=sales_table_stock_name,
        sales_table_stock_price=sales_table_stock_price,
        sales_table_symbols=sales_table_symbols,
        sales_table_volumes=sales_table_volumes,
        sales_table_date=sales_table_date,
        buy_table_stock_name=buy_table_stock_name,
        buy_table_symbols=buy_table_symbols,
        buy_table_volumes=buy_table_volumes,
        buy_table_share_price = buy_table_share_price,
        buy_table_date=buy_table_date)

    else:
        return apology("how did u post to history")

    # return apology("No history here")





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
        rows = db.execute("SELECT * FROM users WHERE username = :username",username=request.form.get("username"))

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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    lookedup = []
    """Get stock quote."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("must provide stock symbol", 403)

        else:
            lookedup = lookup(request.form.get("symbol"))

            # if lookedup == NULL: NULL WASNT DEFINED?

            #     return apology("Not a stock symbol", 403)

            if not lookedup:
                return apology("Not a stock symbol", 403)


            # NEED TO get the info from lookup into the quoted pg

            # test = lookedup
            # test =lookedup.get("name")
            stock_name = lookedup.get("name")
            stock_price = lookedup.get("price")
            stock_symbol = lookedup.get("symbol")



            return render_template("quoted.html", stock_name=stock_name,stock_price=stock_price, stock_symbol=stock_symbol)



    else:
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
        # User reached route via POST (as by submitting a form via POST)

    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        elif not request.form.get("password_confirm"):
            return apology("must confirm password", 403)

        elif request.form.get("password") != request.form.get("password_confirm"):
            return apology("Passwords must match", 403)

        elif request.form.get("username") == db.execute("SELECT username FROM users WHERE username = :username", username=request.form.get("username")) :
            return apology("Username already in use", 403)

        # TODO need to make sure username doesnt already exist done???, then hash pass and store both username and hash, hash is imported see login and imports
        else:

            # db.execute("INSERT INTO users (username,hash,cash) VALUES(?,?,10000)",(request.form.get("username"),generate_password_hash(request.form.get("password_confirm"),sha1,0)))
            db.execute("INSERT INTO users (username,hash) VALUES(:username,:hash)", username=request.form.get("username"), hash = generate_password_hash(request.form.get("password")))
        # Redirect user to home page

        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

    # return apology("TODO")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        current_user = session["user_id"]


        if not request.form.get("sell_amount"):
            return apology("Must provide a number to sell", 403)

        stock_to_sell= request.form.get("stock_to_sell")
        sell_amount= int(request.form.get("sell_amount"))

        current_stocks = db.execute("SELECT volume FROM portfolio WHERE id = :id AND stock_symbol=:stock_symbol", id=current_user, stock_symbol=stock_to_sell)
        # current_stocks=db.execute("SELECT volume FROM portfolio WHERE id= :id AND stock_symbol= :stock_symbol", id=current_user, stock_symbol=stock_to_sell)



        if not current_stocks:
            return apology("You do not own any stocks, try refreshing the sell page")

        current_volume = current_stocks[0]["volume"]
        current_volume = int(current_volume)

        if current_volume < int(request.form.get("sell_amount")):
            return apology("Attempting to sell more shares than you own", 403)

        lookedup=[]
        lookedup=lookup(request.form.get("stock_to_sell"))
        if not lookedup:
            return apology("Unable to lookup stock info.")

        stock_name = lookedup.get("name")
        stock_price = lookedup.get("price")
        stock_symbol = lookedup.get("symbol")


        user_cash = db.execute("SELECT cash FROM users WHERE id = :id", id=current_user)
        # see if properly selecting cash amount
        if not user_cash:
            return apology("Didn't find user's current balance", 000)
        # update user total cash
        current_cash = user_cash[0]["cash"]
        current_cash = int(current_cash)
        total_revenue = sell_amount * stock_price
        new_balance = current_cash + total_revenue
        db.execute("UPDATE users SET cash = :new_balance WHERE id = :id", new_balance=new_balance, id=current_user)

        # update portfolio
        new_volume=0
        new_volume=current_volume-sell_amount
        db.execute("UPDATE portfolio SET volume = :new_volume WHERE id = :id AND stock_symbol = :stock_symbol", new_volume=new_volume, id=current_user, stock_symbol=stock_symbol)

        # update sales database
        db.execute("INSERT INTO sales (id,stock_symbol,volume_sold,price,date_sold) VALUES(:id,:symbol,:amount,:price,datetime('now'))", id=current_user, symbol=stock_symbol, amount=sell_amount, price=stock_price)


        return render_template("sold.html",stock_name=stock_name, stock_price=stock_price, stock_symbol=stock_symbol,shares_to_sell=sell_amount, total_value=total_revenue)


    else:
        current_user = session["user_id"]
        current_stocks=db.execute("SELECT stock_symbol, volume FROM portfolio WHERE id = :id", id=current_user)
        if not current_stocks:
            return apology("You do not own any stocks")
        return render_template("sell.html",current_stocks=current_stocks)
    # return apology("i suck at selling?")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
