from ai_interview_assistant.constants import *
from ai_interview_assistant.utils.common import read_yaml, create_directories
from ai_interview_assistant.entity import (LLMConfig, STTConfig, TTSConfig, ArtifactsConfig)
from pathlib import Path

class ConfigurationManager:
    def __init__(
        self,
        config_filepath = CONFIG_FILE_PATH,
        params_filepath = PARAMS_FILE_PATH):

        self.config = read_yaml(config_filepath)
        self.params = read_yaml(params_filepath)

        create_directories([self.config.artifacts_root])


    def get_llm_config(self) -> LLMConfig:
        config = self.config.llm_config

        llm_config = LLMConfig(
            model_name=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            prompt_template=config.prompt_template
        )

        return llm_config

    def get_stt_config(self) -> STTConfig:
        config = self.config.stt_config

        stt_config = STTConfig(
            model_name=config.model_name,
            sample_rate=config.sample_rate
        )

        return stt_config

    def get_tts_config(self) -> TTSConfig:
        config = self.config.tts_config

        tts_config = TTSConfig(
            language=config.language,
            slow=config.slow
        )

        return tts_config

    def get_artifacts_config(self) -> ArtifactsConfig:
        artifacts_config = ArtifactsConfig(
            root_dir=Path(self.config.artifacts_root),
            audio_store=Path(self.config.data_storage.audio_store),
            ffmpeg_path=self.config.data_storage.get('ffmpeg_path', 'ffmpeg')
        )

        return artifacts_config