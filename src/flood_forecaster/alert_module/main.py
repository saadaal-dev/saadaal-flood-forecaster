import psycopg2

def get_risk_level(conn_params, river_id):
    query = "SELECT risk_level FROM predicted_river_level WHERE id = %s;"
    query = "SHOW TABLES;"
    with psycopg2.connect(**conn_params) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (river_id,))
            result = cur.fetchone()
            return result[0] if result else None

# Example usage:
if __name__ == "__main__":
    conn_params = {
        'host': '68.183.13.232',
        'database': 'postgres',
        'user': 'postgres',
        'password': ''
    }
    river_id = 4  # Replace with the actual river_id you want to query
    risk_level = get_risk_level(conn_params, river_id)
    print(f"Risk level for river_id {river_id}: {risk_level}")