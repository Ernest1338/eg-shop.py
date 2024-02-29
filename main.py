#!/bin/python

import sys
from hashlib import sha256

sys.path.append("./eg-web.py")
sys.path.append("./sqlite-server.py")

from web import App  # noqa: E402
from sqlite import DBLocal, db_guard  # noqa: E402
from templates import template, cache  # noqa: E402

# NOTE: sql injection. and other vulns. i know
# NOTE: there is very likely a vulnerability so I can perform actions as different users
#       (i only validate auth that a user is correctly signed in, not that this user can
#        perform that action)

# db = DB(host="localhost", port=4567, database="shop", secret="secret")
db = DBLocal(filename="database.db")

auth_secret = "SECRET"
delivery_cost = 19.99

auth_cache = {}
listings_cache, _ = db.execute("SELECT * FROM listings")
if listings_cache is None:
    print(
        """--------------------------------------------------------
    Warning:
There are no listings in the DB.
You probably want to execute: ./admin_panel.py recreate-db
Or if you want the example data as well: ./admin_panel.py re
--------------------------------------------------------"""
    )
    if input("Do you want to continue? (y/n) ") not in ["y", "Y"]:
        exit(0)

listings_cache = [
    {
        "id": str(listing_id),
        "img": str(img),
        "name": str(name),
        "description": str(description),
        "price": str(price),
        "button": template["add-to-cart-button"].render({"id": str(listing_id)}),
    }
    for listing_id, img, name, description, price in listings_cache or []
]


def post_register(req):
    username = req.body.get("username")
    email = req.body.get("email")
    password = req.body.get("password")
    confirm_password = req.body.get("confirm_password")

    if None in [username, email, password, confirm_password]:
        return template["register-page"].render(
            {"info": "<p>Wszystkie pola musza zostac podane!</p>"}
        )

    # user must not already exist
    res, err = db.execute(
        f"SELECT * FROM users WHERE username='{username}' OR email='{email}'"
    )
    if db_guard(err):
        return "error"
    if len(res) != 0:
        return template["register-page"].render(
            {
                "info": "<p>Uzytkownik z ta nazwa uzytkownika / lub emailem juz istnieje!</p>"
            }
        )

    # passwords should match
    if password != confirm_password:
        return template["register-page"].render(
            {"info": "<p>Hasla sie nie zgadzaja!</p>"}
        )

    # password max length
    if len(password) not in range(4, 64):
        return template["register-page"].render(
            {"info": "<p>Dlugosc hasla powinna byc w zakresie 4-64</p>"}
        )

    # hash pass and insert
    res, err = db.execute(
        f"""INSERT INTO users (username, email, password) VALUES
            ('{username}', '{email}', '{sha256(password.encode()).hexdigest()}')"""
    )
    if db_guard(err):
        return "error"

    return "<h1>Rejestracja pomyslna<br>Mozesz sie teraz zalogowac</h1>"


def post_login(req):
    username = req.body.get("username")
    password = req.body.get("password")

    if None in [username, password]:
        return template["login-page"].render(
            {"info": "<p>Nazwa uzytkownika oraz haslo powinno zostac podane!</p>"}
        )

    # user must exist
    res, err = db.execute(f"SELECT * FROM users WHERE username='{username}'")
    if db_guard(err):
        return "error"

    pass_hash = sha256(password.encode()).hexdigest()

    if len(res) == 0 or res[0][3] != pass_hash:
        return template["login-page"].render(
            {"info": "<p>Niepoprawna nazwa uzytkownika lub haslo!</p>"}
        )

    return {
        "data": "<h1>Zalogowano</h1>",
        "headers": [
            ("Set-Cookie", f"username={username}; Path=/"),
            (
                "Set-Cookie",
                f"authkey={sha256((username + pass_hash + auth_secret).encode()).hexdigest()}; Path=/",
            ),
            ("HX-Redirect", "/"),
        ],
    }


def get_listings(req):
    search = req.params.get("search")

    if search is None:
        listings = ""
        for listing in listings_cache:
            listings += template["listing"].render(listing)
        return listings

    results, err = db.execute(
        f"SELECT * FROM listings WHERE name LIKE '%{search}%' OR description LIKE '%{search}%'"
    )
    if db_guard(err):
        return "error"

    if len(results) == 0:
        return "Brak wynikow wyszukiwania"

    results = [
        {
            "id": str(listing_id),
            "img": img,
            "name": name,
            "description": description,
            "price": str(price),
            "button": template["add-to-cart-button"].render({"id": str(listing_id)}),
        }
        for listing_id, img, name, description, price in results
    ]

    listings = ""
    for listing in results:
        listings += template["listing"].render(listing)

    return listings


