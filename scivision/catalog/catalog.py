#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pkgutil
import pandas as pd
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, FrozenSet, Optional, Tuple, Union
from pydantic import AnyUrl, BaseModel, Field, validator
from enum import Enum
from collections import Counter


class TaskEnum(str, Enum):
    classificiation = "classification"
    object_detection = "object-detection"
    segmentation = "segmentation"
    thresholding = "thresholding"
    other = "other"


class FlexibleUrl(AnyUrl):
    host_required = False


class CatalogModelEntry(BaseModel, extra="forbid", title="A model catalog entry"):
    # tasks, institution and tags are Tuples (rather than Lists) so
    # that they are immutable - Tuple is being used as an immutable
    # sequence here. This means that these fields are hashable, which
    # can be more convenient when included in a dataframe
    # (e.g. unique()). Could consider using a Frozenset for these
    # fields instead, since duplicates and ordering should not be
    # significant.
    name: str = Field(
        ...,
        title="Name",
        description="Short, unique name for the model (one or two words, "
        "under 20 characters recommended)",
    )
    description: Optional[str] = Field(
        None,
        title="Description",
        description="Detailed description of the model",
    )
    tasks: Tuple[TaskEnum, ...] = Field(
        (),
        title="Tasks",
        description="Which task (or tasks) does the model perform?",
    )
    url: FlexibleUrl = Field(
        ...,
        title="URL",
        description="The URL of the model. This should point to scivision "
        "model yaml file.",
    )
    pkg_url: str = Field(
        ...,
        title="Python package",
        description="A pip requirement specifier for PyPI, or a URL of the "
        "archive or package (on GitHub, for exampe)",
    )
    format: str = Field(
        ...,
        title="Model input format",
        description="The type of data consumed by the model",
    )
    pretrained: bool = Field(
        True,
        title="Pretrained model?",
    )
    labels_required: bool = Field(
        True,
        title="Labels required?",
        description="Does the model require labeled data for training?",
    )
    institution: Tuple[str, ...] = Field(
        (),
        title="Institution(s)",
        description="A list of institutions that produced or are associated with "
        "the model (one per item)",
    )
    tags: Tuple[str, ...]

    def __getitem__(self, item):
        return getattr(self, item)


class CatalogModels(BaseModel, extra="forbid"):
    catalog_type: str = "scivision model catalog"
    name: str
    # Tuple: see comment on CatalogModelEntry
    entries: Tuple[CatalogModelEntry, ...]

    @validator("entries")
    def name_unique_key(cls, entries):
        name_counts = Counter([entry['name'] for entry in entries])
        dups = [item for item, count in name_counts.items() if count > 1]

        if dups:
            raise ValueError(f"The 'name' field in the model catalog should be unique (duplicates: {dups})")

        return entries


class CatalogDatasourceEntry(
    BaseModel, extra="forbid", title="Datasource catalog entry"
):
    name: str = Field(
        ...,
        title="Name",
        description="Short name for the datasource, that must be unique among "
        "all catalog entries (one or two words, under 20 characters recommended)",
    )
    description: Optional[str] = Field(
        None,
        title="Description",
        description="Detailed description of the dataset (no length limit)",
    )
    tasks: FrozenSet[TaskEnum] = Field(
        None,
        title="Suitable tasks",
        description="For which task or tasks is this datasource likely to be "
        "suitable? (Select any number of the following items)",
    )
    labels_provided: bool = Field(
        False,
        title="Labels provided",
        description="Is this a labelled dataset? This can make it suitable for training or validation",
    )
    domains: Tuple[str, ...] = Field(
        None,
        title="Domain areas",
        description="Which domain area or areas is this datasource from? (One per item, no duplicates)",
        # Note: using uniqueItems (used for the json schema) rather
        # than unique_items (which is not possible to enforce on a
        # Tuple).  Could use a set/frozenset instead, or a tuple
        # variant with a constraint.
        uniqueItems=True,
    )
    url: FlexibleUrl = Field(
        None,
        title="URL",
        description="The URL of the scivision datasource yml file",
    )
    format: str = Field(
        None,
        title="Format",
    )
    institution: Tuple[str, ...] = Field(
        (),
        title="Institution(s)",
        description="A list of institutions that produced or are associated with "
        "the dataset (one per item)",
    )
    tags: Tuple[str, ...] = Field(
        (),
        title="Tags",
        description="A list of free-form data to associate with the dataset",
    )

    def __getitem__(self, item):
        return getattr(self, item)


class CatalogDatasources(BaseModel, extra="forbid"):
    catalog_type: str = "scivision datasource catalog"
    name: str
    # Tuple: see comment on CatalogModelEntry
    entries: Tuple[CatalogDatasourceEntry, ...]

    @validator("entries")
    def name_unique_key(cls, entries):
        name_counts = Counter([entry['name'] for entry in entries])
        dups = [item for item, count in name_counts.items() if count > 1]

        if dups:
            raise ValueError(f"The 'name' field in the datasource catalog should be unique (duplicates: {dups})")

        return entries


def _coerce_datasources_catalog(
    datasources: Union[CatalogDatasources, os.PathLike, None]
) -> CatalogDatasources:
    """Returns a CatalogDatasources determined from the argument: either
    the one passed, or one loaded from a file
    """
    if isinstance(datasources, CatalogDatasources):
        return datasources
    elif isinstance(datasources, (bytes, str, os.PathLike)):
        datasources_raw = Path(datasources).read_text()
        return CatalogDatasources.parse_raw(datasources_raw)
    elif datasources is None:
        datasources_raw = pkgutil.get_data(__name__, "data/datasources.json")
        return CatalogDatasources.parse_raw(datasources_raw)
    else:
        raise TypeError("Cannot load datasource from unsupported type")


