CREATE OR REPLACE PROCEDURE add_phone(
    p_contact_name VARCHAR,
    p_phone VARCHAR,
    p_type VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_contact_id INTEGER;
    v_phone_type  VARCHAR(10);
BEGIN
    v_phone_type := lower(trim(p_type));

    IF v_phone_type NOT IN ('home', 'work', 'mobile') THEN
        RAISE EXCEPTION 'Invalid phone type: %', p_type;
    END IF;

    SELECT id
    INTO v_contact_id
    FROM contacts
    WHERE name = p_contact_name;

    IF v_contact_id IS NULL THEN
        RAISE EXCEPTION 'Contact "%" does not exist', p_contact_name;
    END IF;

    INSERT INTO phones (contact_id, phone, type)
    VALUES (v_contact_id, trim(p_phone), v_phone_type)
    ON CONFLICT DO NOTHING;
END;
$$;

CREATE OR REPLACE PROCEDURE move_to_group(
    p_contact_name VARCHAR,
    p_group_name VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_contact_id INTEGER;
    v_group_id   INTEGER;
BEGIN
    INSERT INTO groups (name)
    VALUES (trim(p_group_name))
    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
    RETURNING id INTO v_group_id;

    SELECT id
    INTO v_contact_id
    FROM contacts
    WHERE name = p_contact_name;

    IF v_contact_id IS NULL THEN
        RAISE EXCEPTION 'Contact "%" does not exist', p_contact_name;
    END IF;

    UPDATE contacts
    SET group_id = v_group_id,
        updated_at = NOW()
    WHERE id = v_contact_id;
END;
$$;

CREATE OR REPLACE FUNCTION search_contacts(p_query TEXT)
RETURNS TABLE(
    contact_id   INTEGER,
    name         VARCHAR,
    email        VARCHAR,
    birthday     DATE,
    group_name   VARCHAR,
    phones       TEXT,
    created_at   TIMESTAMP
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_query TEXT := lower(trim(coalesce(p_query, '')));
BEGIN
    RETURN QUERY
    SELECT
        c.id AS contact_id,
        c.name,
        c.email,
        c.birthday,
        g.name AS group_name,
        COALESCE(
            string_agg(DISTINCT (ph.type || ': ' || ph.phone), ', ' ORDER BY (ph.type || ': ' || ph.phone)),
            ''
        ) AS phones,
        c.created_at
    FROM contacts c
    LEFT JOIN groups g ON g.id = c.group_id
    LEFT JOIN phones ph ON ph.contact_id = c.id
    WHERE v_query = ''
       OR lower(c.name) LIKE '%' || v_query || '%'
       OR lower(coalesce(c.email, '')) LIKE '%' || v_query || '%'
       OR lower(coalesce(g.name, '')) LIKE '%' || v_query || '%'
       OR EXISTS (
            SELECT 1
            FROM phones p2
            WHERE p2.contact_id = c.id
              AND (
                    lower(p2.phone) LIKE '%' || v_query || '%'
                    OR lower(p2.type) LIKE '%' || v_query || '%'
              )
       )
    GROUP BY c.id, c.name, c.email, c.birthday, g.name, c.created_at
    ORDER BY c.name;
END;
$$;

CREATE OR REPLACE FUNCTION get_contacts_page(
    p_limit INTEGER,
    p_offset INTEGER,
    p_sort TEXT DEFAULT 'name',
    p_group_name TEXT DEFAULT NULL
)
RETURNS TABLE(
    contact_id   INTEGER,
    name         VARCHAR,
    email        VARCHAR,
    birthday     DATE,
    group_name   VARCHAR,
    phones       TEXT,
    created_at   TIMESTAMP
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_sort TEXT := lower(trim(coalesce(p_sort, 'name')));
    v_order_clause TEXT;
    v_sql TEXT;
BEGIN
    v_order_clause := CASE v_sort
        WHEN 'birthday' THEN 'c.birthday NULLS LAST, c.name'
        WHEN 'date_added' THEN 'c.created_at DESC, c.name'
        ELSE 'c.name'
    END;

    v_sql := '
        SELECT
            c.id AS contact_id,
            c.name,
            c.email,
            c.birthday,
            g.name AS group_name,
            COALESCE(
                string_agg(DISTINCT (ph.type || '' : '' || ph.phone), '', '' ORDER BY (ph.type || '' : '' || ph.phone)),
                ''''
            ) AS phones,
            c.created_at
        FROM contacts c
        LEFT JOIN groups g ON g.id = c.group_id
        LEFT JOIN phones ph ON ph.contact_id = c.id
        WHERE ($3 IS NULL OR g.name = $3)
        GROUP BY c.id, c.name, c.email, c.birthday, g.name, c.created_at
        ORDER BY ' || v_order_clause || '
        LIMIT $1 OFFSET $2';

    RETURN QUERY EXECUTE v_sql USING p_limit, p_offset, p_group_name;
END;
$$;

CREATE OR REPLACE FUNCTION get_total_contacts(p_group_name TEXT DEFAULT NULL)
RETURNS INTEGER
LANGUAGE SQL
AS $$
    SELECT COUNT(*)
    FROM contacts c
    LEFT JOIN groups g ON g.id = c.group_id
    WHERE p_group_name IS NULL OR g.name = p_group_name
$$;