def logout():
    return {
        "data": "Wylogowano",
        "headers": [
            ("Set-Cookie", "username=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT"),
            ("Set-Cookie", "authkey=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT"),
            ("HX-Redirect", "/"),
        ],
    }


def auth_check(req):
    username = req.cookies.get("username")
    authkey = req.cookies.get("authkey")

    if username is None or authkey is None:
        return False

    from_cache = auth_cache.get(username)
    if from_cache is not None:
        return from_cache == authkey

    from_db, _ = db.execute(f"SELECT password FROM users WHERE username='{username}'")
    if len(from_db) == 0:
        return False
    correct_hash = sha256((username + from_db[0][0] + auth_secret).encode()).hexdigest()
    auth_cache[username] = correct_hash

    return correct_hash == authkey


def get_navbar(req):
    if req.cookies.get("username") is not None:
        return cache["navbar-logged"]
    return cache["navbar"]


def get_listing(req):
    param_id = req.params.get("id")
    if param_id is None:
        return "Failed to fetch listing"

    listing_id = int(param_id)
    listing, err = db.execute(f"SELECT * FROM listings WHERE id={listing_id}")
    if db_guard(err) or len(listing) == 0:
        return "Failed to fetch listing"

    options = ""
    for i in range(1, 10 + 1):
        options += f"<option value='{i}'>{i}</option>"

    listing = listing[0]
    listing = {
        "id": str(listing[0]),
        "img": str(listing[1]),
        "name": str(listing[2]),
        "description": str(listing[3]),
        "price": str(listing[4]),
        "options": options,
    }

    return template["listing-page"].render(listing)


def get_shopping_cart(req):
    if not auth_check(req):
        return {
            "data": "Najpierw musisz sie zalogowac",
            "headers": [
                ("HX-Redirect", "/login"),
            ],
        }
    username = req.cookies.get("username")
    cart, err = db.execute(
        f"""SELECT shoppingcart.item_id, listings.image, listings.name, listings.description,
                   listings.price, shoppingcart.quantity
            FROM users
            JOIN shoppingcart ON users.id = shoppingcart.user_id
            JOIN listings ON shoppingcart.item_id = listings.id
            WHERE users.username = '{username}';"""
    )
    if db_guard(err):
        return "error"
    items = ""
    items_to_db = ""
    total_amount = 0.0
    for item in cart:
        if item[5] < 1:  # quantity
            continue
        total_amount += item[4] * item[5]
        item = {
            "item_id": str(item[0]),
            "img": item[1],
            "name": item[2],
            "description": item[3],
            "price": str(item[4]),
            "quantity": str(item[5]),
            "button": template["delete-from-cart-button"].render({"id": str(item[0])}),
        }
        items_to_db += item["item_id"] + ":" + item["quantity"] + ";"
        items += template["shopping-cart-item"].render(item)
    if items == "":
        return template["shopping-cart"].render(
            {"items": "Twoj koszyk jest pusty", "checkout": ""}
        )

    total_amount += delivery_cost

    total_amount = round(total_amount, 2)

    return template["shopping-cart"].render(
        {
            "items": items,
            "checkout": template["checkout-widget"].render(
                {
                    "delivery_cost": str(delivery_cost),
                    "total_amount": str(total_amount),
                    "items": items_to_db[:-1],
                }
            ),
        }
    )


def add_to_cart(req):
    if not auth_check(req):
        return {
            "data": "Najpierw musisz sie zalogowac",
            "headers": [
                ("HX-Redirect", "/login"),
            ],
        }

    username = req.cookies.get("username")
    item_id = req.params.get("id")
    count = req.params.get("count") or "1"

    res, err = db.execute(f"SELECT name FROM listings WHERE id={item_id}")
    if db_guard(err) or len(res) == 0 or count is None:
        return "error"

    count = int(count)

    if count < 1 or count > 1000:
        return "error"

    user_id, err = db.execute(f"SELECT id FROM users WHERE username='{username}';")
    if db_guard(err):
        return "error"

    user_id = user_id[0][0]

    _, err = db.execute(
        f"""INSERT OR IGNORE INTO shoppingcart (user_id, item_id, quantity)
            VALUES ({user_id}, {item_id}, 0);"""
    )
    if db_guard(err):
        return "error"

    _, err = db.execute(
        f"""UPDATE shoppingcart
            SET quantity = quantity + {count}
            WHERE user_id = {user_id} AND item_id = {item_id};"""
    )
    if db_guard(err):
        return "error"

    return f"""<p
    hx-trigger='load delay:2s'
    hx-swap='outerHTML'
    hx-target='closest button'
    hx-get='/content/add-to-cart-button?id={item_id}'>Dodano do koszyka</p>"""


