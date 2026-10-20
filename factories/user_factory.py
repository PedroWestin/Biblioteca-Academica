"""Factory Method para perfis de usuário (Leitor: Aluno/Professor; Administrador)."""
from abc import ABC, abstractmethod

from models.user import Administrator, Professor, Student, User


class UserFactory(ABC):
    @abstractmethod
    def create_user(self, name: str, email: str, password_hash: str) -> User:
        """Factory method."""


class StudentFactory(UserFactory):
    def create_user(self, name, email, password_hash):
        return Student(name, email, password_hash)


class ProfessorFactory(UserFactory):
    def create_user(self, name, email, password_hash):
        return Professor(name, email, password_hash)


class AdministratorFactory(UserFactory):
    def create_user(self, name, email, password_hash):
        return Administrator(name, email, password_hash)


_FACTORIES = {"ALUNO": StudentFactory(), "PROFESSOR": ProfessorFactory(), "ADMIN": AdministratorFactory()}


def user_factory_for(profile: str) -> UserFactory:
    try:
        return _FACTORIES[profile]
    except KeyError:
        raise ValueError(f"Perfil inválido: {profile}") from None
