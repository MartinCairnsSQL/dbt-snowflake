{% macro snowflake__describe_dynamic_table(relation) %}
    {%- set _dynamic_table_sql -%}
        show dynamic tables
            like '{{ relation.identifier }}'
            in schema {{ relation.database }}.{{ relation.schema }}
        ;

        select
            rs."name",
            rs."schema_name",
            rs."database_name",
            rs."text",
            rs."target_lag",
            rs."warehouse",
            rs."refresh_mode",
            TO_BOOLEAN(t.is_transient) as "transient",
            t.retention_time as "time_travel",
            SPLIT(REGEXP_EXTRACT_ALL(t.clustering_key, $$(\w+)?\((.*)\)$$, 1, 1, 'e', 2)[0],',') as "cluster_by"
        from table(result_scan(last_query_id())) rs
        inner join {{ relation.database }}.information_schema.tables t
        ON rs."schema_name" = t.table_schema
        and rs."name" = t.table_name

    {%- endset %}
    {% set _dynamic_table = run_query(_dynamic_table_sql) %}

    {% do return({"dynamic_table": _dynamic_table}) %}
{% endmacro %}