def _coerce_models_catalog(
    models: Union[CatalogModels, os.PathLike, None]
) -> CatalogModels:
    """Returns a CatalogModels determined from the argument: either the
    one passed, or one loaded from a file
    """
    if isinstance(models, CatalogModels):
        return models
    elif isinstance(models, (bytes, str, os.PathLike)):
        models_raw = Path(models).read_text()
        return CatalogModels.parse_raw(models_raw)
    elif models is None:
        models_raw = pkgutil.get_data(__name__, "data/models.json")
        return CatalogModels.parse_raw(models_raw)
    else:
        raise TypeError("Cannot load datasource from unsupported type")


class QueryResult(ABC):
    @abstractmethod
    def to_dataframe(self) -> pd.DataFrame:
        ...

    def to_dict(self) -> Dict[str, Any]:
        return self.to_dataframe().to_dict(orient="records")


class PandasQueryResult(QueryResult):
    def __init__(self, result: pd.DataFrame):
        self._result = result

    def to_dataframe(self) -> pd.DataFrame:
        return self._result


class PandasCatalog:
    def __init__(self, datasources=None, models=None):
        super().__init__()

        if isinstance(datasources, pd.DataFrame):
            self._datasources = datasources
        else:
            datasources_cat = _coerce_datasources_catalog(datasources)
            self._datasources = pd.DataFrame(
                [ent.dict() for ent in datasources_cat.entries]
            )

        if isinstance(models, pd.DataFrame):
            self._models = models
        else:
            models_cat = _coerce_models_catalog(models)
            self._models = pd.DataFrame([ent.dict() for ent in models_cat.entries])

    @property
    def models(self) -> PandasQueryResult:
        return PandasQueryResult(self._models)

    @property
    def datasources(self) -> PandasQueryResult:
        return PandasQueryResult(self._datasources)

    def _compatible_models(self, datasource) -> PandasQueryResult:
        models_compatible_format = self._models[
            self._models.format == datasource["format"]
        ]

        models_compatible_format_labels = models_compatible_format[
            datasource["labels_provided"] | ~models_compatible_format.labels_required
        ]

        datasource_tasks = pd.DataFrame(datasource["tasks"], columns=["tasks"])
        models_compatible_tasks = (
            self._models[["name", "tasks"]]
            .explode("tasks")
            .merge(
                datasource_tasks,
                on="tasks",
                suffixes=("_model", "_datasource"),
            )
            .name.drop_duplicates()
        )
        result_df = models_compatible_format_labels[
            models_compatible_format_labels.name.isin(models_compatible_tasks)
        ]

        return PandasQueryResult(result_df)

    # Similar to _compatible_models, but for datasources.  Can't
    # cleanly combine these two functions, due to the asymmetry
    # between a model's 'labels_required', and datasource 'labels_provided'.
    # In particular, a model that doesn't require labels can still use
    # a datasource that provides them (if they are otherwise
    # compatible), but not vice versa.  For this reason, the distinct
    # names 'labels_provided' and 'labels_required' are used.
    def _compatible_datasources(self, model) -> PandasQueryResult:
        datasources_compatible_format = self._datasources[
            self._datasources.format == model["format"]
        ]

        datasources_compatible_format_labels = datasources_compatible_format[
            datasources_compatible_format.labels_provided | ~model["labels_required"]
        ]

        model_tasks = pd.DataFrame(model["tasks"], columns=["tasks"])
        datasources_compatible_tasks = (
            self._datasources[["name", "tasks"]]
            .explode("tasks")
            .merge(
                model_tasks,
                on="tasks",
                suffixes=("_model", "_datasource"),
            )
            .name.drop_duplicates()
        )
        result_df = datasources_compatible_format_labels[
            datasources_compatible_format_labels.name.isin(datasources_compatible_tasks)
        ]

        return PandasQueryResult(result_df)

    def compatible_models(self, datasource) -> PandasQueryResult:
        """Return all models that are compatible with datasource

        Parameters
        ----------
        datasource : str or dict-like
            Any dictionary-like (including CatalogDatasourceEntry) that
            has keys 'format', 'tasks' and 'labels_provided', representing
            these properties of the datasource.
            If a string is passed, this is used to look up the datasource
            (in `self._datasources`).

        Returns
        -------
        result: QueryResult
            A QueryResult instance containing the models compatible with the
            given datasource (convertible to a dict or pd.DataFrame).

        """
        if isinstance(datasource, str):
            return self._compatible_models(
                self._datasources.set_index("name").loc[datasource]
            )
        else:
            return self._compatible_models(datasource)

    def compatible_datasources(self, model) -> PandasQueryResult:
        """Return all datasources that are compatible with model

        Parameters
        ----------
        model : str or dict-like
            Any dictionary-like (including CatalogModelEntry) that has
            keys 'format', 'tasks' and 'labels_required', representing
            these properties of the model.
            If a string is passed, this is used to look up the model (in `self._models`).

        Returns
        -------
        result: QueryResult
            A QueryResult instance containing the datasources compatible with
            the given model (convertible to a dict or pd.DataFrame).

        """
        if isinstance(model, str):
            return self._compatible_datasources(
                self._models.set_index("name").loc[model]
            )
        else:
            return self._compatible_datasources(model)


default_catalog = PandasCatalog()
