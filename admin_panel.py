#!/bin/python

import sys
sys.path.append("./sqlite-server.py")
import sqlite

from hashlib import sha256
from random import choices
from string import ascii_letters, digits

# db = sqlite.DB(host="localhost", port=4567, database="shop", secret="secret")
db = sqlite.DBLocal(filename="database.db")


def recreate_db():
    db.execute(""" DROP TABLE users; """)
    db.execute(""" DROP TABLE listings; """)
    db.execute(""" DROP TABLE shoppingcart; """)
    db.execute(""" DROP TABLE transactions; """)

    # TODO: add timestamps

    db.execute_or_panic(
        """
    CREATE TABLE users (
        id integer primary key autoincrement,
        username string,
        email string,
        password string
    );"""
    )
    db.execute_or_panic(
        """
    CREATE TABLE listings (
        id integer primary key autoincrement,
        image string,
        name string,
        description string,
        price money
    );"""
    )
    db.execute_or_panic(
        """
    CREATE TABLE shoppingcart (
        id integer primary key autoincrement,
        user_id integer,
        item_id integer,
        quantity integer,
        UNIQUE (user_id, item_id)
    );"""
    )
    db.execute_or_panic(
        """
    CREATE TABLE transactions (
        id integer primary key autoincrement,
        user_id integer,
        items string,
        total_price money,
        status string
    );"""
    )


def insert_example_data():
    db.execute_or_panic(
        """
    INSERT INTO listings (image, name, description, price) VALUES
        ('https://a.allegroimg.com/s512/11553a/826edaa34a668938b70080b741c5/MONOPOLY-CUDA-SWIATA-STRATEGICNZA-GRA-PLANSZOWA-PODROZE-PO-SWIECIE-EAN-GTIN-5036905054461', 'Gra planszowa Winning Moves Monopoly: Cuda Świata', 'Gra stworzona została przez popularną markę Winning Moves. Pochodzi z serii towarzyskich gier planszowych i karcianych uwielbianych przez graczy na całym świecie.', 119.90),
        ('https://gryplanszowe.pl/pol_pm_Ubongo-4913_1.jpg', 'Gra Ubongo', '"Ubongo" to światowy bestseller, który zdobył popularność dzięki bardzo prostym zasadom i błyskawicznej rozgrywce. Dwa poziomy trudności łamigłówek, umożliwiają dostosowanie gry do wieku i doświadczenia graczy.', 109.95),
        ('https://gryplanszowe.pl/pol_pm_Kakao-94_6.jpg', 'Gra Kakao', 'Bestsellerowa gra rodzinna! Zdobądź sławę i bogactwo dla swojego ludu.
    Kakao – najlepsza gra do filiżanki czekolady!', 99.90),
        ('https://gryplanszowe.pl/pol_pm_Roj-42_2.jpg', 'Gra Rój', 'Bestsellerowa gra logiczna dla dwóch graczy? Bez namysłu... Rój!
    Uznana przez MENSA za najlepszą grę umysłową.', 119.50),
        ('https://gryplanszowe.pl/pol_pm_Detektywistyczne-historie-8223_1.jpg', 'Gra Detektywistyczne historie', '50 zagadek dla sprytnych superagentów.', 39.99);
    """  # noqa
    )
    db.execute_or_panic(
        """
    INSERT INTO users (username, email, password) VALUES
        ('user1', 'user1@em.ail', 'f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b');
    """
    )
    db.execute_or_panic(
        """
    INSERT INTO shoppingcart (user_id, item_id, quantity) VALUES
        (1, 1, 1),
        (1, 2, 2);
    """
    )
    db.execute_or_panic(
        """
    INSERT INTO transactions (user_id, items, total_price, status) VALUES
        (1, '1:2;3:1;', 339.7, 'Dostarczono'),
        (1, '2:1;4:1;', 229.45, 'Dostarczono');
    """
    )


def new_product():
    image = input("Image URL: ")
    name = input("Product name: ")
    description = input("Product description: ")
    price = float(input("Product price: "))
    _, err = db.execute(
        f"""INSERT INTO listings (image, name, description, price) VALUES
        ('{image}', '{name}', '{description}', {price});"""
    )
    if err is not None:
        print(f"ERROR: {err}")
        exit(1)
    print("Product added")


def remove_product():
    product_id = int(input("Product ID: "))
    _, err = db.execute(f"DELETE FROM listings WHERE id={product_id};")
    if err is not None:
        print(f"ERROR: {err}")
        exit(1)

    rows_affected = db.rows_affected()

    if rows_affected == 0:
        print("Product doesn't exist. Did nothing")
    else:
        print("Product removed")


def update_product():
    product_id = int(input("Product ID: "))
    image = input("Image URL: ")
    name = input("Product name: ")
    description = input("Product description: ")
    price = input("Product price: ")
    _, err = db.execute(
        f"""UPDATE listings SET image='{image}', name='{name}',
        description='{description}', price={price} WHERE id={product_id};"""
    )
    if err is not None:
        print(f"ERROR: {err}")
        exit(1)
    print("Product updated")


def new_user():
    username = input("Username: ")
    email = input("E-mail: ")
    password = input("Password: ")
    _, err = db.execute(
        f"""INSERT INTO users (username, email, password) VALUES
            ('{username}', '{email}', '{sha256(password.encode()).hexdigest()}');"""
    )
    if err is not None:
        print(f"ERROR: {err}")
        exit(1)
    print("User added")


def remove_user():
    username = input("Username: ")
    _, err = db.execute(f"DELETE FROM users WHERE username='{username}';")
    if err is not None:
        print(f"ERROR: {err}")
        exit(1)

    rows_affected = db.rows_affected()

    if rows_affected == 0:
        print("User doesn't exist. Did nothing")
    else:
        print("User removed")


def change_user_password():
    username = input("Username: ")
    password = input("New password: ")
    _, err = db.execute(
        f"""UPDATE users SET password='{sha256(password.encode()).hexdigest()}'
            WHERE username='{username}';"""
    )
    if err is not None:
        print(f"ERROR: {err}")
        exit(1)
    print("Password changed")


def reset_user_password():
    username = input("Username: ")
    new_password = "".join(choices(ascii_letters + digits, k=10))
    _, err = db.execute(
        f"""UPDATE users SET password='{sha256(new_password.encode()).hexdigest()}'
            WHERE username='{username}';"""
    )
    if err is not None:
        print(f"ERROR: {err}")
        exit(1)
    print(f"Password changed\nNew password: {new_password}")


if __name__ == "__main__":
    args = sys.argv

    usage = f"Usage: {args[0]} <option>"

    if len(args) < 2:
        print(usage)
        exit(0)

    option = args[1]

    if option == "recreate-db":
        recreate_db()

    elif option == "example-data":
        insert_example_data()

    elif option == "re":
        recreate_db()
        insert_example_data()

    elif option == "new-product":
        new_product()

    elif option == "remove-product":
        remove_product()

    elif option == "update-product":
        update_product()

    elif option == "new-user":
        new_user()

    elif option == "remove-user":
        remove_user()

    elif option == "change-user-password":
        change_user_password()

    elif option == "reset-user-password":
        reset_user_password()

    else:
        print(usage)
        exit(1)
