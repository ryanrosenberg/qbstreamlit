import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode, JsCode
from st_aggrid.shared import GridUpdateMode
import subprocess

def aggrid_interactive_table(df: pd.DataFrame, accent_color='#ff4b4b', height=400):
    """Creates an st-aggrid interactive table based on a dataframe.
    Args:
        df (pd.DataFrame]): Source dataframe
    Returns:
        dict: The selected row
    """
    options = GridOptionsBuilder.from_dataframe(
        df, enableValue=True
    )

    options.configure_default_column(min_column_width=0.1)
    options.configure_selection("single")
    options.configure_pagination()
    # options.configure_auto_height(False)

    for name in df.columns:
        if name in ['P', 'G', 'N']:
            options.configure_column(name, width=1)

    bolding_js = JsCode('''
    function(params) {
        return params.value
        }''')

    for name in df.columns:
        if name in ['answer', 'easy', 'medium', 'hard']:
            options.configure_column(name, cellRenderer = bolding_js)

    custom_css = {
        ".ag-header-viewport": {"background-color": "white"},
        ".ag-paging-panel": {"font-size": "1.2em"},
        ".ag-theme-streamlit .ag-root-wrapper": {"border": "0px solid pink !important"},
        ".ag-theme-streamlit .ag-header": {"border": "0px solid pink !important"},
        ".ag-header-cell": {
            "background-color": "#555555", "color": "white",
            "border-bottom": f"2px solid {accent_color} !important"}
    }
    selection = AgGrid(
        df,
        enable_enterprise_modules=True,
        gridOptions=options.build(),
        theme="streamlit",
        height=height,
        custom_css=custom_css,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        allow_unsafe_jscode=True,
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS
    )

    return selection

def df_to_kable(df):
    df.to_csv('temp_df.csv', index = False)
    process = subprocess.Popen("Rscript kable.R", stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell = True)
    result = process.communicate()
    return result[0]

def df_to_dt(df):
    df.to_csv('temp_df.csv', index = False)
    process = subprocess.Popen("Rscript dt.R", stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell = True)
    result = process.communicate()
    return result[0]