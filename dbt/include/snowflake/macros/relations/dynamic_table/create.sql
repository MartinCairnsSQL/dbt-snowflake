{% macro snowflake__get_create_dynamic_table_as_sql(relation, sql) -%}

    {%- set dynamic_table = relation.from_config(config.model) -%}
    create {{ 'transient' if dynamic_table.transient }} dynamic table {{ relation }}
        target_lag = '{{ dynamic_table.target_lag }}'
        warehouse = {{ dynamic_table.snowflake_warehouse }}
        {% if dynamic_table.refresh_mode %}
        refresh_mode = {{ dynamic_table.refresh_mode }}
        {% endif %}
        {% if dynamic_table.initialize %}
        initialize = {{ dynamic_table.initialize }}
        {% endif %}
        {% if dynamic_table.cluster_by is not none -%}
        cluster by ({{ dynamic_table.cluster_by | join(",") }})
        {%- endif -%}
        {% if dynamic_table.time_travel is not none %}
        data_retention_time_in_days = {{ dynamic_table.time_travel }}
        {% endif %}
        as (
            {{ sql }}
        )

{%- endmacro %}
