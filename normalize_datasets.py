import pathlib
from dataclasses import dataclass
from typing import List, TypedDict

import pandas as pd
from pandas.core.frame import DataFrame

from datasets5G import datasets5G


@dataclass
class Limits:
    upload_kbps: float
    download_kbps: float
    change_interval_seconds: int


class NormalizedDataset(TypedDict):
    name: str
    data: List[Limits]
    total_duration: int
    platform: str
    mobility: str
    case: str
    dataset: str


def get_normalized_datasets() -> List[NormalizedDataset]:
    normalized_datasets = []

    for filename in datasets5G:
        # Normalize dataset using pandas
        csv_data: DataFrame = pd.read_csv(filename)  # type: ignore

        filtered_data: DataFrame = csv_data[["Timestamp", "DL_bitrate", "UL_bitrate"]]
        filtered_data = filtered_data.groupby("Timestamp").mean().reset_index()

        filtered_data["Timestamp"] = pd.to_datetime(
            filtered_data["Timestamp"], format="%Y.%m.%d_%H.%M.%S"
        )
        filtered_data["Timestamp"] = (
            ((filtered_data["Timestamp"] - filtered_data["Timestamp"].shift()))
            .shift(-1)
            .fillna(pd.Timedelta(seconds=1))
            .dt.seconds
        )

        total_duration = filtered_data["Timestamp"].sum()

        filtered_data.rename(
            columns={
                "Timestamp": "change_interval_seconds",
                "DL_bitrate": "download_kbps",
                "UL_bitrate": "upload_kbps",
            },
            inplace=True,
        )

        # Normalize name removing first path
        parts = pathlib.Path(filename).parts
        normalized_name = "-".join(parts[1:]).strip(".csv")
        platform = parts[1]
        mobility = parts[2]
        case = parts[3] if len(parts) > 4 else parts[1]
        dataset = parts[4] if len(parts) > 4 else parts[3]

        normalized_datasets.append(
            {
                "name": normalized_name,
                "data": filtered_data.to_dict("records"),
                "total_duration": total_duration,
                "platform": platform,
                "mobility": mobility,
                "case": case,
                "dataset": dataset,
            }
        )

    return normalized_datasets
