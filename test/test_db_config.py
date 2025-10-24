from weschatbot.utils.config import config


def test_db_config():
    db_config = config["db"]
    assert db_config.getint("pool_size") == 10
    assert db_config.getboolean("echo") == True
    assert db_config.getint("pool_recycle", 1800) == 1800
    assert db_config.getboolean("pool_pre_ping", fallback=False) == True
    assert db_config.get("isolation_level") == "READ COMMITTED"
