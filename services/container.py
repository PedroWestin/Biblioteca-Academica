from types import SimpleNamespace

from repositories.book_repository import BookRepository
from repositories.circulation_repository import FineRepository, LoanRepository, ReservationRepository
from repositories.notification_repository import NotificationRepository
from repositories.user_repository import UserRepository
from services.auth_service import AuthService
from services.catalog_service import CatalogService
from services.fine_service import FineService
from services.loan_service import LoanService
from services.notification_service import NotificationService


def build_services(conn, channels=None):
    """Composição das dependências (Persistência → Serviços). A UI só conhece este objeto."""
    books, loans = BookRepository(conn), LoanRepository(conn)
    reservations, fines = ReservationRepository(conn), FineRepository(conn)
    notifier = NotificationService(NotificationRepository(conn), channels)
    fine_service = FineService(fines, notifier)
    return SimpleNamespace(
        auth=AuthService(UserRepository(conn)),
        catalog=CatalogService(books),
        notifications=notifier,
        fines=fine_service,
        loans=LoanService(loans, books, reservations, fine_service, notifier),
    )
