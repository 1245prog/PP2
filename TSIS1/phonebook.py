from __future__ import annotations

import csv
import json
from datetime import datetime, date
from pathlib import Path
from typing import Any

from psycopg2.extras import RealDictCursor

from config import (
    CSV_DEFAULT_PATH,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SORT,
    JSON_DEFAULT_EXPORT,
    JSON_DEFAULT_IMPORT,
)
import connect


def ask(prompt: str, allow_empty: bool = False) -> str:
    while True:
        value = input(prompt).strip()
        if value or allow_empty:
            return value
        print('Value cannot be empty.')


def ask_optional(prompt: str) -> str | None:
    value = input(prompt).strip()
    return value or None


def ask_int(prompt: str, minimum: int | None = None, maximum: int | None = None) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
            if minimum is not None and value < minimum:
                raise ValueError
            if maximum is not None and value > maximum:
                raise ValueError
            return value
        except ValueError:
            print('Enter a valid integer.')


def ask_date(prompt: str) -> date | None:
    raw = input(prompt).strip()
    if not raw:
        return None
    for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    print('Invalid date. Use YYYY-MM-DD.')
    return ask_date(prompt)


def confirm(prompt: str) -> bool:
    return input(prompt).strip().lower() in {'y', 'yes', '1', 'true'}


def normalize_phone_type(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().lower()
    return value if value in {'home', 'work', 'mobile'} else None


def ensure_group(cur, group_name: str | None) -> int | None:
    group_name = (group_name or '').strip()
    if not group_name:
        return None
    cur.execute(
        '''
        INSERT INTO groups (name)
        VALUES (%s)
        ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
        ''',
        (group_name,),
    )
    return int(cur.fetchone()[0])


def get_contact_id_by_name(cur, name: str) -> int | None:
    cur.execute('SELECT id FROM contacts WHERE name = %s', (name,))
    row = cur.fetchone()
    return int(row[0]) if row else None


def list_contacts(group_name: str | None = None, sort_by: str = DEFAULT_SORT) -> list[dict[str, Any]]:
    with connect.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                '''
                SELECT
                    c.id AS contact_id,
                    c.name,
                    c.email,
                    c.birthday,
                    g.name AS group_name,
                    COALESCE(string_agg(ph.type || ': ' || ph.phone, ', ' ORDER BY ph.type, ph.phone), '') AS phones,
                    c.created_at
                FROM contacts c
                LEFT JOIN groups g ON g.id = c.group_id
                LEFT JOIN phones ph ON ph.contact_id = c.id
                WHERE (%s IS NULL OR g.name = %s)
                GROUP BY c.id, c.name, c.email, c.birthday, g.name, c.created_at
                ORDER BY
                    CASE WHEN %s = 'birthday' THEN c.birthday END NULLS LAST,
                    CASE WHEN %s = 'date_added' THEN c.created_at END DESC,
                    CASE WHEN %s = 'name' THEN c.name END
                ''',
                (group_name, group_name, sort_by, sort_by, sort_by),
            )
            return [dict(row) for row in cur.fetchall()]


def list_contacts_page(limit: int, offset: int, sort_by: str = DEFAULT_SORT, group_name: str | None = None) -> list[dict[str, Any]]:
    with connect.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT * FROM get_contacts_page(%s, %s, %s, %s)', (limit, offset, sort_by, group_name))
            return [dict(row) for row in cur.fetchall()]


def get_total_contacts(group_name: str | None = None) -> int:
    with connect.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT get_total_contacts(%s)', (group_name,))
            return int(cur.fetchone()[0])


def search_contacts(query: str) -> list[dict[str, Any]]:
    with connect.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT * FROM search_contacts(%s)', (query,))
            return [dict(row) for row in cur.fetchall()]


