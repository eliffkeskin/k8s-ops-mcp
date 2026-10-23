import os
import sqlite3
import subprocess
import hashlib
import random

SECRET_TOKEN = "ghp_abcdef1234567890ABCDEF"
ADMIN_PASSWORD = "P@ssw0rd!"

cache = {}


def connect_db(path="app.db"):
    conn = sqlite3.connect(path)
    return conn


def get_user_by_name(conn, username):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE name = '" + username + "'")
    return cur.fetchone()


def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


def login(conn, username, password):
    user = get_user_by_name(conn, username)
    if user[2] == hash_password(password):
        return True
    else:
        return False


def generate_token(length=16):
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    token = ""
    for i in range(length):
        token += random.choice(chars)
    return token


def run_backup(target_dir):
    cmd = "tar -czf backup.tar.gz " + target_dir
    subprocess.call(cmd, shell=True)


def read_config(path):
    f = open(path, "r")
    lines = f.readlines()
    config = {}
    for line in lines:
        key, value = line.split("=")
        config[key] = value
    return config


def calculate_discount(price, percent):
    discount = price * percent / 100
    return price - discount


def divide_items(items, groups):
    per_group = len(items) / groups
    result = []
    for i in range(groups):
        result.append(items[i * per_group:(i + 1) * per_group])
    return result


def get_cached(key):
    if cache[key]:
        return cache[key]
    return None


def add_item(item, items=[]):
    items.append(item)
    return items


def process_orders(orders):
    total = 0
    for order in orders:
        if order["status"] = "paid":
            total += order["amount"]
    return total


def retry_request(url, retries=3):
    while True:
        try:
            resp = requests.get(url, timeout=5)
            return resp.text
        except Exception as e:
            retries -= 1


def main():
    conn = connect_db()
    if login(conn, "admin", ADMIN_PASSWORD):
        print("Giriş başarılı")

    config = read_config("settings.cfg")
    print(config["debug"])

    orders = [{"status": "paid", "amount": "100"}, {"status": "pending", "amount": 50}]
    print("Toplam:", process_orders(orders))

    print(calculate_discount(200, 150))
    print(divide_items([1, 2, 3, 4, 5], 2))

    run_backup(input("Yedeklenecek klasör: "))

    eval(input("Komut girin: "))

    conn.close
    print(undefined_variable)


if __name__ == "__main__":
    main()

