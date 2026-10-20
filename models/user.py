from dataclasses import dataclass


@dataclass
class User:
    name: str
    email: str
    password_hash: str
    id: int | None = None

    ROLE = "LEITOR"      # LEITOR | ADMIN
    PROFILE = ""         # ALUNO | PROFESSOR | ADMIN
    LABEL = ""
    _registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.PROFILE:
            User._registry[cls.PROFILE] = cls

    @property
    def is_admin(self) -> bool:
        return self.ROLE == "ADMIN"

    @staticmethod
    def from_row(row) -> "User":
        cls = User._registry[row["profile"]]
        return cls(name=row["name"], email=row["email"], password_hash=row["password_hash"], id=row["id"])


class Student(User):
    PROFILE, LABEL = "ALUNO", "Aluno"


class Professor(User):
    PROFILE, LABEL = "PROFESSOR", "Professor"


class Administrator(User):
    ROLE, PROFILE, LABEL = "ADMIN", "ADMIN", "Bibliotecário"
