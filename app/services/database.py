import sqlite3

from app.services.types import CleanerState


class CleanerDatabase:
    def __init__(self, db_name: str = "cleaner.db"):
        self.db_name = db_name
        self._create_table()

    def _create_table(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS states (
                    mac TEXT,
                    timestamp REAL,
                    distance_front REAL,
                    distance_side REAL,
                    distance_hall REAL,
                    angle REAL
                )
            """)
            conn.commit()

    def add(self, mac: str, state: CleanerState):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO states (mac, timestamp, distance_front, distance_side, distance_hall, angle)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    mac,
                    state.timestamp,
                    state.distance_front,
                    state.distance_side,
                    state.distance_hall,
                    state.angle,
                ),
            )
            conn.commit()

    def get_by_mac(self, mac: str) -> list[CleanerState]:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT timestamp, distance_front, distance_side, distance_hall, angle FROM states WHERE mac = ?
            """,
                (mac,),
            )
            rows = cursor.fetchall()
            return [CleanerState(*row) for row in rows]
