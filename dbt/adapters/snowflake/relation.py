from dataclasses import dataclass, field
from typing import FrozenSet, Optional, Type

from dbt.adapters.base.relation import BaseRelation
from dbt.adapters.contracts.relation import ComponentName, RelationConfig
from dbt.adapters.relation_configs import (
    RelationConfigBase,
    RelationConfigChangeAction,
    RelationResults,
)
from dbt.adapters.utils import classproperty
from dbt_common.exceptions import DbtRuntimeError

from dbt.adapters.snowflake.relation_configs import (
    SnowflakeDynamicTableConfig,
    SnowflakeDynamicTableConfigChangeset,
    SnowflakeDynamicTableRefreshModeConfigChange,
    SnowflakeDynamicTableTargetLagConfigChange,
    SnowflakeDynamicTableWarehouseConfigChange,
    SnowflakeDynamicTableTransientConfigChange,
    SnowflakeDynamicTableQueryConfigChange,    
    SnowflakeQuotePolicy,
    SnowflakeRelationType,
)


@dataclass(frozen=True, eq=False, repr=False)
class SnowflakeRelation(BaseRelation):
    type: Optional[SnowflakeRelationType] = None
    quote_policy: SnowflakeQuotePolicy = field(default_factory=lambda: SnowflakeQuotePolicy())
    require_alias: bool = False
    relation_configs = {
        SnowflakeRelationType.DynamicTable: SnowflakeDynamicTableConfig,
    }
    renameable_relations: FrozenSet[SnowflakeRelationType] = field(
        default_factory=lambda: frozenset(
            {
                SnowflakeRelationType.Table,  # type: ignore
                SnowflakeRelationType.View,  # type: ignore
            }
        )
    )

    replaceable_relations: FrozenSet[SnowflakeRelationType] = field(
        default_factory=lambda: frozenset(
            {
                SnowflakeRelationType.DynamicTable,  # type: ignore
                SnowflakeRelationType.Table,  # type: ignore
                SnowflakeRelationType.View,  # type: ignore
            }
        )
    )

    @property
    def is_dynamic_table(self) -> bool:
        return self.type == SnowflakeRelationType.DynamicTable

    @classproperty
    def DynamicTable(cls) -> str:
        return str(SnowflakeRelationType.DynamicTable)

    @classproperty
    def get_relation_type(cls) -> Type[SnowflakeRelationType]:
        return SnowflakeRelationType

    @classmethod
    def from_config(cls, config: RelationConfig) -> RelationConfigBase:
        relation_type: str = config.config.materialized

        if relation_config := cls.relation_configs.get(relation_type):
            return relation_config.from_relation_config(config)

        raise DbtRuntimeError(
            f"from_config() is not supported for the provided relation type: {relation_type}"
        )

    @classmethod
    def dynamic_table_config_changeset(
        cls, relation_results: RelationResults, relation_config: RelationConfig
    ) -> Optional[SnowflakeDynamicTableConfigChangeset]:
        existing_dynamic_table = SnowflakeDynamicTableConfig.from_relation_results(
            relation_results
        )
        new_dynamic_table = SnowflakeDynamicTableConfig.from_relation_config(relation_config)

        config_change_collection = SnowflakeDynamicTableConfigChangeset()

        if new_dynamic_table.target_lag != existing_dynamic_table.target_lag:
            config_change_collection.target_lag = SnowflakeDynamicTableTargetLagConfigChange(
                action=RelationConfigChangeAction.alter,
                context=new_dynamic_table.target_lag,
            )

        if new_dynamic_table.snowflake_warehouse != existing_dynamic_table.snowflake_warehouse:
            config_change_collection.snowflake_warehouse = (
                SnowflakeDynamicTableWarehouseConfigChange(
                    action=RelationConfigChangeAction.alter,
                    context=new_dynamic_table.snowflake_warehouse,
                )
            )

        if new_dynamic_table.refresh_mode != existing_dynamic_table.refresh_mode and new_dynamic_table.refresh_mode != 'AUTO':
            config_change_collection.refresh_mode = SnowflakeDynamicTableRefreshModeConfigChange(
                action=RelationConfigChangeAction.create,
                context=new_dynamic_table.refresh_mode,
            )
        
        if new_dynamic_table.transient != existing_dynamic_table.transient:
            config_change_collection.transient = SnowflakeDynamicTableTransientConfigChange(
                action=RelationConfigChangeAction.create,
                context=new_dynamic_table.transient,
            )

        if has_snowflake_query_sql_changed(new_dynamic_table.query, existing_dynamic_table.query):
            config_change_collection.query = SnowflakeDynamicTableQueryConfigChange(
                action=RelationConfigChangeAction.create,
                context=new_dynamic_table.query,
            )

        if config_change_collection.has_changes:
            return config_change_collection
        return None

    def as_case_sensitive(self) -> "SnowflakeRelation":
        path_part_map = {}

        for path in ComponentName:
            if self.include_policy.get_part(path):
                part = self.path.get_part(path)
                if part:
                    if self.quote_policy.get_part(path):
                        path_part_map[path] = part
                    else:
                        path_part_map[path] = part.upper()

        return self.replace_path(**path_part_map)

def has_snowflake_query_sql_changed(new_sql, existing_sql) -> bool:
    import re 
    from sqlfmt.api import format_string, Mode as sqlfmt_Mode

    mode = sqlfmt_Mode(line_length=88, fast=False)
    new_select = format_string(new_sql, mode)

    inner_select_re = r"\s+as\s+\(\s+(?P<sql>.*)\)"
    matches = re.search(inner_select_re, existing_sql, re.IGNORECASE | re.DOTALL)
    inner_sql = matches["sql"]

    if len(inner_sql) == 0 or not (inner_sql.startswith("select") or inner_sql.startswith("with")):
        raise Exception("Failed to find inner sql from definition ")
    
    old_select = format_string(inner_sql, mode)

    if old_select != new_select:
        print("OLD:", old_select, "NEW:", new_select)
        breakpoint()
        return True

    return False
