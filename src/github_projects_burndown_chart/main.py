import argparse

from chart.burndown import *
from config import config
from discord import webhook
from gh.api_wrapper import get_organization_project, get_repository_project
from gh.project import Project
from slack import webhook as slack_webhook
from util import calculators, colors
from util.stats import *
from util.calculators import *


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Generate a burndown chart for a GitHub project."
    )
    parser.add_argument(
        "project_type",
        choices=["repository", "organization"],
        help="The type of project to generate a burndown chart for. Can be either 'organization' or 'repository'.",
    )
    parser.add_argument(
        "project_name", help="The name of the project as it appears in the config.json"
    )
    parser.add_argument(
        "--discord",
        action="store_true",
        help="If present, posts the burndown chart to the configured webhook",
    )

    parser.add_argument(
        "--slack",
        action="store_true",
        help="If present, posts the burndown chart to slack",
    )
    return parser.parse_args()


def download_project_data(args):
    if args.project_type == "repository":
        project: Project = get_repository_project()
    elif args.project_type == "organization":
        project: Project = get_organization_project()
    return project


def prepare_chart_data(stats: ProjectStats):
    color = colors()
    data = BurndownChartData(
        sprint_name=stats.project.name,
        utc_chart_start=config.utc_sprint_start(),
        utc_chart_end=config.utc_chart_end() or config.utc_sprint_end(),
        utc_sprint_start=config.utc_sprint_start(),
        utc_sprint_end=config.utc_sprint_end(),
        total_points=stats.total_points,
        series=[
            BurndownChartDataSeries(
                name=pts_type,
                data=stats.remaining_points_by_date(
                    calculators(stats.project)[pts_type]
                ),
                format=dict(color=next(color)),
            )
            for pts_type in config["settings"].get("calculators", ["closed"])
        ],
        points_label=f"Outstanding {'Days' if config['settings']['points_label'] else 'Issues'}",
    )
    return data


if __name__ == "__main__":
    args = parse_cli_args()
    config.set_project(args.project_type, args.project_name)
    project = download_project_data(args)
    stats = ProjectStats(
        project,
        config.utc_sprint_start(),
        config.utc_chart_end() or config.utc_sprint_end(),
    )
    # Generate the burndown chart
    burndown_chart = BurndownChart(prepare_chart_data(stats))

    post_chart = args.discord or args.slack
    if post_chart:
        chart_path = "./tmp/chart.png"
        burndown_chart.generate_chart(chart_path)

    if args.discord:
        webhook.post_burndown_chart(chart_path)
    if args.slack:
        slack_webhook.post_burndown_chart(chart_path)

    burndown_chart.render()
    print("Done")
