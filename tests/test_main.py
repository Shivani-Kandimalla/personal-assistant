from unittest.mock import call, patch

from assistant.main import main
from assistant.config.settings import Settings


class TestMain:
    def test_main_calls_repl_with_settings(self):
        """main() must load settings and pass them directly to repl — no extra logic."""
        fake_settings = Settings(default_city="Austin, TX")

        with patch("assistant.main.load_settings", return_value=fake_settings) as mock_load, \
             patch("assistant.main.repl") as mock_repl:
            main()

        mock_load.assert_called_once()
        mock_repl.assert_called_once_with(fake_settings)

    def test_main_passes_loaded_settings_not_defaults(self):
        """Settings returned by load_settings reach repl unchanged."""
        custom = Settings(default_city="Chicago", calendar_path="/tmp/cal.json")

        with patch("assistant.main.load_settings", return_value=custom), \
             patch("assistant.main.repl") as mock_repl:
            main()

        passed_settings = mock_repl.call_args[0][0]
        assert passed_settings.default_city == "Chicago"
        assert passed_settings.calendar_path == "/tmp/cal.json"
