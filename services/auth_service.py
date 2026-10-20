from werkzeug.security import check_password_hash, generate_password_hash

from factories.user_factory import user_factory_for
from services.errors import BusinessError


class AuthService:
    SELF_SIGNUP_PROFILES = ("ALUNO", "PROFESSOR")

    def __init__(self, users):
        self.users = users

    def _create(self, profile, name, email, password):
        if not name.strip() or "@" not in email or len(password) < 6:
            raise BusinessError("Informe nome, e-mail válido e uma senha com pelo menos 6 caracteres.")
        if self.users.by_email(email):
            raise BusinessError("Este e-mail já está cadastrado.")
        user = user_factory_for(profile).create_user(
            name.strip(), email.lower().strip(), generate_password_hash(password)
        )
        return self.users.add(user)

    def register(self, name, email, password, profile="ALUNO"):
        if profile not in self.SELF_SIGNUP_PROFILES:
            raise BusinessError("Perfil não permitido para cadastro.")
        return self._create(profile, name, email, password)

    def create_admin(self, name, email, password):
        return self._create("ADMIN", name, email, password)

    def login(self, email, password):
        user = self.users.by_email(email)
        if not user or not check_password_hash(user.password_hash, password):
            raise BusinessError("E-mail ou senha incorretos.")
        return user

    def get(self, user_id):
        return self.users.by_id(user_id)
