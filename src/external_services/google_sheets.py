import logging

import pygsheets
import pandas as pd

from src.constants.gsheets import SHEETS_AUTHENTICATION_FILE

logger = logging.getLogger(__name__)


def read_from_sheets(
    worksheet_name: str,
    spreadsheet_name: str,
    header_label: str | None = None,
) -> pd.DataFrame:
    """The tab as a DataFrame, headed by its first row - or, with
    header_label, by the first row that has a cell equal to it, for a table
    with something above it (a summary). A tab that has content but no such
    row raises rather than reading as empty, so a caller that rebuilds the
    tab from what it read can't wipe it. A missing tab reads as empty."""
    # Login/Authenticate
    gc = pygsheets.authorize(service_account_file=SHEETS_AUTHENTICATION_FILE)

    sheet = gc.open(spreadsheet_name)
    try:
        worksheet = sheet.worksheet_by_title(worksheet_name)
    except pygsheets.WorksheetNotFound:
        return pd.DataFrame()
    if header_label is None:
        # get_as_df returns a DataFrame with headers from the first row
        return worksheet.get_as_df()

    values = worksheet.get_as_df(has_header=False)
    for index in range(len(values)):
        row = values.iloc[index]
        if (row.astype(str) == header_label).any():
            table = values.iloc[index + 1 :]
            blank = table.isna() | (
                table.astype(str).apply(lambda c: c.str.strip()) == ""
            )
            table = table[~blank.all(axis=1)].reset_index(drop=True)
            table.columns = [str(label) for label in row]
            return table
    if (values.astype(str) != "").any().any():
        raise ValueError(f"No '{header_label}' header row in '{worksheet_name}'")
    return pd.DataFrame()


def read_values_from_sheets(
    worksheet_names: list[str],
    spreadsheet_name: str,
    optional_worksheet_names: tuple[str, ...] = (),
) -> dict[str, list[list]]:
    """Every cell of each named tab as a matrix of raw values (numbers as
    numbers, dates as serial day numbers), for tabs laid out as a report
    rather than a table with its header in row 1. Opens the spreadsheet once
    for all the tabs. An optional tab the spreadsheet doesn't have is left
    out of the result; any other missing tab raises."""
    gc = pygsheets.authorize(service_account_file=SHEETS_AUTHENTICATION_FILE)

    sheet = gc.open(spreadsheet_name)
    values = {}
    for name in [*worksheet_names, *optional_worksheet_names]:
        try:
            worksheet = sheet.worksheet_by_title(name)
        except pygsheets.WorksheetNotFound:
            if name in optional_worksheet_names:
                continue
            raise
        values[name] = worksheet.get_all_values(
            include_tailing_empty=False,
            include_tailing_empty_rows=False,
            value_render=pygsheets.ValueRenderOption.UNFORMATTED_VALUE,
            date_time_render_option=pygsheets.DateTimeRenderOption.SERIAL_NUMBER,
        )
    return values
