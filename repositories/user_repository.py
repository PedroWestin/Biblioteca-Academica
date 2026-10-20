from models.user import User


class UserRepository:
    def __init__(self, conn):
        self.conn = conn

    def add(self, user: User) -> User:
        cur = self.conn.execute(
            "INSERT INTO users(name, email, password_hash, role, profile) VALUES (?,?,?,?,?)",
            (user.name, user.email, user.password_hash, user.ROLE, user.PROFILE),
        )
        self.conn.commit()
        user.id = cur.lastrowid
        return user

    def by_id(self, user_id):
        row = self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return User.from_row(row) if row else None

    def by_email(self, email):
        row = self.conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
        return User.from_row(row) if row else None
