import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import duckdb
    import polars as pl
    import altair as alt
    return alt, duckdb, mo, pl


@app.cell
def _(mo):
    mo.md(
        """# AddBiomechanics Explorer

Welcome to the MoveDB demo. This interactive notebook lets you explore
the AddBiomechanics dataset using SQL queries powered by DuckDB.

Edit the SQL cell below and run it to query the dataset.
"""
    )
    return


@app.cell
def _(duckdb, mo):
    mo.md(f"DuckDB `{duckdb.__version__}` ready.")
    return


if __name__ == "__main__":
    app.run()
