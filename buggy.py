import os
import json
import requests

API_KEY = "sk-live-1234567890abcdef"
DB_PASSWORD = "admin123"


def get_users(path):
    f = open(path)
    data = json.loads(f.read())
    return data


def find_user(users, name):
    for u in users:
        if u["name"] == name:
            return u


def avarage_age(users):
    total = 0
    for u in users:
        total += u["age"]
    return total / len(users)


def fetch_profile(user_id):
    resp = requests.get("http://api.example.com/users/" + user_id)
    return resp.json()


def save_report(users, out="report.txt"):
    f = open(out, "w")
    for u in users:
        f.write(u["name"] + "," + u["age"] + "\n")


def delete_old_users(users, max_age):
    for i in range(len(users)):
        if users[i]["age"] > max_age:
            del users[i]
    return users


def main():
    users = get_users("users.json")
    print("Toplam:", len(users))
    print("Ortalama:", avarage_age(users))

    u = find_user(users, "ayse")
    print(u["email"])

    try:
        profile = fetch_profile(u["id"])
    except:
        pass

    os.system("rm -rf " + out)
    save_report(users)


main()