def delete_from_cart(req):
    if not auth_check(req):
        return "error"

    username = req.cookies.get("username")
    item_id = req.params.get("id")

    if username is None or item_id is None:
        return "error"

    user_id, err = db.execute(f"SELECT id FROM users WHERE username='{username}';")
    if db_guard(err):
        return "error"

    user_id = user_id[0][0]

    _, err = db.execute(
        f"""UPDATE shoppingcart
            SET quantity = CASE
               WHEN quantity > 0 THEN quantity - 1
               ELSE 0
            END
            WHERE user_id = {user_id} AND item_id = {item_id};"""
    )
    if db_guard(err):
        return "error"

    return get_shopping_cart(req)


def get_transactions(req):
    if not auth_check(req):
        return {
            "data": "Najpierw musisz sie zalogowac",
            "headers": [
                ("HX-Redirect", "/login"),
            ],
        }

    username = req.cookies.get("username")

    if username is None:
        return "error"

    user_id, err = db.execute(f"SELECT id FROM users WHERE username='{username}'")
    if db_guard(err):
        return "error"

    user_id = user_id[0][0]

    transactions, err = db.execute(
        f"SELECT * FROM transactions WHERE user_id={user_id}"
    )
    if db_guard(err):
        return "error"

    out = ""

    for transaction in transactions:
        out += template["transaction"].render(
            {
                "id": str(transaction[0]),
                "price": str(transaction[3]),
                "status": transaction[4],
            }
        )

    if out == "":
        out = "Brak zamowien do wyswietlenia"

    return out


def get_profile(req):
    if not auth_check(req):
        return {
            "data": "Najpierw musisz sie zalogowac",
            "headers": [
                ("HX-Redirect", "/login"),
            ],
        }

    username = req.cookies.get("username")

    if username is None:
        return "error"

    user, err = db.execute(
        f"SELECT id, username, email FROM users WHERE username='{username}'"
    )
    if db_guard(err):
        return "error"

    if len(user) != 1:
        return "error"

    user = user[0]

    user = {
        "id": str(user[0]),
        "username": user[1],
        "email": user[2],
        "orders": get_transactions(req),
    }

    return template["profile"].render(user)


def get_transaction(req):
    transaction_id = req.params.get("id")

    if transaction_id is None:
        return "error"

    transaction_id = int(transaction_id)

    transaction, err = db.execute(
        f"SELECT * FROM transactions WHERE id={transaction_id}"
    )
    if db_guard(err):
        return "error"

    if len(transaction) != 1:
        return "error"

    transaction = transaction[0]

    # NOTE: this should be from the db (we assume you can only view your transactions)
    #       (which should be the case)
    username = req.cookies.get("username")

    listings = transaction[2]
    listings_str = ""
    for listing in listings.split(";"):
        if listing == "":
            break
        listing_id, listing_count = listing.split(":")
        listing_info, err = db.execute(f"SELECT * FROM listings WHERE id={listing_id}")
        if db_guard(err):
            return "error"
        if len(listing_info) != 1:
            return "error"
        listing_info = listing_info[0]
        listing_to_render = {
            "item_id": str(listing_info[0]),
            "img": listing_info[1],
            "name": listing_info[2],
            "price": str(listing_info[4]),
            "quantity": listing_count,
            "button": template["add-to-cart-button"].render(
                {"id": str(listing_info[0])}
            ),
        }
        listings_str += template["shopping-cart-item"].render(listing_to_render)

    buy_button = ""
    if transaction[4] == "Nie zaplacono":
        buy_button = f"""<input type="submit" value="Zaplac teraz"
        hx-get="/content/confirm-transaction?cost={transaction[3]}&transaction_id={transaction[0]}"
        hx-target="body"></input>"""

    transaction = {
        "id": str(transaction[0]),
        "username": username,
        "listings": listings_str,
        "price": str(transaction[3]),
        "status": transaction[4],
        "buy_button": buy_button,
    }

    return template["transaction-page"].render(transaction)


def confirm_transaction(req):
    transaction_id = req.params.get("transaction_id")

    if transaction_id is None:
        return "error"

    _, err = db.execute(
        f"UPDATE transactions SET status='Zaplacono' WHERE id={transaction_id};"
    )
    if db_guard(err):
        return "error"

    return """Transakcja zakonczona powodzeniem!<br>
Przekierowywanie na strone sklepu nastapi na pare sekund
<div hx-get="/profile" hx-trigger="load delay:3s" hx-target="body" hx-push-url="/profile" />"""


