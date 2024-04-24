from pandas import DataFrame
from tabulate import tabulate


def generate_results_table(dataframe: DataFrame, column_list: list[str] = None, section_name: str = "") -> str:
    selected_df = dataframe[column_list] if column_list else dataframe
    section_name = f"## {section_name}" if section_name else "## Test Results"

    table = tabulate(selected_df, headers="keys", tablefmt="pipe", showindex=True)
    ret_str = f"{section_name}\n{table}"
    return ret_str


def generate_markdown_report(test_name: str, report_strings: list[str]):
    with open(test_name, "w") as f:
        f.write(f"Generated from {test_name}.\n\n")
        for report_string in report_strings:
            f.write(report_string + "\n\n")
