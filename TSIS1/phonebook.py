import csv
import json
from datetime import datetime
from connect import get_connection


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    for path in ["schema.sql", "procedures.sql"]:
        with open(path, "r", encoding="utf-8") as f:
            cur.execute(f.read())
    conn.commit()
    cur.close()
    conn.close()


def ensure_group(cur, group_name):
    cur.execute("INSERT INTO groups(name) VALUES (%s) ON CONFLICT(name) DO NOTHING", (group_name,))
    cur.execute("SELECT id FROM groups WHERE name=%s", (group_name,))
    return cur.fetchone()[0]


def upsert_contact(cur, name, email, birthday, group_name, phones, overwrite=False):
    group_id = ensure_group(cur, group_name)
    cur.execute("SELECT id FROM contacts WHERE name=%s", (name,))
    row = cur.fetchone()
    if row and not overwrite:
        return False
    if row and overwrite:
        contact_id = row[0]
        cur.execute(
            "UPDATE contacts SET email=%s, birthday=%s, group_id=%s WHERE id=%s",
            (email, birthday, group_id, contact_id)
        )
        cur.execute("DELETE FROM phones WHERE contact_id=%s", (contact_id,))
    else:
        cur.execute(
            "INSERT INTO contacts(name,email,birthday,group_id) VALUES(%s,%s,%s,%s) RETURNING id",
            (name, email, birthday, group_id)
        )
        contact_id = cur.fetchone()[0]
    for p in phones:
        cur.execute(
            "INSERT INTO phones(contact_id,phone,type) VALUES(%s,%s,%s)",
            (contact_id, p["phone"], p["type"])
        )
    return True


def fetch_contacts(group_filter=None, email_part=None, sort_by="name", limit=10, offset=0):
    conn = get_connection()
    cur = conn.cursor()
    sort_map = {"name": "c.name", "birthday": "c.birthday NULLS LAST", "date": "c.created_at"}
    order_sql = sort_map.get(sort_by, "c.name")
    query = """
        SELECT c.id, c.name, c.email, c.birthday, g.name,
               COALESCE(string_agg(p.phone || ' (' || p.type || ')', ', '), '') AS phones
        FROM contacts c
        LEFT JOIN groups g ON g.id = c.group_id
        LEFT JOIN phones p ON p.contact_id = c.id
        WHERE (%s IS NULL OR g.name = %s)
          AND (%s IS NULL OR c.email ILIKE %s)
        GROUP BY c.id, g.name
        ORDER BY """ + order_sql + """
        LIMIT %s OFFSET %s
    """
    like_email = f"%{email_part}%" if email_part else None
    cur.execute(query, (group_filter, group_filter, like_email, like_email, limit, offset))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def paginated_console():
    group_filter = input("Group filter (or empty): ").strip() or None
    email_filter = input("Email contains (or empty): ").strip() or None
    sort_by = input("Sort by [name/birthday/date]: ").strip() or "name"
    page = 0
    page_size = 5
    while True:
        rows = fetch_contacts(group_filter, email_filter, sort_by, page_size, page * page_size)
        print(f"\nPage {page + 1}")
        if not rows:
            print("No contacts")
        for r in rows:
            print(f"{r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]}")
        cmd = input("next / prev / quit: ").strip().lower()
        if cmd == "next":
            page += 1
        elif cmd == "prev" and page > 0:
            page -= 1
        elif cmd == "quit":
            break


def export_json(path):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.name, c.email, c.birthday, g.name, p.phone, p.type
        FROM contacts c
        LEFT JOIN groups g ON g.id = c.group_id
        LEFT JOIN phones p ON p.contact_id = c.id
        ORDER BY c.name
    """)
    data = {}
    for name, email, birthday, group_name, phone, phone_type in cur.fetchall():
        if name not in data:
            data[name] = {
                "name": name,
                "email": email,
                "birthday": birthday.isoformat() if birthday else None,
                "group": group_name or "Other",
                "phones": []
            }
        if phone:
            data[name]["phones"].append({"phone": phone, "type": phone_type})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(data.values()), f, indent=2, ensure_ascii=False)
    cur.close()
    conn.close()


def import_json(path):
    with open(path, "r", encoding="utf-8") as f:
        contacts = json.load(f)
    conn = get_connection()
    cur = conn.cursor()
    for c in contacts:
        birthday = datetime.strptime(c["birthday"], "%Y-%m-%d").date() if c.get("birthday") else None
        cur.execute("SELECT id FROM contacts WHERE name=%s", (c["name"],))
        exists = cur.fetchone()
        overwrite = False
        if exists:
            action = input(f"{c['name']} exists. skip/overwrite: ").strip().lower()
            if action == "skip":
                continue
            overwrite = action == "overwrite"
        upsert_contact(
            cur,
            c["name"],
            c.get("email"),
            birthday,
            c.get("group", "Other"),
            c.get("phones", []),
            overwrite
        )
    conn.commit()
    cur.close()
    conn.close()


def import_csv(path):
    conn = get_connection()
    cur = conn.cursor()
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            birthday = datetime.strptime(row["birthday"], "%Y-%m-%d").date() if row.get("birthday") else None
            phones = [{"phone": row["phone"], "type": row.get("phone_type", "mobile")}]
            upsert_contact(
                cur,
                row["name"],
                row.get("email"),
                birthday,
                row.get("group", "Other"),
                phones,
                overwrite=True
            )
    conn.commit()
    cur.close()
    conn.close()


def add_phone_procedure():
    name = input("Contact name: ").strip()
    phone = input("Phone: ").strip()
    phone_type = input("Type [home/work/mobile]: ").strip()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("CALL add_phone(%s,%s,%s)", (name, phone, phone_type))
    conn.commit()
    cur.close()
    conn.close()


def move_group_procedure():
    name = input("Contact name: ").strip()
    group_name = input("New group: ").strip()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("CALL move_to_group(%s,%s)", (name, group_name))
    conn.commit()
    cur.close()
    conn.close()


def search_all():
    q = input("Query: ").strip()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM search_contacts(%s)", (q,))
    for row in cur.fetchall():
        print(row)
    cur.close()
    conn.close()


def main():
    while True:
        print("\n1.Init DB 2.Paginated Search 3.Export JSON 4.Import JSON 5.Import CSV 6.Add Phone 7.Move Group 8.Search 9.Exit")
        c = input("Choose: ").strip()
        if c == "1":
            init_db()
        elif c == "2":
            paginated_console()
        elif c == "3":
            export_json(input("File path: ").strip())
        elif c == "4":
            import_json(input("File path: ").strip())
        elif c == "5":
            import_csv(input("CSV path: ").strip())
        elif c == "6":
            add_phone_procedure()
        elif c == "7":
            move_group_procedure()
        elif c == "8":
            search_all()
        elif c == "9":
            break


if __name__ == "__main__":
    main()
