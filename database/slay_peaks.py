import sqlite3

from database.utils import open_cursor

class SlayPeaks:
    def __init__(self):
        self.connection = sqlite3.Connection("database/slay_peaks.sqlite.db")

    def insert_peak(self, server_name: str, timestamp: int, player_count: int):
        self.connection.executescript(
            f"INSERT OR IGNORE INTO {server_name.upper()}_PEAKS"
            + f" (TIMESTAMP, PLAYER_COUNT) VALUES ({timestamp},{player_count})"
        )
    
    def fetch_peaks_between_timestamps(
        self,
        server_name: str,
        from_timestamp: int,
        to_timestamp: int,
        steps: int = 3600
    ) -> list[int, int]:

        """ return list[tuple[hour_timestamp, player_count]] """

        with open_cursor(self.connection) as cursor:
            cursor.execute(
                "WITH RECURSIVE TIMESTAMPS(TIMESTAMP) AS"
                f" (VALUES({to_timestamp}) UNION ALL"
                f" SELECT TIMESTAMP + {steps} FROM TIMESTAMPS"
                f" WHERE TIMESTAMP < {from_timestamp})"
                " SELECT a.TIMESTAMP, b.PLAYER_COUNT FROM TIMESTAMPS a"
                f" LEFT JOIN {server_name}_PEAKS b ON a.TIMESTAMP = b.TIMESTAMP"
                " ORDER BY a.TIMESTAMP ASC"
            )

            return cursor.fetchall()
    
    def fetch_highest_peaks_in_intervals(
        self,
        server_name: str,
        from_timestamp: int,
        to_timestamp: int,
        interval: int = 86400
    ) -> list[int, int]:

        """ return list[tuple[hour_timestamp, player_count]] """

        with open_cursor(self.connection) as cursor:
            cursor.execute(
                "WITH RECURSIVE TIMESTAMPS(TIMESTAMP) AS"
                f" (VALUES({to_timestamp})"
                f" UNION ALL SELECT TIMESTAMP + {interval} FROM TIMESTAMPS"
                f" WHERE TIMESTAMP < {from_timestamp})"
                " SELECT a.TIMESTAMP, MAX(b.PLAYER_COUNT)"
                f" FROM TIMESTAMPS a LEFT JOIN {server_name}_PEAKS b"
                " ON b.TIMESTAMP >= a.TIMESTAMP"
                f" AND b.TIMESTAMP < a.TIMESTAMP + {interval}"
                " GROUP BY a.TIMESTAMP ORDER BY a.TIMESTAMP ASC"
            )

            return cursor.fetchall()
    
    def fetch_highest_peak_between_timestamps(
        self, server_name: str, from_timestamp: int, to_timestamp: int
    ) -> tuple[int, int]:
        
        """ return tuple[hour_timestamp, player_count]"""

        with open_cursor(self.connection) as cursor:
            cursor.execute(
                f"SELECT {to_timestamp}, MAX(a.PLAYER_COUNT) as PLAYER_COUNT"
                f" FROM {server_name}_PEAKS a"
                f" WHERE a.TIMESTAMP >= {to_timestamp}"
                f" AND a.TIMESTAMP < {from_timestamp}"
            )

            return cursor.fetchone()
