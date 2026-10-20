class NotificationService:
    """Persiste avisos in-app e despacha para canais extras (e-mail, SMS...) — callables (user_id, msg)."""

    def __init__(self, repo, channels=None):
        self.repo = repo
        self.channels = channels or []

    def send(self, user_id, message):
        self.repo.add(user_id, message)
        for channel in self.channels:
            channel(user_id, message)

    def send_once_per_day(self, user_id, message) -> bool:
        if self.repo.exists_today(user_id, message):
            return False
        self.send(user_id, message)
        return True

    def unread(self, user_id):
        return self.repo.unread(user_id)

    def mark_read(self, user_id):
        self.repo.mark_all_read(user_id)
