DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'trace_runtime') THEN
        CREATE ROLE trace_runtime NOLOGIN;
    END IF;
END
$$;