def print_contacts(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print('No contacts found.')
        return

    header = f"{'ID':<4} {'Name':<22} {'Email':<25} {'Birthday':<12} {'Group':<10} {'Phones'}"
    print(header)
    print('-' * len(header))
    for row in rows:
        birthday = row.get('birthday')
        birthday_str = birthday.isoformat() if hasattr(birthday, 'isoformat') and birthday else '-'
        print(
            f"{row.get('contact_id', row.get('id', '-')):<4} "
            f"{str(row.get('name', ''))[:22]:<22} "
            f"{str(row.get('email', '-'))[:25]:<25} "
            f"{birthday_str:<12} "
            f"{str(row.get('group_name', '-'))[:10]:<10} "
            f"{row.get('phones', '')}"
        )


def show_paginated_contacts(group_name: str | None = None, sort_by: str = DEFAULT_SORT) -> None:
    page_size = DEFAULT_PAGE_SIZE
    if confirm('Change page size? (y/n): '):
        page_size = ask_int('Page size: ', minimum=1, maximum=100)

    offset = 0
    while True:
        total = get_total_contacts(group_name)
        rows = list_contacts_page(page_size, offset, sort_by, group_name)

        print()
        print(f'Page {offset // page_size + 1} | Total contacts: {total}')
        print_contacts(rows)

        command = input('[n]ext / [p]rev / [q]uit: ').strip().lower()
        if command == 'n':
            if offset + page_size < total:
                offset += page_size
            else:
                print('Already at last page.')
        elif command == 'p':
            if offset - page_size >= 0:
                offset -= page_size
            else:
                print('Already at first page.')
        elif command == 'q':
            break


def add_contact() -> None:
    name = ask('Name: ')
    email = ask_optional('Email: ')
    birthday = ask_date('Birthday (YYYY-MM-DD, optional): ')
    group_name = ask_optional('Group (Family / Work / Friend / Other, optional): ')

    phones: list[tuple[str, str]] = []
    while True:
        phone = ask_optional('Phone (leave empty to finish): ')
        if not phone:
            break
        phone_type = normalize_phone_type(ask('Type (home/work/mobile): '))
        while phone_type is None:
            print('Invalid phone type.')
            phone_type = normalize_phone_type(ask('Type (home/work/mobile): '))
        phones.append((phone.strip(), phone_type))

    with connect.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO contacts (name, email, birthday, group_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                ''',
                (name, email or None, birthday, ensure_group(cur, group_name)),
            )
            contact_id = int(cur.fetchone()[0])

            for phone, phone_type in phones:
                cur.execute(
                    '''
                    INSERT INTO phones (contact_id, phone, type)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (contact_id, phone, type) DO NOTHING
                    ''',
                    (contact_id, phone, phone_type),
                )
    print('Contact added.')


def update_contact() -> None:
    name = ask('Contact name to update: ')
    with connect.get_connection() as conn:
        with conn.cursor() as cur:
            contact_id = get_contact_id_by_name(cur, name)
            if contact_id is None:
                print('Contact not found.')
                return

            email = ask_optional('New email (leave empty to keep): ')
            birthday_raw = input('New birthday YYYY-MM-DD (leave empty to keep): ').strip()
            birthday = datetime.strptime(birthday_raw, '%Y-%m-%d').date() if birthday_raw else None
            group_name = ask_optional('New group (leave empty to keep): ')

            cur.execute('SELECT email, birthday, group_id FROM contacts WHERE id = %s', (contact_id,))
            current_email, current_birthday, current_group_id = cur.fetchone()
            if email is None:
                email = current_email
            if birthday is None:
                birthday = current_birthday
            group_id = ensure_group(cur, group_name) if group_name is not None else current_group_id

            cur.execute(
                '''
                UPDATE contacts
                SET email = %s,
                    birthday = %s,
                    group_id = %s,
                    updated_at = NOW()
                WHERE id = %s
                ''',
                (email, birthday, group_id, contact_id),
            )

            if confirm('Replace all phones? (y/n): '):
                cur.execute('DELETE FROM phones WHERE contact_id = %s', (contact_id,))
                while True:
                    phone = ask_optional('Phone (leave empty to finish): ')
                    if not phone:
                        break
                    phone_type = normalize_phone_type(ask('Type (home/work/mobile): '))
                    while phone_type is None:
                        print('Invalid phone type.')
                        phone_type = normalize_phone_type(ask('Type (home/work/mobile): '))
                    cur.execute(
                        '''
                        INSERT INTO phones (contact_id, phone, type)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (contact_id, phone, type) DO NOTHING
                        ''',
                        (contact_id, phone.strip(), phone_type),
                    )
    print('Contact updated.')


def delete_contact() -> None:
    name = ask('Contact name to delete: ')
    with connect.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM contacts WHERE name = %s', (name,))
            if cur.rowcount == 0:
                print('Contact not found.')
            else:
                print('Contact deleted.')


def add_phone_via_procedure() -> None:
    name = ask('Contact name: ')
    phone = ask('New phone: ')
    phone_type = normalize_phone_type(ask('Type (home/work/mobile): '))
    while phone_type is None:
        print('Invalid phone type.')
        phone_type = normalize_phone_type(ask('Type (home/work/mobile): '))
    with connect.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('CALL add_phone(%s, %s, %s)', (name, phone, phone_type))
    print('Phone added.')


def move_contact_to_group() -> None:
    name = ask('Contact name: ')
    group_name = ask('Group name: ')
    with connect.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('CALL move_to_group(%s, %s)', (name, group_name))
    print('Contact moved to group.')


def search_menu() -> None:
    query = ask('Search query (name / email / phone / group): ')
    print_contacts(search_contacts(query))


def filter_by_group_menu() -> None:
    group_name = ask('Group name: ')
    print_contacts(list_contacts(group_name=group_name, sort_by='name'))


def sort_menu() -> None:
    sort_by = ask('Sort by (name / birthday / date_added): ').lower()
    if sort_by not in {'name', 'birthday', 'date_added'}:
        sort_by = 'name'
    print_contacts(list_contacts(sort_by=sort_by))


def paginated_menu() -> None:
    group_name = ask_optional('Filter by group (leave empty for all): ')
    sort_by = ask('Sort by (name / birthday / date_added): ').lower()
    if sort_by not in {'name', 'birthday', 'date_added'}:
        sort_by = 'name'
    show_paginated_contacts(group_name=group_name, sort_by=sort_by)


def export_to_json() -> None:
    path = ask_optional(f'Export file [{JSON_DEFAULT_EXPORT}]: ') or JSON_DEFAULT_EXPORT
    rows = list_contacts(sort_by='name')
    data: list[dict[str, Any]] = []

    with connect.get_connection() as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute('SELECT phone, type FROM phones WHERE contact_id = %s ORDER BY type, phone', (row['contact_id'],))
                phones = [{'phone': phone, 'type': ptype} for phone, ptype in cur.fetchall()]
                data.append(
                    {
                        'name': row['name'],
                        'email': row['email'],
                        'birthday': row['birthday'].isoformat() if row['birthday'] else None,
                        'group': row['group_name'],
                        'phones': phones,
                        'created_at': row['created_at'].isoformat(sep=' ', timespec='seconds') if row.get('created_at') else None,
                    }
                )

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f'Exported {len(data)} contacts to {path}')


def insert_or_update_contact_from_record(cur, record: dict[str, Any], overwrite: bool) -> None:
    name = record.get('name')
    email = record.get('email')
    birthday_raw = record.get('birthday')
    group_name = record.get('group')
    phones = record.get('phones') or []

    birthday = None
    if birthday_raw:
        birthday = datetime.strptime(str(birthday_raw)[:10], '%Y-%m-%d').date()

    cur.execute('SELECT id FROM contacts WHERE name = %s', (name,))
    existing = cur.fetchone()
    if existing:
        if not overwrite:
            return
        contact_id = int(existing[0])
        cur.execute('SELECT group_id FROM contacts WHERE id = %s', (contact_id,))
        current_group_id = cur.fetchone()[0]
        cur.execute(
            '''
            UPDATE contacts
            SET email = %s,
                birthday = %s,
                group_id = %s,
                updated_at = NOW()
            WHERE id = %s
            ''',
            (email or None, birthday, ensure_group(cur, group_name) if group_name is not None else current_group_id, contact_id),
        )
        cur.execute('DELETE FROM phones WHERE contact_id = %s', (contact_id,))
    else:
        cur.execute(
            '''
            INSERT INTO contacts (name, email, birthday, group_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            ''',
            (name, email or None, birthday, ensure_group(cur, group_name)),
        )
        contact_id = int(cur.fetchone()[0])

    for phone_item in phones:
        phone = (phone_item.get('phone') or '').strip()
        phone_type = normalize_phone_type(phone_item.get('type')) or 'mobile'
        if not phone:
            continue
        cur.execute(
            '''
            INSERT INTO phones (contact_id, phone, type)
            VALUES (%s, %s, %s)
            ON CONFLICT (contact_id, phone, type) DO NOTHING
            ''',
            (contact_id, phone, phone_type),
        )


def import_from_json() -> None:
    path = ask_optional(f'Import file [{JSON_DEFAULT_IMPORT}]: ') or JSON_DEFAULT_IMPORT
    file_path = Path(path)
    if not file_path.exists():
        print('File does not exist.')
        return

    with file_path.open('r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        print('Invalid JSON format. Expected a list.')
        return

    imported = 0
    skipped = 0

    with connect.get_connection() as conn:
        with conn.cursor() as cur:
            for record in data:
                if not isinstance(record, dict) or 'name' not in record:
                    continue
                cur.execute('SELECT 1 FROM contacts WHERE name = %s', (record['name'],))
                exists = cur.fetchone() is not None
                if exists:
                    choice = input(f"Contact '{record['name']}' exists. Skip or overwrite? [s/o]: ").strip().lower()
                    if choice.startswith('s'):
                        skipped += 1
                        continue
                insert_or_update_contact_from_record(cur, record, overwrite=True)
                imported += 1

    print(f'Imported: {imported}, skipped: {skipped}')


def import_from_csv() -> None:
    path = ask_optional(f'CSV file [{CSV_DEFAULT_PATH}]: ') or CSV_DEFAULT_PATH
    file_path = Path(path)
    if not file_path.exists():
        print('File does not exist.')
        return

    with file_path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print('CSV is empty.')
        return

    created = 0
    updated = 0

    with connect.get_connection() as conn:
        with conn.cursor() as cur:
            for row in rows:
                name = (row.get('name') or row.get('Name') or '').strip()
                if not name:
                    continue

                email = (row.get('email') or row.get('Email') or '').strip() or None
                birthday_raw = (row.get('birthday') or row.get('Birthday') or '').strip()
                group_name = (row.get('group') or row.get('Group') or row.get('group_name') or '').strip() or None
                phone = (row.get('phone') or row.get('Phone') or '').strip()
                phone_type = normalize_phone_type((row.get('phone_type') or row.get('PhoneType') or row.get('type') or '').strip()) or 'mobile'

                birthday = None
                if birthday_raw:
                    for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'):
                        try:
                            birthday = datetime.strptime(birthday_raw, fmt).date()
                            break
                        except ValueError:
                            continue

                cur.execute('SELECT id FROM contacts WHERE name = %s', (name,))
                existing = cur.fetchone()
                if existing:
                    contact_id = int(existing[0])
                    cur.execute(
                        '''
                        UPDATE contacts
                        SET email = COALESCE(%s, email),
                            birthday = COALESCE(%s, birthday),
                            group_id = COALESCE(%s, group_id),
                            updated_at = NOW()
                        WHERE id = %s
                        ''',
                        (email, birthday, ensure_group(cur, group_name), contact_id),
                    )
                    updated += 1
                else:
                    cur.execute(
                        '''
                        INSERT INTO contacts (name, email, birthday, group_id)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                        ''',
                        (name, email, birthday, ensure_group(cur, group_name)),
                    )
                    contact_id = int(cur.fetchone()[0])
                    created += 1

                if phone:
                    cur.execute(
                        '''
                        INSERT INTO phones (contact_id, phone, type)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (contact_id, phone, type) DO NOTHING
                        ''',
                        (contact_id, phone, phone_type),
                    )

    print(f'CSV import completed. Created: {created}, updated: {updated}')


def show_help():
    print()
    print('1) Add contact')
    print('2) Update contact')
    print('3) Delete contact')
    print('4) Add phone (procedure)')
    print('5) Move contact to group (procedure)')
    print('6) Search contacts')
    print('7) Filter by group')
    print('8) Sort contacts')
    print('9) Paginated browse')
    print('10) Export to JSON')
    print('11) Import from JSON')
    print('12) Import from CSV')
    print('0) Exit')
    print()


def main() -> None:
    connect.initialize_database()

    while True:
        show_help()
        choice = ask('Choose: ')

        if choice == '1':
            add_contact()
        elif choice == '2':
            update_contact()
        elif choice == '3':
            delete_contact()
        elif choice == '4':
            add_phone_via_procedure()
        elif choice == '5':
            move_contact_to_group()
        elif choice == '6':
            search_menu()
        elif choice == '7':
            filter_by_group_menu()
        elif choice == '8':
            sort_menu()
        elif choice == '9':
            paginated_menu()
        elif choice == '10':
            export_to_json()
        elif choice == '11':
            import_from_json()
        elif choice == '12':
            import_from_csv()
        elif choice == '0':
            break
        else:
            print('Invalid choice.')


if __name__ == '__main__':
    main()
