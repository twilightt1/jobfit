from argparse import ArgumentParser


def main() -> None:
    parser = ArgumentParser(description="Run JobFit AI evaluation tasks.")
    parser.add_argument("--task", default="all", help="Evaluation task to run.")
    parser.add_argument("--dataset", default="v1", help="Dataset version to evaluate.")
    args = parser.parse_args()

    print(
        "Evaluation harness skeleton. "
        f"Task={args.task!r}, dataset={args.dataset!r}. "
        "Implementation starts in Milestone 6."
    )


if __name__ == "__main__":
    main()
