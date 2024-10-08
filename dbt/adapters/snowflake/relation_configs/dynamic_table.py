from dataclasses import dataclass
from typing import Optional, Dict, Any, TYPE_CHECKING

from dbt.adapters.relation_configs import RelationConfigChange, RelationResults
from dbt.adapters.contracts.relation import RelationConfig
from dbt.adapters.contracts.relation import ComponentName
from dbt_common.dataclass_schema import StrEnum  # doesn't exist in standard library until py3.11
from typing_extensions import Self

from dbt.adapters.snowflake.relation_configs.base import SnowflakeRelationConfigBase

if TYPE_CHECKING:
    import agate


class RefreshMode(StrEnum):
    AUTO = "AUTO"
    FULL = "FULL"
    INCREMENTAL = "INCREMENTAL"

    @classmethod
    def default(cls) -> Self:
        return cls("AUTO")


class Initialize(StrEnum):
    ON_CREATE = "ON_CREATE"
    ON_SCHEDULE = "ON_SCHEDULE"

    @classmethod
    def default(cls) -> Self:
        return cls("ON_CREATE")


@dataclass(frozen=True, eq=True, unsafe_hash=True)
class SnowflakeDynamicTableConfig(SnowflakeRelationConfigBase):
    """
    This config follow the specs found here:
    https://docs.snowflake.com/en/sql-reference/sql/create-dynamic-table

    The following parameters are configurable by dbt:
    - name: name of the dynamic table
    - query: the query behind the table
    - target_lag: the maximum amount of time that the dynamic table’s content should lag behind updates to the base tables
    - snowflake_warehouse: the name of the warehouse that provides the compute resources for refreshing the dynamic table
    - refresh_mode: specifies the refresh type for the dynamic table
    - initialize: specifies the behavior of the initial refresh of the dynamic table

    There are currently no non-configurable parameters.
    """

    name: str
    schema_name: str
    database_name: str
    query: str
    target_lag: str
    snowflake_warehouse: str
    refresh_mode: Optional[RefreshMode] = RefreshMode.default()
    initialize: Optional[Initialize] = Initialize.default()
    transient: Optional[bool] = None
    time_travel: Optional[int] = None
    cluster_by: Optional[str] = None

    @classmethod
    def from_dict(cls, config_dict) -> "SnowflakeDynamicTableConfig":
        kwargs_dict = {
            "name": cls._render_part(ComponentName.Identifier, config_dict.get("name")),
            "schema_name": cls._render_part(ComponentName.Schema, config_dict.get("schema_name")),
            "database_name": cls._render_part(
                ComponentName.Database, config_dict.get("database_name")
            ),
            "query": config_dict.get("query"),
            "target_lag": config_dict.get("target_lag"),
            "snowflake_warehouse": config_dict.get("snowflake_warehouse"),
            "refresh_mode": config_dict.get("refresh_mode"),
            "initialize": config_dict.get("initialize"),
            "transient": config_dict.get("transient"),
            "time_travel": config_dict.get("time_travel"),
            "cluster_by": config_dict.get("cluster_by"),
        }

        dynamic_table: "SnowflakeDynamicTableConfig" = super().from_dict(kwargs_dict)
        return dynamic_table

    @classmethod
    def parse_relation_config(cls, relation_config: RelationConfig) -> Dict[str, Any]:
        config_dict = {
            "name": relation_config.identifier,
            "schema_name": relation_config.schema,
            "database_name": relation_config.database,
            "query": relation_config.compiled_code,
            "target_lag": relation_config.config.extra.get("target_lag"),
            "snowflake_warehouse": relation_config.config.extra.get("snowflake_warehouse"),
            "time_travel": relation_config.config.extra.get("time_travel"),
            "transient": relation_config.config.extra.get("transient"),
            "cluster_by": relation_config.config.extra.get("cluster_by"),
        }

        if refresh_mode := relation_config.config.extra.get("refresh_mode"):
            config_dict.update(refresh_mode=refresh_mode.upper())

        if initialize := relation_config.config.extra.get("initialize"):
            config_dict.update(initialize=initialize.upper())

        if target_lag := relation_config.config.extra.get("target_lag"):
            if target_lag == "downstream":
                config_dict.update(target_lag=target_lag.upper())

        return config_dict

    @classmethod
    def parse_relation_results(cls, relation_results: RelationResults) -> Dict:
        dynamic_table: "agate.Row" = relation_results["dynamic_table"].rows[0]

        config_dict = {
            "name": dynamic_table.get("name"),
            "schema_name": dynamic_table.get("schema_name"),
            "database_name": dynamic_table.get("database_name"),
            "query": dynamic_table.get("text"),
            "target_lag": dynamic_table.get("target_lag"),
            "snowflake_warehouse": dynamic_table.get("warehouse"),
            "refresh_mode": dynamic_table.get("refresh_mode"),
            # we don't get initialize since that's a one-time scheduler attribute, not a DT attribute
            "transient": dynamic_table.get("transient"),
            "time_travel": dynamic_table.get("time_travel"),
            "cluster_by": dynamic_table.get("cluster_by"), # Get inner values from "LINEAR()"
        }

        return config_dict


