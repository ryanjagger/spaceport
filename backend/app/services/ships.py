from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Ship


def list_ships(session: Session) -> list[Ship]:
    return list(session.scalars(select(Ship).order_by(Ship.id)))


def get_ship(session: Session, ship_id: int) -> Ship:
    ship = session.get(Ship, ship_id)
    if ship is None:
        raise NotFoundError(f"Ship {ship_id} does not exist.")
    return ship