def empty_cart(user_id):
    _, _ = db.execute(f"DELETE FROM shoppingcart WHERE user_id={user_id};")


def make_order(req):
    if not auth_check(req):
        return "error"

    cost = req.params.get("cost")
    items = req.params.get("items")
    username = req.cookies.get("username")

    if cost is None or items is None or username is None:
        return "error"

    transaction_id, err = db.execute("SELECT count(id) FROM transactions")
    if db_guard(err):
        return "error"

    transaction_id = transaction_id[0][0] + 1

    user_id, err = db.execute(f"SELECT id FROM users WHERE username='{username}';")
    if db_guard(err):
        return "error"

    user_id = user_id[0][0]

    _, err = db.execute(
        f"""INSERT INTO transactions (id, user_id, items, total_price, status) VALUES
                        ({transaction_id}, {user_id}, '{items}', {cost}, 'Nie zaplacono')"""
    )
    if db_guard(err):
        return "error"

    empty_cart(user_id)

    return template["bank"].render({"total_amount": cost, "id": str(transaction_id)})


def change_pass(req):
    username = req.body.get("username")
    current_password = req.body.get("current-password")
    new_password = req.body.get("new-password")
    confirm_new_password = req.body.get("confirm-new-password")

    if None in [username, current_password, new_password, confirm_new_password]:
        return "ERROR: Wszystkie pola musza zostac wypelnione"

    # passwords should match
    if new_password != confirm_new_password:
        return "ERROR: Nowe haslo oraz potwierdzenie nowego hasla sa rozne"

    # password max length
    if len(new_password) not in range(4, 64):
        return "ERROR: Haslo powinno miec dlugosc w zakresie 4-64"

    # current_password should be correct
    expected_current_password, err = db.execute(
        f"SELECT password FROM users WHERE username='{username}';"
    )
    if db_guard(err):
        return "error"

    expected_current_password = expected_current_password[0][0]

    if sha256(current_password.encode()).hexdigest() != expected_current_password:
        return "ERROR: Nie poprawne obecne haslo"  # NOTE: Doesn't this enable bruteforce attacks?

    # change password
    res, err = db.execute(
        f"""UPDATE users SET password='{sha256(new_password.encode()).hexdigest()}' WHERE username='{username}';"""
    )
    if db_guard(err):
        return "error"

    return """<h1>Haslo zmienione pomyslnie<br>Mozesz sie teraz zalogowac</h1>
        <p hx-trigger='load delay:3s' hx-get='/logout'></p>"""


App(
    {
        "/": lambda req: template["base"].render(
            {
                "header": get_navbar(req),
                "main": template["index"].render({"listings": get_listings(req)}),
            }
        ),
        "/login": lambda req: template["base"].render(
            {"header": get_navbar(req), "main": cache["login"]}
        ),
        "/register": lambda req: template["base"].render(
            {"header": get_navbar(req), "main": cache["register"]}
        ),
        "/listing": lambda req: template["base"].render(
            {"header": get_navbar(req), "main": get_listing(req)}
        ),
        "/shopping-cart": lambda req: template["base"].render(
            {"header": get_navbar(req), "main": get_shopping_cart(req)}
        ),
        "/logout": logout,
        "/add-to-cart": add_to_cart,
        "/delete-from-cart": delete_from_cart,
        "/profile": lambda req: template["base"].render(
            {"header": get_navbar(req), "main": get_profile(req)}
        ),
        "/transaction": lambda req: template["base"].render(
            {"header": get_navbar(req), "main": get_transaction(req)}
        ),
        "/make-order": make_order,
        "/confirm-transaction": confirm_transaction,
        "/get/listing": get_listing,
        "/get/listings": get_listings,
        "/get/transaction": get_transaction,
        "/post/login": post_login,
        "/post/register": post_register,
        "/content/index": lambda req: template["index"].render(
            {"listings": get_listings(req)}
        ),
        "/content/login": lambda: cache["login"],
        "/content/register": lambda: cache["register"],
        "/content/shopping-cart": get_shopping_cart,
        "/content/add-to-cart-button": lambda req: template[
            "add-to-cart-button"
        ].render({"id": req.params.get("id")}),
        "/content/profile": get_profile,
        "/content/confirm-transaction": lambda req: template["bank"].render(
            {
                "total_amount": str(req.params.get("cost")),
                "id": str(req.params.get("transaction_id")),
            }
        ),
        "/change-pass": lambda: cache["change-pass"],
        "/post/change-pass": change_pass,
        "/clicked": lambda: "Hello from the server!",
    },
    static_hosting="static",
    logging=True,
).run()