@dataclass(frozen=True, eq=True, unsafe_hash=True)
class SnowflakeDynamicTableTargetLagConfigChange(RelationConfigChange):
    context: Optional[str] = None

    @property
    def requires_full_refresh(self) -> bool:
        return False


@dataclass(frozen=True, eq=True, unsafe_hash=True)
class SnowflakeDynamicTableWarehouseConfigChange(RelationConfigChange):
    context: Optional[str] = None

    @property
    def requires_full_refresh(self) -> bool:
        return False


@dataclass(frozen=True, eq=True, unsafe_hash=True)
class SnowflakeDynamicTableRefreshModeConfigChange(RelationConfigChange):
    context: Optional[str] = None

    @property
    def requires_full_refresh(self) -> bool:
        return True


@dataclass(frozen=True, eq=True, unsafe_hash=True)
class SnowflakeDynamicTableTransientConfigChange(RelationConfigChange):
    context: Optional[str] = None

    @property
    def requires_full_refresh(self) -> bool:
        return True


@dataclass(frozen=True, eq=True, unsafe_hash=True)
class SnowflakeDynamicTableQueryConfigChange(RelationConfigChange):
    context: Optional[str] = None

    @property
    def requires_full_refresh(self) -> bool:
        return True


@dataclass(frozen=True, eq=True, unsafe_hash=True)
class SnowflakeDynamicTableTimeTravelConfigChange(RelationConfigChange):
    context: Optional[str] = None

    @property
    def requires_full_refresh(self) -> bool:
        return True
    

@dataclass(frozen=True, eq=True, unsafe_hash=True)
class SnowflakeDynamicTableClusterByConfigChange(RelationConfigChange):
    context: Optional[str] = None

    @property
    def requires_full_refresh(self) -> bool:
        return True


@dataclass
class SnowflakeDynamicTableConfigChangeset:
    target_lag: Optional[SnowflakeDynamicTableTargetLagConfigChange] = None
    snowflake_warehouse: Optional[SnowflakeDynamicTableWarehouseConfigChange] = None
    refresh_mode: Optional[SnowflakeDynamicTableRefreshModeConfigChange] = None
    transient: Optional[SnowflakeDynamicTableTransientConfigChange] = None
    query: Optional[SnowflakeDynamicTableQueryConfigChange] = None
    time_travel: Optional[SnowflakeDynamicTableTimeTravelConfigChange] = None
    cluster_by: Optional[SnowflakeDynamicTableClusterByConfigChange] = None

    @property
    def requires_full_refresh(self) -> bool:
        return any(
            [
                self.target_lag.requires_full_refresh if self.target_lag else False,
                self.snowflake_warehouse.requires_full_refresh if self.snowflake_warehouse else False,
                self.refresh_mode.requires_full_refresh if self.refresh_mode else False,
                self.transient.requires_full_refresh if self.transient else False,
                self.query.requires_full_refresh if self.query else False,
                self.time_travel.requires_full_refresh if self.time_travel else False,
                self.cluster_by.requires_full_refresh if self.cluster_by else False, 
            ]
        )

    @property
    def has_changes(self) -> bool:
        return any([self.target_lag, self.snowflake_warehouse, self.refresh_mode, self.transient, self.query, self.time_travel, self.cluster_by])
