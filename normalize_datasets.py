import pathlib
from typing import List, TypedDict

import numpy as np
import pandas as pd
from pandas.core.frame import DataFrame

from datasets5G import datasets5G


class Limits(TypedDict):
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


# disable pandas warnings for chaining assignment
pd.options.mode.chained_assignment = None


def get_normalized_datasets() -> List[NormalizedDataset]:
    normalized_datasets = []

    for filename in datasets5G:
        # Normalize dataset using pandas
        csv_data: DataFrame = pd.read_csv(filename)  # type: ignore

        # Get only interesting columns
        filtered_data: DataFrame = csv_data[
            ["Timestamp", "DL_bitrate", "UL_bitrate", "State"]
        ]

        # Set value types
        filtered_data.astype({"DL_bitrate": "float", "UL_bitrate": "float"})

        # Interpolate values between idle rows and downloaded ones
        filtered_data.loc[
            filtered_data["State"] == "I", ["DL_bitrate", "UL_bitrate"]
        ] = np.nan
        filtered_data["DL_bitrate"].values[filtered_data["DL_bitrate"] < 0.001] = np.nan
        filtered_data["UL_bitrate"].values[filtered_data["UL_bitrate"] < 0.001] = np.nan
        filtered_data.interpolate(inplace=True)
        filtered_data.dropna(inplace=True)

        # Remove repeated timestamps and State column by taking the mean
        filtered_data = filtered_data.groupby("Timestamp").mean().reset_index()

        # calculate time deltas for each speed
        filtered_data["Timestamp"] = pd.to_datetime(
            filtered_data["Timestamp"], format="%Y.%m.%d_%H.%M.%S"
        )
        filtered_data["Timestamp"] = (
            ((filtered_data["Timestamp"] - filtered_data["Timestamp"].shift()))
            .shift(-1)
            .fillna(pd.Timedelta(seconds=1))
            .dt.seconds
        )

        # replace values less than 1bps to be 1bps or htb does not work properly
        filtered_data["DL_bitrate"].values[filtered_data["DL_bitrate"] < 0.001] = 0.001
        filtered_data["UL_bitrate"].values[filtered_data["UL_bitrate"] < 0.001] = 0.001

        # calculate total duration of data
        total_duration = filtered_data["Timestamp"].sum()

        # rename data columns to standardized names
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

        # append normalized results
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
