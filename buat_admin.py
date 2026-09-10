from werkzeug.security import generate_password_hash
from utils.db_utils import insert_user

username = input("Username admin: ")
password = input("Password admin: ")
nama = input("Nama lengkap: ")

password_hash = generate_password_hash(password)
insert_user(username, password_hash, nama, role="admin")
print(f"Akun '{username}' berhasil dibuat!")