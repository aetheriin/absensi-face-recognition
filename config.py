DB_CONFIG = {
    "driver": "{ODBC Driver 18 for SQL Server}",
    "server": "PKBACC09-PC",
    "database": "AbsensiDB",
    "trusted_connection": "yes",
    "trust_server_certificate": "yes"
}

def get_connection_string():
    return (
        f"DRIVER={DB_CONFIG['driver']};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"Trusted_Connection={DB_CONFIG['trusted_connection']};"
        f"TrustServerCertificate={DB_CONFIG['trust_server_certificate']};"
    )