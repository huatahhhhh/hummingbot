import os
import shutil
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from hummingbot.client.config.config_helpers import (
    format_config_file_name,
    parse_config_default_to_text,
    parse_cvar_value,
    save_previous_strategy_value,
)
from hummingbot.client.config.config_validators import validate_bool
from hummingbot.client.config.config_var import ConfigVar
from hummingbot.client.settings import STRATEGIES_CONF_DIR_PATH
from hummingbot.core.utils.async_utils import safe_ensure_future

from .import_command import ImportCommand

if TYPE_CHECKING:
    from hummingbot.client.hummingbot_application import HummingbotApplication


class CreateNewFromPreviousCommand:
    def create_new_from_previous_strategy(
        self,  # type: HummingbotApplication
    ):
        previous_strategy_file = self.client_config_map.previous_strategy

        if previous_strategy_file is not None:
            safe_ensure_future(self.prompt_for_create_new_from_previous_strategy(previous_strategy_file))
        else:
            self.notify("No previous strategy found.")

    async def prompt_for_create_new_from_previous_strategy(
        self,  # type: HummingbotApplication
        file_name: str,
    ):
        self.app.clear_input()
        self.placeholder_mode = True
        self.app.hide_input = True

        previous_strategy = ConfigVar(
            key="previous_strategy_answer",
            prompt=f"Do you want to replicate the previously stored config? [{file_name}] (Yes/No) >>>",
            type_str="bool",
            validator=validate_bool,
        )

        await self.prompt_answer_2(previous_strategy)
        if self.app.to_stop_config:
            self.app.to_stop_config = False
            return

        if previous_strategy.value:
            new_filename = await self.prompt_new_file_name_2()
            new_file_path = STRATEGIES_CONF_DIR_PATH / new_filename
            previous_file_path = STRATEGIES_CONF_DIR_PATH / file_name
            shutil.copy(previous_file_path, new_file_path)
            self.notify(f"Created new strategy file {new_filename}")
            ImportCommand.import_command(self, new_filename)
            save_previous_strategy_value(new_filename, self.client_config_map)

        # clean
        self.app.change_prompt(prompt=">>> ")

        # reset input
        self.placeholder_mode = False
        self.app.hide_input = False

    async def prompt_answer_2(
        self,  # type: HummingbotApplication
        config: ConfigVar,
        input_value: Optional[str] = None,
        assign_default: bool = True,
    ):

        if input_value is None:
            if assign_default:
                self.app.set_text(parse_config_default_to_text(config))
            prompt = await config.get_prompt()
            input_value = await self.app.prompt(prompt=prompt)

        if self.app.to_stop_config:
            return

        config.value = parse_cvar_value(config, input_value)
        err_msg = await config.validate(input_value)
        if err_msg is not None:
            self.notify(err_msg)
            config.value = None
            self.notify("Bad")
            await self.prompt_answer_2(config)

    async def prompt_new_file_name_2(
        self,  # type: HummingbotApplication
    ):
        dt = datetime.utcnow().strftime("%Y-%m-%d:%H:%M:%S")
        prompt = f"Add a note to append to the back of the the filename (e.g conf_{dt}__<your_custom_note>.yml) >>> "
        input = await self.app.prompt(prompt=prompt)
        if input:
            input = f"conf_{dt}__{input}"
        else:
            input = f"conf_{dt}"

        input = format_config_file_name(input)
        file_path = os.path.join(STRATEGIES_CONF_DIR_PATH, input)
        if os.path.exists(file_path):
            self.notify(f"{input} file already exists, please enter a new name.")
            return await self.prompt_new_file_name_2()
        else:
            return input
