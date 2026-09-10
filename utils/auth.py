from flask_login import UserMixin
from utils.db_utils import get_user_by_id

class User(UserMixin):
    def __init__(self, id, username, nama_lengkap, role):
        self.id = id
        self.username = username
        self.nama_lengkap = nama_lengkap
        self.role = role

    @staticmethod
    def get(user_id):
        row = get_user_by_id(user_id)
        if row is None:
            return None
        return User(row.Id, row.Username, row.NamaLengkap, row.Role)