import pytz
import pandas as pd
from datetime import datetime, timezone


def iso_to_unix(timestamp_str: str):
    """
    Converts an ISO 8601 formatted date string to a UNIX timestamp in nanoseconds.

    This function parses a provided ISO 8601 string, which may or may not include timezone information.
    If no timezone is specified, the function defaults to UTC. It then converts this datetime object to
    the corresponding UNIX timestamp expressed in nanoseconds since the epoch (January 1, 1970, 00:00:00 UTC).

    Parameters:
    - timestamp_str (str): An ISO 8601 formatted datetime string.

    Returns:
    - int: The UNIX timestamp in nanoseconds corresponding to the given ISO 8601 datetime.
    """
    try:
        # Try to parse the timestamp with timezone information
        dt = datetime.fromisoformat(timestamp_str)

        # If the datetime is naive (no timezone), assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        # If parsing fails, raise an error
        raise ValueError("Invalid ISO 8601 datetime format")

    # Convert to Unix timestamp in nanoseconds
    unix_timestamp = int(dt.timestamp() * 1e9)
    return unix_timestamp


# def iso_to_unix(timestamp_str: str):
#     """
#     Converts an ISO 8601 formatted date string to a UNIX timestamp in nanoseconds.
#
#     This function parses a provided ISO 8601 string, which may or may not include timezone information.
#     If no timezone is specified, the function defaults to UTC. It then converts this datetime object to
#     the corresponding UNIX timestamp expressed in nanoseconds since the epoch (January 1, 1970, 00:00:00 UTC).
#
#     Parameters:
#     - timestamp_str (str): An ISO 8601 formatted datetime string.
#
#     Returns:
#     - int: The UNIX timestamp in nanoseconds corresponding to the given ISO 8601 datetime.
#     """
#     try:
#         # Try to parse the timestamp with timezone information
#         dt = datetime.fromisoformat(timestamp_str)
#     except ValueError:
#         # If no timezone is specified, assume UTC
#         dt = datetime.fromisoformat(timestamp_str + "Z").replace(
#             tzinfo=timezone.utc
#         )
#
#     # Convert to Unix timestamp (seconds since the epoch, with nanoseconds)
#     unix_timestamp = int(dt.timestamp() * 1e9)
#     return unix_timestamp
#


def unix_to_iso(unix_timestamp: int, tz_info="UTC"):
    """
    Converts a UNIX timestamp in nanoseconds to an ISO 8601 formatted string, with an optional timezone.

    This function takes a UNIX timestamp in nanoseconds and converts it into a datetime object. The datetime
    is initially set in UTC. If a different timezone is specified, the datetime is converted to that timezone
    before formatting it into an ISO 8601 string.

    Parameters:
    - unix_timestamp (int): The UNIX timestamp in nanoseconds since the epoch.
    - tz_info (str): A string representing the timezone for the resulting ISO string. Defaults to 'UTC'.

    Returns:
    - str: An ISO 8601 formatted datetime string in the specified timezone.
    """
    # Convert Unix timestamp to datetime object in UTC
    dt_utc = datetime.fromtimestamp(unix_timestamp / 1e9, tz=timezone.utc)

    # Check if a specific timezone is requested
    if tz_info != "UTC":
        tz = pytz.timezone(tz_info)
        dt_tz = dt_utc.astimezone(tz)
        return dt_tz.isoformat()
    else:
        return dt_utc.isoformat()


def unix_to_date(unix_timestamp: int, tz_info="UTC") -> datetime.date:
    """
    Converts a UNIX timestamp in nanoseconds to an ISO 8601 formatted date string, with an optional timezone.

    This function takes a UNIX timestamp in nanoseconds and converts it into a datetime object. The datetime
    is initially set in UTC. If a different timezone is specified, the datetime is converted to that timezone
    before formatting it into an ISO 8601 date string (YYYY-MM-DD).

    Parameters:
    - unix_timestamp (int): The UNIX timestamp in nanoseconds since the epoch.
    - tz_info (str): A string representing the timezone for the resulting ISO string. Defaults to 'UTC'.

    Returns:
    - str: An ISO 8601 formatted date string in the specified timezone (YYYY-MM-DD).
    """
    # Convert Unix timestamp to datetime object in UTC
    dt_utc = datetime.fromtimestamp(unix_timestamp / 1e9, tz=timezone.utc)

    # Check if a specific timezone is requested
    if tz_info != "UTC":
        tz = pytz.timezone(tz_info)
        dt_tz = dt_utc.astimezone(tz)
        return dt_tz.date()
    else:
        return dt_utc.date()


def _convert_timestamp(
    df: pd.DataFrame,
    column: str = "timestamp",
    tz_info: str = "UTC",
) -> None:
    """Converts a dataframe column to iso from unix."""
    df[column] = pd.to_datetime(
        df[column].map(lambda x: unix_to_iso(x, tz_info))
    )


def resample_timestamp(df: pd.DataFrame, interval: str = "D", tz_info="UTC"):
    """
    Converts a DataFrame with UNIX timestamp index to default daily resolution.

    Parameters:
    - df (pd.DataFrame): DataFrame with UNIX timestamp index.
    - value_column (str): Name of the column to resample.
    - tz_info (str): Timezone information for conversion.

    Returns:
    - pd.DataFrame: Resampled DataFrame with daily frequency.
    """
    utc = True

    if tz_info != "UTC":
        utc = False

    # Convert index to readable datetime
    df.index = pd.to_datetime(
        df.index.map(lambda x: unix_to_iso(x, tz_info)), utc=utc
    )

    # Store original UNIX timestamps before resampling
    original_timestamps = df.index.to_series().resample(interval).last()
    original_timestamps.dropna(inplace=True)

    # Resample to daily frequency, using the last value of each day
    daily_df = df.resample(interval).last()

    # Optionally, fill NaN values if necessary, depending on your specific needs
    daily_df.dropna(inplace=True)

    # Restore original UNIX timestamps
    daily_df.index = original_timestamps.map(
        lambda x: iso_to_unix(x.isoformat())
    )
    daily_df.index.name = "timestamp"

    return daily_df
