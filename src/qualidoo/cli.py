"""Qualidoo CLI - AI-powered Odoo addon quality analyzer."""

import typer

app = typer.Typer(
    name="qualidoo",
    help="AI-powered Odoo addon quality analyzer",
)


@app.command()
def check():
    """Check your Odoo addon quality."""
    typer.echo("🧪 We're preparing something interesting for the Odoo environment... stay tuned!")


if __name__ == "__main__":
    app()
