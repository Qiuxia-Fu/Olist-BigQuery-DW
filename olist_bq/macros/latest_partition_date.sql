{% macro latest_partition_date(relation) %}
    {% if execute %}
        {% set query %}
            select max(partition_id)
            from `{{ relation.database }}.{{ relation.schema }}.INFORMATION_SCHEMA.PARTITIONS`
            where table_name = '{{ relation.identifier }}'
              and partition_id not in ('__NULL__', '__UNPARTITIONED__')
        {% endset %}
        {% set partition_id = run_query(query).columns[0].values()[0] %}
        {{ return("DATE '" ~ partition_id[0:4] ~ "-" ~ partition_id[4:6] ~ "-" ~ partition_id[6:8] ~ "'") }}
    {% else %}
        {{ return("CURRENT_DATE()") }}
    {% endif %}
{% endmacro %}