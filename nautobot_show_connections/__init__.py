from nautobot.extras.plugins import PluginConfig


class ShowConnectionsConfig(PluginConfig):
    """This class defines attributes for the Nautobot Show Connections Plugin."""

    name = 'nautobot_show_connections'
    verbose_name = 'Show circuit connections'
    description = 'Nautobot plugin that shows connections between sites based on the presence of circuits'
    version = '0.1'
    base_url = 'show-connections'
    author = 'Johan Boer'
    min_version = "1.0"
    required_settings = []
    default_settings = {}
    caching_config = {}


config = ShowConnectionsConfig
