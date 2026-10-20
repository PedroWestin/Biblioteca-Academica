class NotificationRepository:
    def __init__(self, conn):
        self.conn = conn

    def add(self, user_id, message):
        self.conn.execute("INSERT INTO notifications(user_id, message) VALUES (?,?)", (user_id, message))
        self.conn.commit()

    def exists_today(self, user_id, message):
        return self.conn.execute(
            "SELECT 1 FROM notifications WHERE user_id=? AND message=? AND date(created_at)=date('now')",
            (user_id, message),
        ).fetchone() is not None

    def unread(self, user_id):
        return self.conn.execute(
            "SELECT * FROM notifications WHERE user_id=? AND read=0 ORDER BY id DESC", (user_id,)
        ).fetchall()

    def mark_all_read(self, user_id):
        self.conn.execute("UPDATE notifications SET read=1 WHERE user_id=?", (user_id,))
        self.conn.commit()
