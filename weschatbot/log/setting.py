from weschatbot.utils.config import config


def logging_setting() -> None:
    import logging.config

    logging_config_file = config.get("logging", "config_file")

    print(f"Load logging config from file: {logging_config_file}")

    logging.config.fileConfig(logging_config_file)
